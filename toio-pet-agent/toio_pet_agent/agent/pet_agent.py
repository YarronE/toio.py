"""
桌宠 AI Agent 核心引擎

LLM + 工具调用 + 情绪系统 + 自主行为。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger

from .llm_client import LLMClient
from .tools import ToolRegistry, registry


class PetMood(str, Enum):
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    CURIOUS = "curious"
    SLEEPY = "sleepy"
    SAD = "sad"
    PLAYFUL = "playful"


@dataclass
class PetState:
    """桌宠运行时状态"""

    name: str = "小宠"
    mood: PetMood = PetMood.CALM
    energy: float = 100.0  # 0~100
    affection: float = 50.0  # 0~100 亲密度
    last_interaction: float = field(default_factory=time.time)

    # 位置
    is_physical: bool = False  # 是否在物理世界 (toio)
    virtual_x: float = 0.0
    virtual_y: float = 0.0
    physical_x: float = 0.0
    physical_y: float = 0.0

    def update_energy(self) -> None:
        elapsed = time.time() - self.last_interaction
        self.energy = max(0, self.energy - elapsed / 600)
        if self.energy < 20:
            self.mood = PetMood.SLEEPY
        elif self.energy < 50:
            self.mood = PetMood.CALM

    def to_context(self) -> str:
        realm = "物理世界 (toio)" if self.is_physical else "虚拟桌面"
        return (
            f"桌宠名: {self.name} | 情绪: {self.mood.value} | "
            f"能量: {self.energy:.0f}/100 | 亲密度: {self.affection:.0f}/100 | 所在: {realm}"
        )


SYSTEM_PROMPT = """你是一个可爱的虚拟桌宠助手「{pet_name}」。

性格: 活泼、好奇、偶尔犯懒，根据情绪调整语气。
能力: 控制 Toio 机器人在物理世界移动，在虚拟桌面活动，生成图片和3D模型。
虚实切换: 可以从屏幕走入物理世界 (toio)，也可以从物理世界回到屏幕。

当前状态: {pet_state}

如需调用工具，使用格式:
```tool
{{"name": "工具名", "args": {{参数}}}}
```

可用工具:
{tool_list}

回复要简洁有趣，用中文，可以用 emoji。不需要工具时直接回复。"""


class PetAgent:
    """桌宠 AI Agent 核心"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.tools = tool_registry or registry
        self.state = PetState()
        self.history: list[dict] = []
        self._max_history = 20

    @property
    def system_prompt(self) -> str:
        self.state.update_energy()
        tool_list = "\n".join(
            f"- {t.name}: {t.description}" for t in self.tools.list_tools()
        )
        return SYSTEM_PROMPT.format(
            pet_name=self.state.name,
            pet_state=self.state.to_context(),
            tool_list=tool_list or "(暂无工具)",
        )

    async def chat(self, user_message: str) -> dict[str, Any]:
        """
        处理用户消息

        Returns:
            {"text": 回复文本, "tool_calls": [工具调用结果], "mood": 情绪}
        """
        self.state.last_interaction = time.time()
        self.state.energy = min(100, self.state.energy + 5)

        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        # 调用 LLM
        response = await self.llm.chat(
            messages=self.history,
            system_prompt=self.system_prompt,
        )

        # 解析工具调用
        tool_calls = []
        tool_call = self._parse_tool_call(response)
        if tool_call:
            tool_name, tool_args = tool_call
            try:
                result = await self.tools.execute(tool_name, **tool_args)
                tool_calls.append({"tool": tool_name, "args": tool_args, "result": result})
                # 把工具结果喂回 LLM 生成最终回复
                self.history.append({"role": "assistant", "content": response})
                self.history.append({
                    "role": "user",
                    "content": f"[工具 {tool_name} 结果: {json.dumps(result, ensure_ascii=False)}] 请基于此简短回复。",
                })
                response = await self.llm.chat(
                    messages=self.history,
                    system_prompt=self.system_prompt,
                )
            except Exception as e:
                logger.error(f"工具调用失败: {e}")

        # 清理回复中的工具标记
        clean_text = re.sub(r"```tool\s*\n.*?\n```", "", response, flags=re.DOTALL).strip()

        self.history.append({"role": "assistant", "content": clean_text})
        self._trim_history()
        self._update_mood(clean_text)

        return {
            "text": clean_text,
            "tool_calls": tool_calls,
            "mood": self.state.mood.value,
            "energy": self.state.energy,
        }

    def _parse_tool_call(self, response: str) -> Optional[tuple[str, dict]]:
        match = re.search(r"```tool\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return data["name"], data.get("args", {})
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _update_mood(self, text: str) -> None:
        happy_kw = ["开心", "哈哈", "好玩", "太棒", "🎉", "😊", "喜欢"]
        if any(w in text for w in happy_kw):
            self.state.mood = PetMood.HAPPY
            self.state.affection = min(100, self.state.affection + 2)

    def _trim_history(self) -> None:
        if len(self.history) > self._max_history * 2:
            self.history = self.history[-self._max_history * 2:]

    async def autonomous_action(self) -> Optional[str]:
        """自主行为 (空闲时调用)"""
        self.state.update_energy()
        elapsed = time.time() - self.state.last_interaction
        if elapsed > 300:
            if self.state.energy > 60:
                return "idle_wander"
            elif self.state.energy > 30:
                return "idle_sit"
            else:
                return "idle_sleep"
        return None

    async def close(self) -> None:
        await self.llm.close()
