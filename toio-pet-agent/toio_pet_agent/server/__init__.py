"""
WebSocket + REST API 通信服务

连接 Python 后端 (Agent + Toio) 和前端 (Electron 桌面端 / Vision Pro AR 端)。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import websockets
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from ..agent.pet_agent import PetAgent
from ..config import get_config
from ..spatial import SpaceCoordinator


# ============================================================
# Pydantic 模型
# ============================================================

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    text: str
    mood: str
    energy: float
    tool_calls: list[dict] = []

class PetStateResponse(BaseModel):
    name: str
    mood: str
    energy: float
    affection: float
    realm: str
    virtual_pos: dict
    physical_pos: dict

class ToioCommandRequest(BaseModel):
    action: str
    params: dict = {}


# ============================================================
# REST API (FastAPI)
# ============================================================

def create_app(
    agent: PetAgent,
    coordinator: SpaceCoordinator,
) -> FastAPI:
    """创建 FastAPI 应用"""

    app = FastAPI(title="Toio Pet Agent API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        """与桌宠对话"""
        result = await agent.chat(req.message)
        return ChatResponse(**result)

    @app.get("/api/state", response_model=PetStateResponse)
    async def get_state():
        """获取桌宠状态"""
        space = coordinator.to_state_dict()
        return PetStateResponse(
            name=agent.state.name,
            mood=agent.state.mood.value,
            energy=agent.state.energy,
            affection=agent.state.affection,
            realm=space["realm"],
            virtual_pos=space["virtual_pos"],
            physical_pos=space["physical_pos"],
        )

    @app.post("/api/toio/command")
    async def toio_command(req: ToioCommandRequest):
        """直接发送 Toio 命令"""
        return {"action": req.action, "params": req.params, "status": "queued"}

    @app.post("/api/pet/name")
    async def set_pet_name(data: dict):
        """设置桌宠名字"""
        name = data.get("name", "小宠")
        agent.state.name = name
        return {"name": name}

    return app


# ============================================================
# WebSocket 服务 (实时通信)
# ============================================================

class WebSocketServer:
    """
    WebSocket 服务器

    前端通过 WS 订阅:
    - 桌宠位置实时更新
    - 情绪变化
    - 虚实过渡事件
    - Toio 状态

    前端通过 WS 发送:
    - 用户消息
    - 桌宠虚拟位置更新
    - 交互事件
    """

    def __init__(
        self,
        agent: PetAgent,
        coordinator: SpaceCoordinator,
        port: int = 8765,
    ):
        self.agent = agent
        self.coordinator = coordinator
        self.port = port
        self._clients: set[websockets.WebSocketServerProtocol] = set()
        self._server: Optional[websockets.WebSocketServer] = None

    async def start(self) -> None:
        """启动 WS 服务器"""
        self._server = await websockets.serve(
            self._handler, "0.0.0.0", self.port
        )
        logger.info(f"WebSocket 服务启动: ws://0.0.0.0:{self.port}")

    async def stop(self) -> None:
        """停止服务"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def broadcast(self, msg: dict) -> None:
        """广播消息给所有客户端"""
        if not self._clients:
            return
        data = json.dumps(msg, ensure_ascii=False)
        dead = set()
        for ws in self._clients:
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                dead.add(ws)
        self._clients -= dead

    async def _handler(
        self, ws: websockets.WebSocketServerProtocol, path: str = "/"
    ) -> None:
        """处理单个 WS 连接"""
        self._clients.add(ws)
        logger.info(f"WS 客户端连接: {ws.remote_address}")

        # 发送当前状态
        await ws.send(json.dumps({
            "type": "state",
            "data": self.coordinator.to_state_dict(),
        }, ensure_ascii=False))

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await self._handle_message(ws, msg)
                except json.JSONDecodeError:
                    await ws.send(json.dumps({"type": "error", "data": "Invalid JSON"}))
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            logger.info(f"WS 客户端断开: {ws.remote_address}")

    async def _handle_message(
        self, ws: websockets.WebSocketServerProtocol, msg: dict
    ) -> None:
        """处理客户端消息"""
        msg_type = msg.get("type", "")

        if msg_type == "chat":
            # 用户聊天消息
            user_msg = msg.get("data", {}).get("message", "")
            if user_msg:
                result = await self.agent.chat(user_msg)
                response = {"type": "chat_response", "data": result}
                await ws.send(json.dumps(response, ensure_ascii=False))
                # 广播状态更新
                await self.broadcast({
                    "type": "state_update",
                    "data": {
                        "mood": result["mood"],
                        "energy": result["energy"],
                    },
                })

        elif msg_type == "pet_position":
            # 前端报告桌宠虚拟位置
            x = msg.get("data", {}).get("x", 0)
            y = msg.get("data", {}).get("y", 0)
            edge = self.coordinator.update_virtual_pos(x, y)
            if edge:
                # 触发虚→实过渡
                transition = await self.coordinator.begin_transition_to_physical(edge)
                await self.broadcast({"type": "transition", "data": transition})

        elif msg_type == "transition_complete":
            # 前端报告过渡完成
            target = msg.get("data", {}).get("target", "")
            if target == "physical":
                pos = msg.get("data", {}).get("mat_pos", {})
                await self.coordinator.complete_transition_to_physical(
                    pos.get("x", 250), pos.get("y", 250)
                )
            elif target == "virtual":
                pos = msg.get("data", {}).get("screen_pos", {})
                await self.coordinator.complete_transition_to_virtual(
                    pos.get("x", 960), pos.get("y", 540)
                )
            await self.broadcast({
                "type": "state",
                "data": self.coordinator.to_state_dict(),
            })

        elif msg_type == "ping":
            await ws.send(json.dumps({"type": "pong"}))
