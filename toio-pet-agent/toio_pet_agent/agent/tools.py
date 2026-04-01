"""
AI Agent 工具注册框架

定义桌宠 Agent 可调用的工具集。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from loguru import logger


@dataclass
class ToolParam:
    """工具参数描述"""

    name: str
    type: str  # "string" | "number" | "boolean"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[list[str]] = None


@dataclass
class Tool:
    """可注册的 Agent 工具"""

    name: str
    description: str
    parameters: list[ToolParam] = field(default_factory=list)
    handler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
    category: str = "general"  # toio | aigc | pet | system

    def to_openai_function(self) -> dict:
        """转换为 OpenAI function calling 格式"""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name} [{tool.category}]")

    def tool(
        self,
        name: str,
        description: str,
        parameters: Optional[list[ToolParam]] = None,
        category: str = "general",
    ):
        """装饰器: 注册异步函数为工具"""

        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
            t = Tool(
                name=name,
                description=description,
                parameters=parameters or [],
                handler=func,
                category=category,
            )
            self.register(t)
            return func

        return decorator

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> list[Tool]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def to_openai_functions(self, category: Optional[str] = None) -> list[dict]:
        return [t.to_openai_function() for t in self.list_tools(category)]

    async def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"未知工具: {name}")
        if not tool.handler:
            raise ValueError(f"工具 {name} 没有注册 handler")

        logger.info(f"执行工具: {name}({kwargs})")
        try:
            result = await tool.handler(**kwargs)
            return result
        except Exception as e:
            logger.error(f"工具 {name} 执行失败: {e}")
            raise


# 全局工具注册表单例
registry = ToolRegistry()
