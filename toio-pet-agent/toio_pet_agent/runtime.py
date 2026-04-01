"""
运行时上下文 — 全局服务实例注册中心

将 ToioManager、SpaceCoordinator、WebSocketServer 等运行时实例
注入到 Agent 工具中，实现工具调用 → 真实硬件控制的闭环。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .server import WebSocketServer
    from .spatial import SpaceCoordinator
    from .toio.controller import ToioManager


class _RuntimeContext:
    """运行时服务定位器 (单例)"""

    def __init__(self):
        self.toio_manager: Optional[ToioManager] = None
        self.coordinator: Optional[SpaceCoordinator] = None
        self.ws_server: Optional[WebSocketServer] = None

    def register(
        self,
        toio_manager: Optional[ToioManager] = None,
        coordinator: Optional[SpaceCoordinator] = None,
        ws_server: Optional[WebSocketServer] = None,
    ) -> None:
        if toio_manager is not None:
            self.toio_manager = toio_manager
        if coordinator is not None:
            self.coordinator = coordinator
        if ws_server is not None:
            self.ws_server = ws_server


# 全局单例
runtime = _RuntimeContext()
