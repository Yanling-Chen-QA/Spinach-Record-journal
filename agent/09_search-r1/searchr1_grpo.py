import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np
import re
from typing import List, Dict
from dataclasses import dataclass
import difflib
from search_engine import SearchEngine
import os

from searchr1_config import searchr1_config
config = searchr1_config()

@dataclass
class TokenStep:
    # 记录 token id
    token_id: int
    # 记录 token 文本
    token_text: str
    # 记录 token 的 log_prob
    log_prob: float
    # 记录 token 在序列中的位置
    position: int

@dataclass
class Trajectory:
    # 记录查询
    query: str
    # 记录生成的 token 步骤
    token_steps: List[TokenStep]
    # 记录生成的文本
    generated_text: str
    # 记录奖励值
    reward: float
    # 记录最终答案，初始为空字符串
    final_answer: str
    # 记录完整的输入序列（包含 prompt + generated + information）
    full_input_ids: List[int]  
    # 记录每个生成 token 在序列中的预测位置
    generated_positions: List[int]  

class SearchR1GRPO:
    def __init__(
        self, model_name: str = config.modle_name, lr: float = config.lr):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 加载模型
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map=self.device)

        # GRPO 参数
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.beta = config.beta  # KL 散度系数
        self.clip_epsilon = config.clip_epsilon  # PPO 裁剪参数
        self.search_engine = SearchEngine()


    def generate_trajectory(self, query: str, max_tokens: int = config.max_tokens) -> Trajectory:
        """生成轨迹 - 每个 token 作为一个动作"""
        self.model.eval()
        prompt = config.prompt.format(query=query)
    
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

        token_steps = []
        generated_tokens = []
        current_text = prompt

        # 用于保存完整序列和位置信息
        full_input_ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        prompt_len = len(full_input_ids)
        generated_positions = []

        with torch.no_grad():
            for step in range(max_tokens):
                # 前向传播
                outputs = self.model(input_ids)
                logits = outputs.logits[0, -1, :]  # 最后一个位置的 logits

                # 转换为 float32 类型, 避免溢出
                logits = logits.float()

                # 计算概率分布
                probs = F.softmax(logits, dim=-1)
                
                # 采样下一个 token，会返回 token id
                token_dist = torch.distributions.Categorical(probs)
                # 根据当前概率分布采样下一个 token，引入随机性
                next_token_id = token_dist.sample()

                # 计算这个 token 的 log_prob
                log_prob = token_dist.log_prob(next_token_id).item()

                # 将 token id 解码为 token
                token_text = self.tokenizer.decode(
                    [next_token_id], skip_special_tokens=False
                )
                # 记录当前这个 token 的位置，这个位置是完整序列中的位置
                generated_positions.append(len(full_input_ids) - 1)

                # 记录步骤，记录这个 token 在完整序列中的位置
                token_step = TokenStep(
                    token_id=next_token_id.item(),
                    token_text=token_text,
                    log_prob=log_prob,
                    position=step,
                )
                token_steps.append(token_step)
                
                # 记录生成的 token id，从<think>开始记录
                generated_tokens.append(next_token_id.item())

                # 将当前 token 加入到输入中
                input_ids = torch.cat(
                    [input_ids, next_token_id.unsqueeze(0).unsqueeze(0)], dim=1
                )

                full_input_ids.append(next_token_id.item())
                current_text += token_text

                
                if current_text.rstrip().endswith("</search>"):
                    search_result = self.search_engine.search(query)
                    info_text = f"\n<information>{search_result}</information>\n"
                    info_tokens = self.tokenizer.encode(
                        info_text, add_special_tokens=False
                    )

                    # 将搜索结果添加到输入中
                    info_tensor = torch.tensor(info_tokens, dtype=input_ids.dtype, device=input_ids.device).unsqueeze(0)
                    input_ids = torch.cat([input_ids, info_tensor], dim=1)
                    full_input_ids.extend(info_tokens)
                    current_text += info_text
                    # print(current_text)
                    
                # 检查是否遇到 </answer> 结束生成
                if current_text.rstrip().endswith("</answer>"):
                    break

                # 检查其他结束条件
                if (
                    next_token_id.item() == self.tokenizer.eos_token_id
                    or step >= max_tokens - 1
                ):
                    break

        # 生成的完整文本
        generated_text = self.tokenizer.decode(
            input_ids[0][prompt_len:], skip_special_tokens=False
        )
        # 提取最终答案
        final_answer = self.extract_final_answer(generated_text)

        return Trajectory(
            query=query,
            token_steps=token_steps,
            generated_text=generated_text,
            reward=0.0,
            final_answer=final_answer,
            full_input_ids=full_input_ids,
            generated_positions=generated_positions,
        )

    def extract_final_answer(self, text: str) -> str:
        """从 <answer>...</answer> 中提取答案"""
        pattern = r"<answer>(.*?)</answer>"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[-1].strip()
        return ""

    def compute_reward(self, trajectory: Trajectory, ground_truth: str) -> float:
        """
        计算奖励 - 包含答案正确性和格式正确性
        答案正确: 完全一致得1分，否则0分
        格式正确: 符合格式得0.1分，否则-1分
        """

        # 1. 格式正确性检查
        format_reward = self.check_format_correctness(trajectory.generated_text)

        # 2. 答案正确性检查
        answer_reward = self.check_answer_correctness(
            trajectory.final_answer, ground_truth
        )

        # 总奖励 = 答案奖励 + 格式奖励
        total_reward = answer_reward + format_reward

        return total_reward

    def check_format_correctness(self, generated_text: str) -> float:

        # 移除 think 标签及中间的内容
        generated_text = re.sub(r'<think>.*?</think>', '', generated_text, flags=re.DOTALL).strip()

        # 检查 answer 标签
        answer_start_count = generated_text.count("<answer>")
        answer_end_count = generated_text.count("</answer>")

        # answer 标签必须恰好出现一次
        if answer_start_count != 1 or answer_end_count != 1:
            return -1.0  # answer 标签数量错误

        # 检查 answer 是否在最末尾
        answer_start_pos = generated_text.rfind("<answer>")
        answer_end_pos = generated_text.rfind("</answer>")

        # answer 标签位置错误
        if (not generated_text.endswith("</answer>")) or answer_start_pos > answer_end_pos:
            return -1.0

        start_search_tag = generated_text.count("<search>")
        end_search_tag = generated_text.count("</search>")
        start_information_tag = generated_text.count("<information>")
        end_information_tag = generated_text.count("</information>")    

        # 必须成对出现
        tag_pair_check = (start_search_tag == end_search_tag) and (start_information_tag == end_information_tag)
        # 两类标签必须同时存在/不存在
        tag_exist_check = (start_search_tag == start_information_tag)

        if not (tag_pair_check and tag_exist_check):
            return -1.0

        return 0.5

    def check_answer_correctness(self, final_answer: str, ground_truth: str) -> float:

        if not final_answer or not ground_truth:
            return 0.0
        
        if final_answer == ground_truth:
            return 2.0
        
        if final_answer == '未找到相关内容':
            return 0.5
    
        # 预处理：去掉空格并统一大小写，确保比较的纯粹性
        pred = "".join(final_answer.split()).lower()
        target = "".join(ground_truth.split()).lower()
    
        if not pred:
            return 0.0
    
        # 计算相似度 (0.0 到 1.0)
        matcher = difflib.SequenceMatcher(None, pred, target)
        similarity = matcher.ratio()
    
        # 设定硬门槛
        if similarity < 0.5:
            return 0.0

        return 1.0

    def compute_advantages(self, rewards: List[float]) -> torch.Tensor:
        """计算相对优势"""
        rewards_tensor = torch.tensor(rewards, dtype=torch.float32).to(self.device)

        # 如果只有一个样本，直接返回 0（无优势）
        if len(rewards) == 1:
            return torch.zeros_like(rewards_tensor)

        mean_reward = torch.mean(rewards_tensor)
        std_reward = torch.std(rewards_tensor, unbiased=False) + 1e-8  # 使用总体标准差
        advantages = (rewards_tensor - mean_reward) / std_reward
        return advantages

    def compute_kl_divergence(
        self, old_log_probs: torch.Tensor, new_log_probs: torch.Tensor
    ) -> torch.Tensor:
        """计算 GRPO 要求的 K3 近似 KL 散度"""
        # 步骤1：计算 π_old/π_new = exp(old_log_probs - new_log_probs)
        ratio_old_new = torch.exp(old_log_probs - new_log_probs)
        # 步骤2：计算 log(π_old/π_new) = old_log_probs - new_log_probs
        log_ratio_old_new = old_log_probs - new_log_probs
        # 步骤3：K3 公式
        k3 = ratio_old_new - log_ratio_old_new - 1
        # 取均值（token级平均）
        return torch.mean(k3)

    def recompute_log_probs(self, trajectories: List[Trajectory]) -> List[torch.Tensor]:
        """重新计算轨迹的对数概率"""
        # 关键优化：使用 padding 一次性计算所有新的 log_probs
        if not trajectories:
            return []

        # 收集所有序列的 input_ids 和 positions
        all_input_ids = [traj.full_input_ids for traj in trajectories]
        all_positions = [traj.generated_positions for traj in trajectories]

        # 找到最大长度
        max_len = max(len(ids) for ids in all_input_ids)

        # Padding 到相同长度（左侧 padding）
        padded_ids = []
        attention_masks = []
        adjusted_positions = []  # 调整后的位置索引

        for ids, positions in zip(all_input_ids, all_positions):
            pad_len = max_len - len(ids)
            # 左侧 padding
            padded_ids.append([self.tokenizer.pad_token_id] * pad_len + ids)
            attention_masks.append([0] * pad_len + [1] * len(ids))
            # 调整位置索引（因为左侧添加了 padding）
            adjusted_positions.append([pos + pad_len for pos in positions])

        # 转换为 tensor 并批量前向传播
        input_ids = torch.tensor(padded_ids, dtype=torch.long).to(self.device)
        attention_mask = torch.tensor(attention_masks, dtype=torch.long).to(self.device)

        # 一次性前向传播所有样本
        outputs = self.model(input_ids, attention_mask=attention_mask)
        
        # 提取每个 token 的 logits
        logits = outputs.logits

        # 提取每个样本的 log_probs
        all_log_probs = []
        # 
        for i, (traj, positions) in enumerate(zip(trajectories, adjusted_positions)):
            log_probs = []
            for pos, token_step in zip(positions, traj.token_steps):
                log_prob = F.log_softmax(logits[i, pos], dim=-1)[token_step.token_id]
                log_probs.append(log_prob)
            all_log_probs.append(torch.stack(log_probs))

        return all_log_probs

    def update_policy(self, trajectories: List[Trajectory]) -> Dict[str, float]:
        """GRPO 策略更新"""

        if not trajectories:
            return {"loss": 0.0, "kl_div": 0.0}

        self.model.train()

        # 计算奖励和优势
        rewards = [traj.reward for traj in trajectories]
        advantages = self.compute_advantages(rewards)

        # 提取生成轨迹时记录的 old_log_probs
        old_log_probs_list = []
        for traj in trajectories:
            old_probs = torch.tensor([step.log_prob for step in traj.token_steps]).to(self.device)
            old_log_probs_list.append(old_probs)

        # 用同一批轨迹数据对模型进行多少次参数更新
        update_times = config.update_times
        for _ in range(update_times):

            # 重新计算new_log_probs（用当前模型参数）
            new_log_probs_list = self.recompute_log_probs(trajectories)

            # 清空梯度
            self.optimizer.zero_grad()

            # 收集所有样本的 loss（不在循环中 backward）
            all_policy_losses = []
            all_kl_divs = []

            for i, traj in enumerate(trajectories):
                new_log_probs = new_log_probs_list[i]
                old_log_probs = old_log_probs_list[i]

                if len(old_log_probs) != len(new_log_probs):
                    continue

                # 计算概率比
                ratio = torch.exp(new_log_probs - old_log_probs)

                # 扩展优势到所有 token
                traj_advantage = advantages[i].repeat(len(ratio)).to(self.device)

                # PPO 裁剪目标
                surr1 = ratio * traj_advantage
                surr2 = (
                    torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                    * traj_advantage
                )
                policy_loss = -torch.min(surr1, surr2).mean()

                # KL 散度
                kl_div = self.compute_kl_divergence(old_log_probs, new_log_probs)

                all_policy_losses.append(policy_loss)
                all_kl_divs.append(kl_div)

            # 计算 loss（对比new/old_log_probs + KL散度）
            if all_policy_losses:
                total_policy_loss = torch.stack(all_policy_losses).mean()
                total_kl_div = torch.stack(all_kl_divs).mean()
                total_loss = total_policy_loss + self.beta * total_kl_div

                # 反向传播计算梯度
                total_loss.backward()

                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)

                # 更新参数
                self.optimizer.step()

                # 记录统计信息
                avg_loss = total_loss.item()
                avg_kl = total_kl_div.item()
            else:
                avg_loss = 0.0
                avg_kl = 0.0

        # 显式清理缓存
        torch.cuda.empty_cache()

        return {
            "loss": avg_loss,
            "kl_div": avg_kl,
            "avg_reward": np.mean(rewards),
            "beta": self.beta,
        }
    
    def save_model(self, save_dir: str = "./output_model") -> None:
        # 创建保存目录（如果不存在）
        os.makedirs(save_dir, exist_ok=True)
        
        # 设置模型为评估模式（避免保存训练相关的状态）
        self.model.eval()
        
        try:
            # 保存模型权重和配置
            self.model.save_pretrained(
                save_dir,
                safe_serialization=True, 
                max_shard_size="10GB"     
            )
            
            # 保存分词器（包含特殊token配置）
            self.tokenizer.save_pretrained(save_dir)
            
            print(f"模型和分词器已成功保存到: {os.path.abspath(save_dir)}")
            
        except Exception as e:
            print(f"保存模型时出错: {str(e)}")
            raise  # 抛出异常让调用方感知错误

    def train_step(
        self, queries: List[str], ground_truths: List[str], group_size: int = 2
    ) -> Dict[str, float]:
        """执行一步训练 - 适配 GRPO 组内优势计算"""
        all_trajectories = []
        
        for query, truth in zip(queries, ground_truths):
            group_trajectories = []
            
            # 1. 针对同一个 Query 生成多条轨迹 (Group Sampling)
            for _ in range(group_size):
                trajectory = self.generate_trajectory(query, max_tokens=500)
                trajectory.reward = self.compute_reward(trajectory, truth)
                group_trajectories.append(trajectory)
            
            # 2. 计算组内奖励统计
            group_rewards = torch.tensor([t.reward for t in group_trajectories], dtype=torch.float32)
            mean_reward = group_rewards.mean()
            std_reward = group_rewards.std() + 1e-8
            
            # 3. 计算相对优势并存储到 trajectory 对象中
            for t in group_trajectories:
                # 标准化：(当前奖励 - 组内平均) / 组内标准差
                t.advantage = (t.reward - mean_reward.item()) / std_reward.item()
                all_trajectories.append(t)

        # 4. 调用更新策略（注意：update_policy 内部也需要从 traj.advantage 读取）
        metrics = self.update_policy(all_trajectories)

        # 计算平均 token 数
        avg_tokens = np.mean([len(traj.token_steps) for traj in all_trajectories])
        # 计算包含搜索指令的轨迹数
        search_count = sum(1 for traj in all_trajectories if "<search>" in traj.generated_text)

        # 5. metrics 是个记录统计信息的字典
        metrics.update({
            "avg_tokens": avg_tokens,
            "search_trajectories": search_count / len(all_trajectories),
            "trajectories": all_trajectories,
        })

        torch.cuda.empty_cache()
        return metrics
