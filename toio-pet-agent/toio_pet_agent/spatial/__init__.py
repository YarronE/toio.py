"""
空间协调器

管理虚拟桌面坐标 ↔ Toio 物理坐标的映射，以及虚实切换过渡逻辑。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from loguru import logger


class Realm(str, Enum):
    """桌宠所在世界"""
    VIRTUAL = "virtual"   # 虚拟桌面
    PHYSICAL = "physical"  # 物理世界 (toio)
    TRANSITION = "transition"  # 过渡中


@dataclass
class ScreenConfig:
    """屏幕参数"""
    width: int = 1920
    height: int = 1080
    # 屏幕边缘触发区域 (像素)
    edge_margin: int = 30
    # toio mat 相对屏幕的方位
    mat_direction: str = "bottom"  # bottom | right | left | top


@dataclass
class ToioMatConfig:
    """Toio mat 坐标范围 (Position ID)"""
    x_min: int = 45
    x_max: int = 455
    y_min: int = 45
    y_max: int = 455


@dataclass
class CalibrationData:
    """空间校准数据 — 屏幕边缘对应 mat 上的入口点"""
    # 屏幕下方 → mat 顶部入口
    screen_bottom_to_mat: tuple[int, int] = (250, 50)
    # 屏幕右侧 → mat 左侧入口
    screen_right_to_mat: tuple[int, int] = (455, 250)
    # 屏幕左侧 → mat 右侧入口
    screen_left_to_mat: tuple[int, int] = (45, 250)
    # 屏幕上方 → mat 底部入口
    screen_top_to_mat: tuple[int, int] = (250, 455)


class SpaceCoordinator:
    """
    虚实空间协调器

    职责:
    1. 检测桌宠是否走到屏幕边缘 → 触发虚→实过渡
    2. 屏幕坐标 ↔ mat 坐标映射
    3. 管理过渡状态机
    """

    def __init__(
        self,
        screen: Optional[ScreenConfig] = None,
        mat: Optional[ToioMatConfig] = None,
        calibration: Optional[CalibrationData] = None,
    ):
        self.screen = screen or ScreenConfig()
        self.mat = mat or ToioMatConfig()
        self.calibration = calibration or CalibrationData()
        self.realm = Realm.VIRTUAL

        # 桌宠当前位置
        self.virtual_pos: tuple[float, float] = (
            self.screen.width / 2,
            self.screen.height / 2,
        )
        self.physical_pos: tuple[float, float] = (250, 250)

    def check_screen_edge(self, x: float, y: float) -> Optional[str]:
        """
        检测桌宠是否到达屏幕边缘

        Returns:
            "bottom" | "right" | "left" | "top" | None
        """
        m = self.screen.edge_margin
        if y >= self.screen.height - m:
            return "bottom"
        if x >= self.screen.width - m:
            return "right"
        if x <= m:
            return "left"
        if y <= m:
            return "top"
        return None

    def get_mat_entry_point(self, edge: str) -> tuple[int, int]:
        """获取从屏幕边缘进入 mat 的入口点坐标"""
        mapping = {
            "bottom": self.calibration.screen_bottom_to_mat,
            "right": self.calibration.screen_right_to_mat,
            "left": self.calibration.screen_left_to_mat,
            "top": self.calibration.screen_top_to_mat,
        }
        return mapping.get(edge, (250, 250))

    def screen_to_mat(self, sx: float, sy: float) -> tuple[int, int]:
        """屏幕坐标 → mat 坐标 (线性映射)"""
        mat_w = self.mat.x_max - self.mat.x_min
        mat_h = self.mat.y_max - self.mat.y_min
        mx = int(self.mat.x_min + (sx / self.screen.width) * mat_w)
        my = int(self.mat.y_min + (sy / self.screen.height) * mat_h)
        return (
            max(self.mat.x_min, min(self.mat.x_max, mx)),
            max(self.mat.y_min, min(self.mat.y_max, my)),
        )

    def mat_to_screen(self, mx: float, my: float) -> tuple[int, int]:
        """mat 坐标 → 屏幕坐标"""
        mat_w = self.mat.x_max - self.mat.x_min
        mat_h = self.mat.y_max - self.mat.y_min
        sx = int(((mx - self.mat.x_min) / mat_w) * self.screen.width)
        sy = int(((my - self.mat.y_min) / mat_h) * self.screen.height)
        return (
            max(0, min(self.screen.width, sx)),
            max(0, min(self.screen.height, sy)),
        )

    async def begin_transition_to_physical(self, edge: str) -> dict:
        """
        开始虚→实过渡

        Returns:
            过渡参数 (供前端和 toio 控制使用)
        """
        self.realm = Realm.TRANSITION
        entry = self.get_mat_entry_point(edge)
        logger.info(f"虚→实过渡: 屏幕{edge} → mat入口{entry}")

        return {
            "type": "virtual_to_physical",
            "edge": edge,
            "screen_exit_pos": self.virtual_pos,
            "mat_entry_pos": entry,
            "animation": "jump_out",  # 前端播放跳出动画
        }

    async def complete_transition_to_physical(self, mat_x: int, mat_y: int) -> None:
        """过渡完成: 桌宠已在物理世界"""
        self.realm = Realm.PHYSICAL
        self.physical_pos = (mat_x, mat_y)
        logger.info(f"已切换到物理世界: ({mat_x}, {mat_y})")

    async def begin_transition_to_virtual(self) -> dict:
        """开始实→虚过渡"""
        self.realm = Realm.TRANSITION
        # 根据 toio 当前位置映射到屏幕
        screen_pos = self.mat_to_screen(*self.physical_pos)
        logger.info(f"实→虚过渡: mat{self.physical_pos} → 屏幕{screen_pos}")

        return {
            "type": "physical_to_virtual",
            "mat_exit_pos": self.physical_pos,
            "screen_entry_pos": screen_pos,
            "animation": "jump_in",
        }

    async def complete_transition_to_virtual(self, sx: int, sy: int) -> None:
        """过渡完成: 桌宠已回到虚拟桌面"""
        self.realm = Realm.VIRTUAL
        self.virtual_pos = (sx, sy)
        logger.info(f"已切换到虚拟桌面: ({sx}, {sy})")

    def update_virtual_pos(self, x: float, y: float) -> Optional[str]:
        """
        更新虚拟位置，并检测是否触发过渡

        Returns:
            触发的边缘方向，或 None
        """
        self.virtual_pos = (x, y)
        if self.realm == Realm.VIRTUAL:
            return self.check_screen_edge(x, y)
        return None

    def update_physical_pos(self, x: float, y: float) -> None:
        """更新物理位置 (来自 toio 传感器)"""
        self.physical_pos = (x, y)

    def to_state_dict(self) -> dict:
        """导出当前空间状态 (供 WebSocket 广播)"""
        return {
            "realm": self.realm.value,
            "virtual_pos": {"x": self.virtual_pos[0], "y": self.virtual_pos[1]},
            "physical_pos": {"x": self.physical_pos[0], "y": self.physical_pos[1]},
        }
