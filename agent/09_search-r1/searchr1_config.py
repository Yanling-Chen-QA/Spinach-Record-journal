class searchr1_config:
    def __init__(self):
        # 使用模型
        self.modle_name = '/data/xxx/LLMs/Qwen/Qwen3-0.6B'
        self.num_epochs = 500
        self.batch_size = 2
        self.save_interval = 100
        self.lr = 5e-5
        self.beta = 0.1  # KL 散度系数
        self.clip_epsilon = 0.2  # PPO 裁剪参数
        self.max_tokens = 500  # 最大生成 token 数
        self.update_times = 2  # 每个轨迹更新次数
        self.prompt = '''
<|im_start|>system
你是一个具有搜索能力的推理型助手。在解决问题时，你必须遵循以下逻辑步骤：
1. 思考 (Thinking)：在 <think> 和 </think>标签内分析问题，确定是否需要外部知识。
2. 搜索 (Searching)：如果涉及具体的学校规章制度时，请务必使用 <search>输入用户问题</search> 标签进行查询搜索。
3. 回答 (Answering)：根据以上内容，在 <answer> 输出结果 </answer> 标签内给出准确、简洁的最终结论。
注意：
1. 所有回答必须包含 <think> 和 <answer> 标签。
2. 如果使用了搜索，尽量使用 <information> 中的原文内容进行回答。

如果与学校规章制度相关，就需要进行搜索。示例：
问题：大学一学期学费是多少钱？
<think>用户询问学费相关问题，这属于学校行政规定。</think>
<search>大学一学期学费是多少钱？</search>
<information>一学期费用是 5 千元</information>
<answer>一学期费用是 5 千元</answer>(如果有<search>, 就根据<information>中的内容回答)

如果<information>标签中的内容为空，就回答未找到相关内容：
<information></information>
<answer>未找到相关内容</answer>

如果与学校规章制度不相关，就不需要搜索。示例：
问题：帮我写一篇以勇敢为主题的 100 字的小故事。
<think>思考过程</think>
<answer>直接输出结果</answer>
注意： 所有回答必须包含 <think> 和 <answer> 标签。
<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
'''
