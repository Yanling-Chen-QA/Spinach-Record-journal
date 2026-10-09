from __future__ import annotations

import asyncio
import atexit
import os
import sys
from pathlib import Path
from typing import Any

# 加载环境变量
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek

from background_loop import BackgroundLoop
from memory_manager import MemoryManager
from skills_scanner import generate_skills_prompt, scan_skills
from tools import get_all_tools


def load_identity(memory_dir: Path) -> str:
    """加载 IDENTITY.md 作为基础身份设定。"""
    identity_file = memory_dir / "IDENTITY.md"
    if identity_file.exists():
        content = identity_file.read_text(encoding="utf-8")
        # 移除 frontmatter（第一个 # 标题之前的所有内容）
        lines = content.split("\n")
        result = []
        found_title = False
        for line in lines:
            if line.startswith("# "):
                found_title = True
            if found_title:
                result.append(line)
        return "\n".join(result).strip()
    return "你是 CoreClaw，一个拥有工具调用能力的 AI 助手。"


def load_user_memory(memory_dir: Path) -> str:
    """加载 USER.md 和 MEMORY.md 中的用户相关记忆。"""
    sections = []

    # 加载 USER.md
    user_file = memory_dir / "USER.md"
    if user_file.exists():
        content = user_file.read_text(encoding="utf-8")
        # 提取用户偏好和兴趣部分
        lines = content.split("\n")
        for section_title in ["## 使用偏好", "## 兴趣爱好", "## 基本信息"]:
            for i, line in enumerate(lines):
                if line.startswith(section_title):
                    section_content = [line]
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## "):
                            break
                        section_content.append(lines[j])
                    sections.append("\n".join(section_content))
                    break

    return "\n\n".join(sections) if sections else ""


def load_soul(memory_dir: Path) -> str:
    """加载 SOUL.md 作为性格特征设定。"""
    soul_file = memory_dir / "SOUL.md"
    if soul_file.exists():
        content = soul_file.read_text(encoding="utf-8")
        # 移除 frontmatter（第一个 # 标题之前的所有内容）
        lines = content.split("\n")
        result = []
        found_title = False
        for line in lines:
            if line.startswith("# "):
                found_title = True
            if found_title:
                result.append(line)
        return "\n".join(result).strip()
    return ""


class CoreClawAgent:
    """CoreClaw Agent with tool support and memory management."""

    def __init__(self, base_dir: Path | None = None, model: str | None = None):
        self.base_dir = base_dir or Path.cwd()
        self.tools = get_all_tools(self.base_dir)

        # 初始化模型 (默认 DeepSeek)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model_name = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")

        self.llm = ChatDeepSeek(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.2,
        )

        # 初始化记忆管理器（传入 LLM 用于主动提取记忆）
        self.memory = MemoryManager(self.base_dir, llm_client=self.llm)
        self.memory.start_watching()

        # 初始化后台定时任务（延迟启动，等事件循环准备好）
        self.bg_loop = BackgroundLoop(self.base_dir)
        self._bg_started = False

        # 加载身份设定（IDENTITY.md）
        identity_content = load_identity(self.memory.memory_dir)

        # 加载性格特征（SOUL.md）
        soul_content = load_soul(self.memory.memory_dir)

        # 加载用户记忆（USER.md）
        user_memory = load_user_memory(self.memory.memory_dir)

        # 加载技能系统
        skills_content = generate_skills_prompt(self.base_dir / "skills")

        # 构建完整 system prompt
        full_system_prompt = identity_content

        # 添加性格特征
        if soul_content:
            full_system_prompt += "\n\n" + soul_content

        # 添加技能系统
        if skills_content:
            full_system_prompt += "\n\n" + skills_content

        # 添加用户特定记忆
        if user_memory:
            full_system_prompt += f"\n\n## 用户档案\n{user_memory}"

        # 创建 Agent
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=full_system_prompt,
        )

        # 会话历史
        self.messages: list[Any] = []

        # 注册退出清理
        atexit.register(self.close)

    def close(self) -> None:
        """清理资源。"""
        if hasattr(self, 'memory') and self.memory:
            self.memory.close()
        if hasattr(self, 'bg_loop') and self.bg_loop and self._bg_started:
            self.bg_loop.stop()
            self._bg_started = False

    def ensure_background_tasks_started(self) -> None:
        """确保后台任务已启动。"""
        if not self._bg_started:
            self.bg_loop.start()
            self._bg_started = True

    async def chat(self, user_input: str) -> str:
        """发送消息给 Agent 并返回回复。"""
        # 延迟启动后台任务（第一次聊天时）
        self.ensure_background_tasks_started()

        user_msg = HumanMessage(content=user_input)
        self.messages.append(user_msg)
        self.memory.log_message(user_msg)

        # 调用 Agent
        response = await self.agent.ainvoke({"messages": self.messages})

        # 获取回复消息 (最后一条 AI 消息)
        ai_message = response["messages"][-1]
        self.messages = response["messages"]

        # 记录 AI 回复
        self.memory.log_message(ai_message)

        return ai_message.content

    async def stream_chat(self, user_input: str):
        """流式输出 Agent 的回复。"""
        self.messages.append(HumanMessage(content=user_input))

        async for chunk in self.agent.astream({"messages": self.messages}):
            if "messages" in chunk:
                # 获取最新的 AI 消息内容
                for msg in chunk["messages"]:
                    if hasattr(msg, "content"):
                        yield msg.content

    def clear_history(self):
        """清除对话历史。"""
        self.messages = []
        print("✅ 对话历史已清除")


