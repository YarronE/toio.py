"""
Toio BLE 异步控制器

使用 bleak 实现跨平台 (Windows/macOS/Linux) 的 BLE 通信。
核心类 ToioCube 表示一个 toio Core Cube 设备。
"""

from __future__ import annotations

import asyncio
import math
from typing import Callable, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from loguru import logger

from ..config import get_config
from .protocol import (
    BatteryLevel,
    ButtonState,
    PositionID,
    SensorData,
    decode_battery,
    decode_button,
    decode_position_id,
    decode_sensor,
    encode_light,
    encode_light_off,
    encode_light_sequence,
    encode_motor,
    encode_motor_stop,
    encode_motor_target,
    encode_motor_timed,
    encode_sound,
    encode_sound_stop,
    hsv_to_rgb,
)


class ToioCube:
    """
    单个 toio Core Cube 的异步控制器

    Usage:
        cube = ToioCube()
        await cube.connect()
        await cube.motor(50, 50)
        await cube.led(255, 0, 0)
        pos = await cube.get_position()
        await cube.disconnect()
    """

    def __init__(self, device: Optional[BLEDevice] = None):
        self._device = device
        self._client: Optional[BleakClient] = None
        self._connected = False

        # 缓存的传感器数据 (通过 notify 实时更新)
        self._position: Optional[PositionID] = None
        self._sensor: Optional[SensorData] = None
        self._button: Optional[ButtonState] = None
        self._battery: Optional[BatteryLevel] = None

        # 回调
        self._on_position: Optional[Callable[[PositionID], None]] = None
        self._on_button: Optional[Callable[[ButtonState], None]] = None
        self._on_sensor: Optional[Callable[[SensorData], None]] = None

        self._cfg = get_config().toio

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    @property
    def position(self) -> Optional[PositionID]:
        """最近一次的位置数据 (通过 notify 实时更新)"""
        return self._position

    # ----------------------------------------------------------
    # 连接管理
    # ----------------------------------------------------------

    async def connect(self, device: Optional[BLEDevice] = None) -> None:
        """连接到 toio 设备"""
        if device:
            self._device = device

        if self._device is None:
            raise ValueError("未指定 BLE 设备，请先扫描或传入 device")

        logger.info(f"连接 toio: {self._device.name} ({self._device.address})")
        self._client = BleakClient(self._device, timeout=self._cfg.scan_timeout)
        await self._client.connect()
        self._connected = True
        logger.info(f"已连接 toio: {self._device.address}")

        # 订阅 notify
        await self._subscribe_notifications()

    async def disconnect(self) -> None:
        """断开连接"""
        if self._client and self._connected:
            try:
                await self.motor_stop()
                await self.led_off()
            except Exception:
                pass
            await self._client.disconnect()
            self._connected = False
            logger.info("已断开 toio")

    async def _subscribe_notifications(self) -> None:
        """订阅所有传感器的 notify"""
        if not self._client:
            return

        # 位置 ID
        await self._client.start_notify(
            self._cfg.id_uuid, self._handle_position_notify
        )
        # 运动传感器
        await self._client.start_notify(
            self._cfg.sensor_uuid, self._handle_sensor_notify
        )
        # 按钮
        await self._client.start_notify(
            self._cfg.button_uuid, self._handle_button_notify
        )

    def _handle_position_notify(self, _sender: int, data: bytearray) -> None:
        """位置 notify 回调"""
        pos = decode_position_id(bytes(data))
        if pos:
            self._position = pos
            if self._on_position:
                self._on_position(pos)

    def _handle_sensor_notify(self, _sender: int, data: bytearray) -> None:
        """传感器 notify 回调"""
        sensor = decode_sensor(bytes(data))
        if sensor:
            self._sensor = sensor
            if self._on_sensor:
                self._on_sensor(sensor)

    def _handle_button_notify(self, _sender: int, data: bytearray) -> None:
        """按钮 notify 回调"""
        btn = decode_button(bytes(data))
        if btn:
            self._button = btn
            if self._on_button:
                self._on_button(btn)

    # ----------------------------------------------------------
    # 电机控制
    # ----------------------------------------------------------

    async def motor(self, left: int, right: int) -> None:
        """设置左右电机速度 (-100 ~ 100)"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.motor_uuid, encode_motor(left, right)
        )

    async def motor_timed(self, left: int, right: int, duration_ms: int) -> None:
        """带时长的电机控制"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.motor_uuid, encode_motor_timed(left, right, duration_ms)
        )

    async def motor_target(
        self,
        target_x: int,
        target_y: int,
        target_angle: int = 0,
        max_speed: int = 80,
        request_id: int = 0,
    ) -> None:
        """目标指定移动 (toio 内置寻路)"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.motor_uuid,
            encode_motor_target(
                request_id=request_id,
                timeout=5,
                move_type=0,
                max_speed=max_speed,
                speed_change=3,  # 先加后减
                target_x=target_x,
                target_y=target_y,
                target_angle=target_angle,
            ),
        )

    async def motor_stop(self) -> None:
        """停止电机"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.motor_uuid, encode_motor_stop()
        )

    # ----------------------------------------------------------
    # LED 灯光
    # ----------------------------------------------------------

    async def led(self, r: int, g: int, b: int, duration_ms: int = 0) -> None:
        """设置 LED 颜色"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.light_uuid, encode_light(duration_ms, r, g, b)
        )

    async def led_sequence(
        self, repeat: int, frames: list[tuple[int, int, int, int]]
    ) -> None:
        """LED 灯光序列"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.light_uuid, encode_light_sequence(repeat, frames)
        )

    async def led_off(self) -> None:
        """关闭 LED"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.light_uuid, encode_light_off()
        )

    # ----------------------------------------------------------
    # 音效
    # ----------------------------------------------------------

    async def sound(self, sound_id: int, volume: int = 255) -> None:
        """播放预设音效"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.sound_uuid, encode_sound(sound_id, volume)
        )

    async def sound_stop(self) -> None:
        """停止音效"""
        if not self._client or not self._connected:
            return
        await self._client.write_gatt_char(
            self._cfg.sound_uuid, encode_sound_stop()
        )

    # ----------------------------------------------------------
    # 传感器读取
    # ----------------------------------------------------------

    async def get_position(self) -> Optional[PositionID]:
        """读取当前位置 (也可直接访问 self.position 获取 notify 缓存)"""
        if not self._client or not self._connected:
            return None
        data = await self._client.read_gatt_char(self._cfg.id_uuid)
        pos = decode_position_id(bytes(data))
        if pos:
            self._position = pos
        return pos

    async def get_battery(self) -> Optional[BatteryLevel]:
        """读取电池电量"""
        if not self._client or not self._connected:
            return None
        data = await self._client.read_gatt_char(self._cfg.battery_uuid)
        bat = decode_battery(bytes(data))
        if bat:
            self._battery = bat
        return bat

    # ----------------------------------------------------------
    # 高级运动 (从旧版 PID 控制迁移)
    # ----------------------------------------------------------

    async def move_to(
        self,
        x: int,
        y: int,
        speed: int = 80,
        threshold: int = 50,
        use_easing: bool = True,
        timeout: float = 10.0,
    ) -> bool:
        """
        PID 控制移动到目标点 (软件层实现)

        Args:
            x, y: 目标坐标
            speed: 最大速度
            threshold: 到达判定距离
            use_easing: 是否减速缓动
            timeout: 超时时间(秒)

        Returns:
            是否到达目标
        """
        # PID 参数
        kp, ki, kd = 1.0, 0.94, 0.05
        integral = 0.0
        last_error = 0.0
        dt = 0.1
        windup_guard = 20.0

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                await self.motor_stop()
                return False

            pos = self.position  # 使用 notify 缓存
            if pos is None:
                pos = await self.get_position()
            if pos is None:
                await asyncio.sleep(0.05)
                continue

            dx = x - pos.center_x
            dy = y - pos.center_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < threshold:
                await self.motor_stop()
                return True

            # 计算角度偏差
            target_angle = math.degrees(math.atan2(dy, dx))
            rel_angle = (target_angle - pos.center_angle) % 360
            if rel_angle > 180:
                rel_angle -= 360

            # PID 控制
            error = -rel_angle
            integral += error * dt
            integral = max(-windup_guard, min(windup_guard, integral))
            derivative = (error - last_error) / dt
            last_error = error

            pid_output = kp * error + ki * integral + kd * derivative
            pid_output = max(-90, min(90, pid_output))

            # 计算速度
            if use_easing:
                actual_speed = self._easing(distance, speed, 50)
            else:
                actual_speed = speed

            # 差速驱动
            ratio = 1 - abs(pid_output) / 90.0
            if pid_output < 0:
                left, right = actual_speed, int(actual_speed * ratio)
            else:
                left, right = int(actual_speed * ratio), actual_speed

            await self.motor(left, right)
            await asyncio.sleep(0.02)

    async def turn_to(
        self,
        target_angle: int,
        speed: int = 80,
        threshold: int = 3,
        use_easing: bool = True,
        timeout: float = 5.0,
    ) -> bool:
        """旋转到目标角度"""
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                await self.motor_stop()
                return False

            pos = self.position or await self.get_position()
            if pos is None:
                await asyncio.sleep(0.05)
                continue

            diff = (target_angle - pos.center_angle) % 360
            if diff > 180:
                direction = -1
                dist = 360 - diff
            else:
                direction = 1
                dist = diff

            if dist < threshold:
                await self.motor_stop()
                return True

            if use_easing:
                s = self._easing(dist, speed) * direction
            else:
                s = speed * direction

            await self.motor(s, -s)
            await asyncio.sleep(0.02)

    @staticmethod
    def _easing(value: float, max_speed: int, max_value: float = 180.0) -> int:
        """减速缓动"""
        min_speed = 10
        ratio = min(1.0, value / max_value)
        return int(min_speed + (max_speed - min_speed) * ratio)


