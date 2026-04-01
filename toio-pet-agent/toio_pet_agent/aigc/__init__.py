"""
AIGC 生成管线

桌宠形象创建 — 文生图、图生3D 等 API 调用封装。
"""

from __future__ import annotations

from typing import Optional

import httpx
from loguru import logger

from ..config import get_config


class ImageGenerator:
    """
    文生图调用器

    支持 ComfyUI 本地 和 远程 API 两种模式。
    """

    def __init__(self):
        self._cfg = get_config().aigc
        self._http = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        style: str = "chibi",
        width: int = 512,
        height: int = 512,
    ) -> Optional[str]:
        """
        生成图片

        Args:
            prompt: 英文描述
            style: 风格预设 (pixel/anime/chibi/realistic)
            width, height: 尺寸

        Returns:
            生成的图片路径/URL，失败返回 None
        """
        style_prompts = {
            "pixel": "pixel art style, cute, game sprite, ",
            "anime": "anime style, cute character, ",
            "chibi": "chibi style, kawaii, cute mascot, ",
            "realistic": "3d render, cute figurine, ",
        }
        full_prompt = style_prompts.get(style, "") + prompt

        if self._cfg.image_gen_provider == "comfyui":
            return await self._generate_comfyui(full_prompt, width, height)
        else:
            return await self._generate_api(full_prompt, width, height)

    async def _generate_comfyui(
        self, prompt: str, width: int, height: int
    ) -> Optional[str]:
        """ComfyUI 本地调用 (简化版 — 后续接入完整 workflow)"""
        logger.info(f"ComfyUI 生图: {prompt[:50]}...")
        # TODO: 接入 ComfyUI WebSocket API 和 workflow
        # 当前返回占位
        return f"[comfyui] generated: {prompt[:30]}"

    async def _generate_api(
        self, prompt: str, width: int, height: int
    ) -> Optional[str]:
        """远程生图 API 调用"""
        if not self._cfg.image_gen_api_url or not self._cfg.image_gen_api_key:
            logger.warning("未配置生图 API")
            return None

        logger.info(f"远程生图: {prompt[:50]}...")
        try:
            resp = await self._http.post(
                self._cfg.image_gen_api_url,
                headers={"Authorization": f"Bearer {self._cfg.image_gen_api_key}"},
                json={"prompt": prompt, "width": width, "height": height},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("url") or data.get("image_url")
        except Exception as e:
            logger.error(f"生图 API 失败: {e}")
            return None

    async def close(self) -> None:
        await self._http.aclose()


class Model3DGenerator:
    """
    图/文 → 3D 模型生成器

    支持 TripoSR / Meshy 等 API。
    """

    def __init__(self):
        self._cfg = get_config().aigc
        self._http = httpx.AsyncClient(timeout=300.0)

    async def generate(
        self,
        image_path: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        生成 3D 模型

        Returns:
            模型文件路径/URL，失败返回 None
        """
        if self._cfg.model3d_gen_provider == "triposr":
            return await self._generate_triposr(image_path, prompt)
        else:
            return await self._generate_meshy(image_path, prompt)

    async def _generate_triposr(
        self, image_path: Optional[str], prompt: Optional[str]
    ) -> Optional[str]:
        """TripoSR API"""
        logger.info(f"TripoSR 生成 3D: image={image_path}, prompt={prompt}")
        # TODO: 接入 TripoSR API
        return f"[triposr] generated 3d model"

    async def _generate_meshy(
        self, image_path: Optional[str], prompt: Optional[str]
    ) -> Optional[str]:
        """Meshy API"""
        if not self._cfg.meshy_api_key:
            logger.warning("未配置 Meshy API Key")
            return None
        logger.info(f"Meshy 生成 3D: image={image_path}, prompt={prompt}")
        # TODO: 接入 Meshy API
        return f"[meshy] generated 3d model"

    async def close(self) -> None:
        await self._http.aclose()
