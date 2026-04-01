"""
Toio Pet Agent 主入口

启动所有服务: Agent + Toio BLE + WebSocket + REST API
"""

from __future__ import annotations

import asyncio
import signal
import sys

import uvicorn
from loguru import logger

from .agent.pet_agent import PetAgent
from .agent import pet_tools  # noqa: F401 — 注册工具
from .config import get_config
from .server import WebSocketServer, create_app
from .spatial import SpaceCoordinator
from .toio.controller import ToioManager


async def run_api_server(app, port: int) -> None:
    """后台运行 FastAPI"""
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def async_main() -> None:
    """异步主函数"""
    cfg = get_config()

    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level=cfg.log_level)
    logger.add(cfg.log_file, rotation="10 MB", level="DEBUG")
    logger.info("=" * 50)
    logger.info("🐾 Toio Pet Agent 启动中...")
    logger.info(f"   LLM: {cfg.llm.provider} ({cfg.llm.ollama_model if cfg.llm.provider == 'ollama' else cfg.llm.openai_model})")
    logger.info(f"   API: http://0.0.0.0:{cfg.server.api_port}")
    logger.info(f"   WS:  ws://0.0.0.0:{cfg.server.websocket_port}")
    logger.info("=" * 50)

    # 初始化组件
    agent = PetAgent()
    coordinator = SpaceCoordinator()
    toio_manager = ToioManager()
    ws_server = WebSocketServer(agent, coordinator, port=cfg.server.websocket_port)
    api_app = create_app(agent, coordinator)

    # 注册运行时上下文 — 让 Agent 工具能访问 Toio/WS/Coordinator
    from .runtime import runtime
    runtime.register(
        toio_manager=toio_manager,
        coordinator=coordinator,
        ws_server=ws_server,
    )

    # 可选: 自动连接 Toio
    if cfg.toio.auto_connect:
        logger.info("扫描 Toio 设备...")
        try:
            cubes = await toio_manager.scan_and_connect()
            if cubes:
                logger.info(f"✅ 已连接 {len(cubes)} 个 Toio")
            else:
                logger.warning("⚠️ 未找到 Toio 设备，仅启用虚拟模式")
        except Exception as e:
            logger.warning(f"⚠️ Toio 连接失败: {e}，仅启用虚拟模式")

    # 启动 WebSocket
    await ws_server.start()

    # 自主行为循环 (后台)
    async def autonomous_loop():
        while True:
            try:
                action = await agent.autonomous_action()
                if action:
                    await ws_server.broadcast({
                        "type": "autonomous_action",
                        "data": {"action": action, "mood": agent.state.mood.value},
                    })
            except Exception as e:
                logger.error(f"自主行为错误: {e}")
            await asyncio.sleep(30)

    # 位置同步循环 (Toio → 前端)
    async def toio_sync_loop():
        while True:
            cube = toio_manager.get_cube(0)
            if cube and cube.is_connected and cube.position:
                pos = cube.position
                coordinator.update_physical_pos(pos.center_x, pos.center_y)
                await ws_server.broadcast({
                    "type": "toio_position",
                    "data": {
                        "x": pos.center_x,
                        "y": pos.center_y,
                        "angle": pos.center_angle,
                    },
                })
            await asyncio.sleep(0.1)

    # 并发运行所有服务
    try:
        await asyncio.gather(
            run_api_server(api_app, cfg.server.api_port),
            autonomous_loop(),
            toio_sync_loop(),
        )
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("正在关闭...")
        await ws_server.stop()
        await toio_manager.disconnect_all()
        await agent.close()
        logger.info("🐾 Toio Pet Agent 已停止")


def main() -> None:
    """同步入口 (CLI 命令)"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n🐾 再见！")


if __name__ == "__main__":
    main()
