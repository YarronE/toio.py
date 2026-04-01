"""
Toio BLE 消息编解码器

将 toio Core Cube 的 BLE 特征值编码为字节序列 / 从字节序列解码。
从旧版 toio_message.py 迁移并升级到 Python3 + bytes 原生操作。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PositionID:
    """位置检测 ID (Position ID)"""
    center_x: int
    center_y: int
    center_angle: int
    sensor_x: int
    sensor_y: int
    sensor_angle: int


@dataclass
class SensorData:
    """姿态传感器"""
    is_level: bool  # 水平检测
    is_collision: bool  # 碰撞检测
    is_double_tap: bool  # 双击检测
    orientation: int  # 姿态方向 (1-6)


@dataclass
class MotionData:
    """运动传感器 (toio v2.3.0+)"""
    is_flat: bool
    is_collision: bool
    is_double_tap: bool
    orientation: int
    is_shaking: int  # 0=无, 1-10=摇晃强度


@dataclass
class ButtonState:
    """按钮状态"""
    pressed: bool


@dataclass
class BatteryLevel:
    """电池电量"""
    level: int  # 0-100


# ============================================================
# 电机命令编码
# ============================================================

def encode_motor(left: int, right: int) -> bytes:
    """
    编码电机控制命令 (不带时长)

    Args:
        left: 左电机速度 -100~100
        right: 右电机速度 -100~100
    """
    left = max(-100, min(100, int(left)))
    right = max(-100, min(100, int(right)))

    left_dir = 0x02 if left < 0 else 0x01  # 0x01=正转, 0x02=反转
    right_dir = 0x02 if right < 0 else 0x01

    return bytes([
        0x01,  # 控制类型: 无时长电机控制
        0x01,  # 左电机ID
        left_dir,
        abs(left),
        0x02,  # 右电机ID
        right_dir,
        abs(right),
    ])


def encode_motor_timed(left: int, right: int, duration_ms: int) -> bytes:
    """
    编码带时长的电机控制命令

    Args:
        left: 左电机速度 -100~100
        right: 右电机速度 -100~100
        duration_ms: 运行时长 0~2550 (精度10ms)
    """
    left = max(-100, min(100, int(left)))
    right = max(-100, min(100, int(right)))
    duration_ms = max(0, min(2550, int(duration_ms)))

    left_dir = 0x02 if left < 0 else 0x01
    right_dir = 0x02 if right < 0 else 0x01

    return bytes([
        0x02,  # 控制类型: 有时长电机控制
        0x01,  # 左电机ID
        left_dir,
        abs(left),
        0x02,  # 右电机ID
        right_dir,
        abs(right),
        duration_ms // 10,
    ])


def encode_motor_target(
    request_id: int,
    timeout: int,
    move_type: int,
    max_speed: int,
    speed_change: int,
    target_x: int,
    target_y: int,
    target_angle: int,
) -> bytes:
    """
    编码目标指定电机控制 (toio v2.1.0+)

    Args:
        request_id: 请求ID (0-255)
        timeout: 超时 (秒, 0=10秒)
        move_type: 移动类型 (0=旋转后前进, 1=边旋转边前进, 2=旋转后前进(反向))
        max_speed: 最大速度 (10-255)
        speed_change: 速度变化类型 (0=匀速, 1=加速, 2=减速, 3=先加后减)
        target_x: 目标X
        target_y: 目标Y
        target_angle: 目标角度 (0-0x1FFF, 或含旋转模式标记)
    """
    return bytes([
        0x03,  # 控制类型: 目标指定控制
        request_id & 0xFF,
        timeout & 0xFF,
        move_type & 0xFF,
        max_speed & 0xFF,
        speed_change & 0xFF,
    ]) + struct.pack("<HHH", target_x, target_y, target_angle)


def encode_motor_stop() -> bytes:
    """编码电机停止命令"""
    return encode_motor(0, 0)


# ============================================================
# LED 灯光命令编码
# ============================================================

def encode_light(duration_ms: int, r: int, g: int, b: int) -> bytes:
    """
    编码 LED 灯光控制

    Args:
        duration_ms: 持续时间 0~2550 (精度10ms, 0=持续)
        r, g, b: 颜色 0~255
    """
    return bytes([
        0x03,  # 控制类型: 指定点亮
        duration_ms // 10,
        0x01,  # 灯数量
        0x01,  # LED ID
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    ])


def encode_light_sequence(
    repeat: int,
    frames: list[tuple[int, int, int, int]],
) -> bytes:
    """
    编码 LED 灯光序列

    Args:
        repeat: 重复次数 (0=无限)
        frames: [(duration_ms, r, g, b), ...]
    """
    data = bytearray([
        0x04,  # 控制类型: 连续点亮
        repeat & 0xFF,
        len(frames) & 0xFF,
    ])
    for dur, r, g, b in frames:
        data.extend([
            dur // 10,
            0x01,  # 灯数量
            0x01,  # LED ID
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        ])
    return bytes(data)


def encode_light_off() -> bytes:
    """编码灯光关闭"""
    return bytes([0x01])


# ============================================================
# 音效命令编码
# ============================================================

def encode_sound(sound_id: int, volume: int = 255) -> bytes:
    """
    编码预设音效播放

    Args:
        sound_id: 音效ID (0-10)
        volume: 音量 (0-255)
    """
    return bytes([
        0x02,  # 控制类型: 预设音效
        sound_id & 0xFF,
        volume & 0xFF,
    ])


def encode_sound_stop() -> bytes:
    """编码停止音效"""
    return bytes([0x01])


# ============================================================
# 传感器数据解码
# ============================================================

def decode_position_id(data: bytes) -> Optional[PositionID]:
    """
    解码位置检测ID

    Args:
        data: 从 ID 特征收到的原始字节
    """
    if len(data) < 1:
        return None

    info_type = data[0]

    if info_type == 0x01 and len(data) >= 13:
        # Position ID
        cx, cy, ca = struct.unpack_from("<HHH", data, 1)
        sx, sy, sa = struct.unpack_from("<HHH", data, 7)
        return PositionID(
            center_x=cx, center_y=cy, center_angle=ca,
            sensor_x=sx, sensor_y=sy, sensor_angle=sa,
        )

    if info_type == 0x03:
        # Position ID missed (离开 mat)
        return None

    return None


def decode_sensor(data: bytes) -> Optional[SensorData]:
    """解码姿态传感器"""
    if len(data) < 3:
        return None
    return SensorData(
        is_level=bool(data[1]),
        is_collision=bool(data[2]),
        is_double_tap=bool(data[3]) if len(data) > 3 else False,
        orientation=data[4] if len(data) > 4 else 1,
    )


def decode_button(data: bytes) -> Optional[ButtonState]:
    """解码按钮状态"""
    if len(data) < 2:
        return None
    return ButtonState(pressed=data[1] == 0x80)


def decode_battery(data: bytes) -> Optional[BatteryLevel]:
    """解码电池电量"""
    if len(data) < 1:
        return None
    return BatteryLevel(level=data[0])


# ============================================================
# 颜色工具
# ============================================================

def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """
    HSV → RGB 转换

    Args:
        h: 色相 0~360
        s: 饱和度 0~255
        v: 明度 0~255
    """
    if h is None:
        return (0, 0, 0)

    i = int(h / 60.0)
    mx = v
    mn = v - ((s / 255.0) * v)

    if i == 0:
        r, g, b = mx, (h / 60.0) * (mx - mn) + mn, mn
    elif i == 1:
        r, g, b = ((120.0 - h) / 60.0) * (mx - mn) + mn, mx, mn
    elif i == 2:
        r, g, b = mn, mx, ((h - 120.0) / 60.0) * (mx - mn) + mn
    elif i == 3:
        r, g, b = mn, ((240.0 - h) / 60.0) * (mx - mn) + mn, mx
    elif i == 4:
        r, g, b = ((h - 240.0) / 60.0) * (mx - mn) + mn, mn, mx
    else:
        r, g, b = mx, mn, ((360.0 - h) / 60.0) * (mx - mn) + mn

    return (int(r), int(g), int(b))
