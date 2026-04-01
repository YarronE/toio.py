"""
Toio / 桌宠 / AIGC 工具定义

通过 runtime 上下文连接到真实的 Toio 控制器和 WebSocket 广播，
实现 Agent 工具调用 → 物理世界控制的完整闭环。
"""

from __future__ import annotations

import json

from loguru import logger

from .tools import ToolParam, registry


def _toio():
    """获取 ToioManager 实例"""
    from ..runtime import runtime
    return runtime.toio_manager


def _coord():
    """获取 SpaceCoordinator 实例"""
    from ..runtime import runtime
    return runtime.coordinator


async def _broadcast(msg: dict):
    """广播 WS 消息"""
    from ..runtime import runtime
    if runtime.ws_server:
        await runtime.ws_server.broadcast(msg)


# ============================================================
# Toio 物理控制工具
# ============================================================


@registry.tool(
    name="toio_move_forward",
    description="让 Toio 向前移动。桌宠走入物理世界后在桌上移动。",
    parameters=[
        ToolParam(name="speed", type="number", description="速度 (1-100)", default=50),
        ToolParam(name="duration_ms", type="number", description="时长(ms)", default=1000),
    ],
    category="toio",
)
async def toio_move_forward(speed: int = 50, duration_ms: int = 1000):
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        await cube.motor_timed(speed, speed, duration_ms)
        logger.info(f"Toio 前进: speed={speed}, {duration_ms}ms")
        return {"status": "ok", "action": "move_forward"}
    return {"status": "no_toio", "action": "move_forward"}


@registry.tool(
    name="toio_move_to",
    description="让 Toio 移动到 mat 上的指定坐标。",
    parameters=[
        ToolParam(name="x", type="number", description="目标 X 坐标"),
        ToolParam(name="y", type="number", description="目标 Y 坐标"),
        ToolParam(name="speed", type="number", description="最大速度", required=False, default=80),
    ],
    category="toio",
)
async def toio_move_to(x: int, y: int, speed: int = 80):
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        arrived = await cube.move_to(x, y, speed=speed, timeout=10)
        return {"status": "arrived" if arrived else "timeout", "x": x, "y": y}
    return {"status": "no_toio"}


@registry.tool(
    name="toio_turn",
    description="让 Toio 旋转到指定角度。",
    parameters=[
        ToolParam(name="angle", type="number", description="目标角度 (0-360)"),
    ],
    category="toio",
)
async def toio_turn(angle: int):
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        done = await cube.turn_to(angle, timeout=5)
        return {"status": "done" if done else "timeout", "angle": angle}
    return {"status": "no_toio"}


@registry.tool(
    name="toio_stop",
    description="让 Toio 立即停止移动。",
    parameters=[],
    category="toio",
)
async def toio_stop():
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        await cube.motor_stop()
        return {"status": "stopped"}
    return {"status": "no_toio"}


@registry.tool(
    name="toio_led",
    description="设置 Toio LED 灯颜色，表达桌宠情绪。",
    parameters=[
        ToolParam(name="r", type="number", description="红 0-255"),
        ToolParam(name="g", type="number", description="绿 0-255"),
        ToolParam(name="b", type="number", description="蓝 0-255"),
    ],
    category="toio",
)
async def toio_led(r: int, g: int, b: int):
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        await cube.led(r, g, b)
        return {"status": "ok", "color": [r, g, b]}
    return {"status": "no_toio"}


@registry.tool(
    name="toio_sound",
    description="让 Toio 播放预设音效。",
    parameters=[
        ToolParam(name="sound_id", type="number", description="音效ID (0-10)"),
    ],
    category="toio",
)
async def toio_sound(sound_id: int):
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        await cube.sound(sound_id)
        return {"status": "ok", "sound_id": sound_id}
    return {"status": "no_toio"}


# ============================================================
# 桌宠行为工具 — 通过 WS 广播给前端执行
# ============================================================


