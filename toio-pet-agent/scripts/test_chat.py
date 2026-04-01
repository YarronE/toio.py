"""
快速 Agent 对话测试

不需要 Toio 硬件，仅测试 LLM 对话和工具调用。
需要先启动 Ollama: ollama serve
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from toio_pet_agent.agent.pet_agent import PetAgent
from toio_pet_agent.agent import pet_tools  # noqa: F401


async def main():
    print("🐾 Toio Pet Agent 对话测试")
    print("=" * 40)
    print("输入消息与桌宠聊天 (输入 quit 退出)")
    print()

    agent = PetAgent()
    agent.state.name = "小团子"

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        try:
            result = await agent.chat(user_input)
            print(f"🐾 {agent.state.name}: {result['text']}")
            if result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    print(f"   [工具] {tc['tool']}: {tc['result']}")
            print(f"   (情绪: {result['mood']}, 能量: {result['energy']:.0f})")
            print()
        except Exception as e:
            print(f"❌ 错误: {e}")
            print("   请确保 Ollama 已启动: ollama serve")
            print()

    await agent.close()
    print("\n🐾 再见!")


if __name__ == "__main__":
    asyncio.run(main())