# ============================================================
# Toio 设备管理器
# ============================================================

class ToioManager:
    """
    管理多个 toio 设备的扫描、连接、断开

    Usage:
        manager = ToioManager()
        cubes = await manager.scan_and_connect(max_cubes=2)
        for cube in cubes:
            await cube.motor(50, 50)
        await manager.disconnect_all()
    """

    def __init__(self):
        self._cubes: list[ToioCube] = []
        self._cfg = get_config().toio

    @property
    def cubes(self) -> list[ToioCube]:
        return self._cubes

    def get_cube(self, index: int = 0) -> Optional[ToioCube]:
        """获取指定索引的 cube"""
        if 0 <= index < len(self._cubes):
            return self._cubes[index]
        return None

    async def scan(self, timeout: float = 10.0) -> list[BLEDevice]:
        """扫描附近的 toio 设备"""
        logger.info(f"扫描 toio 设备 (超时 {timeout}s)...")

        devices = await BleakScanner.discover(
            timeout=timeout,
            service_uuids=[self._cfg.service_uuid],
        )

        toio_devices = [
            d for d in devices
            if d.name and "toio" in d.name.lower()
        ]

        logger.info(f"发现 {len(toio_devices)} 个 toio 设备")
        for d in toio_devices:
            logger.info(f"  - {d.name} ({d.address})")

        return toio_devices

    async def scan_and_connect(
        self, max_cubes: Optional[int] = None
    ) -> list[ToioCube]:
        """扫描并连接 toio 设备"""
        if max_cubes is None:
            max_cubes = self._cfg.max_cubes

        devices = await self.scan(timeout=self._cfg.scan_timeout)
        devices = devices[:max_cubes]

        for device in devices:
            cube = ToioCube(device)
            try:
                await cube.connect()
                self._cubes.append(cube)
                # 用不同颜色标识
                idx = len(self._cubes) - 1
                r, g, b = hsv_to_rgb(360 * idx / max(max_cubes, 1), 255, 255)
                await cube.led(r, g, b, duration_ms=1000)
                await cube.sound(0)
            except Exception as e:
                logger.error(f"连接 {device.name} 失败: {e}")

        logger.info(f"已连接 {len(self._cubes)} 个 toio")
        return self._cubes

    async def disconnect_all(self) -> None:
        """断开所有设备"""
        for cube in self._cubes:
            try:
                await cube.disconnect()
            except Exception as e:
                logger.warning(f"断开失败: {e}")
        self._cubes.clear()
        logger.info("已断开所有 toio")