async def interactive_mode(agent: CoreClawAgent):
    """交互式对话模式。"""
    print("=" * 60)
    print("🐾 CoreClaw Agent")
    print("=" * 60)
    print(f"模型: {agent.llm.model}")
    print(f"工具: {', '.join(t.name for t in agent.tools)}")
    print(f"记忆: {agent.memory.memory_dir}")
    print("\n命令: /quit 退出, /clear 清除历史, /tools 查看工具, /skills 查看技能, /memory 查看记忆, /task 查看任务")
    print("-" * 60)

    while True:
        try:
            # input() 是阻塞调用，放到线程中避免卡住事件循环。
            raw_input = await asyncio.to_thread(input, "\n👤 You: ")
            user_input = raw_input.strip()

            if not user_input:
                continue

            if user_input == "/quit":
                print("👋 再见!")
                break

            if user_input == "/clear":
                agent.clear_history()
                continue

            if user_input == "/tools":
                print("\n🔧 可用工具:")
                for tool in agent.tools:
                    print(f"  • {tool.name}: {tool.description[:60]}...")
                continue

            if user_input == "/skills":
                skills = scan_skills(agent.base_dir / "skills")
                if skills:
                    print(f"\n🎯 已加载 {len(skills)} 个技能:")
                    for skill in skills:
                        print(f"  • {skill['name']}: {skill['description']}")
                    print("\n使用方法: 直接描述你的需求，Agent 会自动调用相应技能")
                else:
                    print("\n📭 暂无技能，在 skills/ 目录下添加 SKILL.md 文件")
                continue

            if user_input == "/memory":
                print("\n🧠 记忆文件:")
                for name, path in agent.memory.get_memory_files().items():
                    exists = "✅" if path.exists() else "❌"
                    print(f"  {exists} {name}: {path}")
                continue

            if user_input == "/task":
                tasks = agent.bg_loop.list_tasks()
                if tasks:
                    print(f"\n⏰ 运行中的任务 ({len(tasks)}个):")
                    for task in tasks:
                        status = "🟢" if task["running"] else "🔴"
                        interval_m = task["interval"] / 60
                        interval_str = f"{int(interval_m)}分钟" if interval_m >= 1 else f"{int(task['interval'])}秒"
                        desc = task.get("description", "")
                        print(f"  {status} {task['name']}: 每{interval_str}")
                        if desc:
                            print(f"     {desc}")
                else:
                    print("\n📭 暂无运行中的任务")
                continue

            print("\n🤖 CoreClaw: ", end="", flush=True)

            response = await agent.chat(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def single_query(agent: CoreClawAgent, query: str) -> str:
    """单次查询模式。"""
    return await agent.chat(query)


def main():
    """主入口。"""
    # 检查环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 错误: DEEPSEEK_API_KEY 未设置")
        print("请设置环境变量或在 .env 文件中配置")
        sys.exit(1)

    # 创建 Agent
    base_dir = Path(__file__).parent
    agent = CoreClawAgent(base_dir=base_dir)

    # 判断模式
    if len(sys.argv) > 1:
        # 单次查询模式
        query = sys.argv[1]
        result = asyncio.run(single_query(agent, query))
        print(result)
    else:
        # 交互式模式
        asyncio.run(interactive_mode(agent))


if __name__ == "__main__":
    main()