@registry.tool(
    name="pet_change_mood",
    description="改变桌宠的情绪表情和动画。",
    parameters=[
        ToolParam(
            name="mood", type="string", description="情绪类型",
            enum=["happy", "excited", "calm", "curious", "sleepy", "sad", "playful"],
        ),
    ],
    category="pet",
)
async def pet_change_mood(mood: str):
    await _broadcast({"type": "pet_command", "data": {"action": "change_mood", "mood": mood}})
    # 同步更改 Toio LED 情绪颜色
    mood_colors = {
        "happy": (255, 215, 0), "excited": (255, 107, 107),
        "calm": (135, 206, 235), "curious": (155, 89, 182),
        "sleepy": (160, 160, 192), "sad": (93, 173, 226),
        "playful": (46, 204, 113),
    }
    r, g, b = mood_colors.get(mood, (135, 206, 235))
    mgr = _toio()
    cube = mgr.get_cube(0) if mgr else None
    if cube and cube.is_connected:
        await cube.led(r, g, b, duration_ms=2000)
    return {"status": "ok", "mood": mood}


@registry.tool(
    name="pet_virtual_walk",
    description="让桌宠在虚拟桌面上走到指定屏幕位置。",
    parameters=[
        ToolParam(name="x", type="number", description="屏幕 X 坐标 (像素)"),
        ToolParam(name="y", type="number", description="屏幕 Y 坐标 (像素)"),
    ],
    category="pet",
)
async def pet_virtual_walk(x: int, y: int):
    await _broadcast({"type": "pet_command", "data": {"action": "walk_to", "x": x, "y": y}})
    coord = _coord()
    if coord:
        edge = coord.update_virtual_pos(x, y)
        if edge:
            return {"status": "reached_edge", "edge": edge}
    return {"status": "ok", "x": x, "y": y}


@registry.tool(
    name="pet_switch_realm",
    description="在虚拟世界和物理世界之间切换。桌宠从屏幕走到 Toio 上，或从 Toio 回到屏幕。",
    parameters=[
        ToolParam(name="target", type="string", description="目标世界", enum=["physical", "virtual"]),
    ],
    category="system",
)
async def pet_switch_realm(target: str):
    coord = _coord()
    if not coord:
        return {"status": "error", "msg": "空间协调器未初始化"}

    if target == "physical":
        transition = await coord.begin_transition_to_physical("bottom")
        await _broadcast({"type": "transition", "data": transition})
        # 启动 Toio
        mgr = _toio()
        cube = mgr.get_cube(0) if mgr else None
        if cube and cube.is_connected:
            entry = transition["mat_entry_pos"]
            await cube.led(255, 200, 0, duration_ms=500)
            await cube.sound(0)
        return {"status": "transitioning", "target": "physical"}
    else:
        transition = await coord.begin_transition_to_virtual()
        await _broadcast({"type": "transition", "data": transition})
        # 停止 Toio
        mgr = _toio()
        cube = mgr.get_cube(0) if mgr else None
        if cube and cube.is_connected:
            await cube.motor_stop()
            await cube.led_off()
        return {"status": "transitioning", "target": "virtual"}


# ============================================================
# AIGC 生成工具
# ============================================================


@registry.tool(
    name="generate_image",
    description="根据文字描述生成图片。可用于创建桌宠形象、表情变体等。",
    parameters=[
        ToolParam(name="prompt", type="string", description="图片描述 (英文)"),
        ToolParam(name="style", type="string", description="风格", required=False,
                  enum=["pixel", "anime", "chibi", "realistic"]),
    ],
    category="aigc",
)
async def generate_image(prompt: str, style: str = "chibi"):
    from ..aigc import ImageGenerator
    gen = ImageGenerator()
    try:
        result = await gen.generate(prompt, style=style)
        await _broadcast({"type": "image_generated", "data": {"url": result, "prompt": prompt}})
        return {"status": "ok", "image": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        await gen.close()


@registry.tool(
    name="generate_3d_model",
    description="从图片或描述生成 3D 模型 (用于 Vision Pro AR 显示)。",
    parameters=[
        ToolParam(name="image_path", type="string", description="输入图片路径", required=False),
        ToolParam(name="prompt", type="string", description="3D 模型描述", required=False),
    ],
    category="aigc",
)
async def generate_3d_model(image_path: str = "", prompt: str = ""):
    from ..aigc import Model3DGenerator
    gen = Model3DGenerator()
    try:
        result = await gen.generate(image_path=image_path or None, prompt=prompt or None)
        await _broadcast({"type": "model3d_generated", "data": {"url": result}})
        return {"status": "ok", "model": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        await gen.close()
