"""
LLM 统一接口

提供 Ollama 本地模型 和 OpenAI 兼容 API 的统一调用接口。
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx
from loguru import logger

from ..config import AppConfig, get_config


class LLMClient:
    """
    LLM 统一调用客户端

    自动根据配置选择 Ollama 或 OpenAI 后端。
    支持普通调用和流式输出。
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self._cfg = (config or get_config()).llm
        self._http = httpx.AsyncClient(timeout=120.0)

    @property
    def provider(self) -> str:
        return self._cfg.provider

    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        调用 LLM 获取完整回复

        Args:
            messages: [{"role": "user/assistant/system", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        if self._cfg.provider == "ollama":
            return await self._chat_ollama(messages, temperature)
        else:
            return await self._chat_openai(messages, temperature)

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """流式调用 LLM"""
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        if self._cfg.provider == "ollama":
            async for chunk in self._stream_ollama(messages, temperature):
                yield chunk
        else:
            async for chunk in self._stream_openai(messages, temperature):
                yield chunk

    # --- Ollama ---

    async def _chat_ollama(self, messages: list[dict], temperature: float) -> str:
        url = f"{self._cfg.ollama_base_url}/api/chat"
        payload = {
            "model": self._cfg.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama 调用失败: {e}")
            raise

    async def _stream_ollama(
        self, messages: list[dict], temperature: float
    ) -> AsyncIterator[str]:
        url = f"{self._cfg.ollama_base_url}/api/chat"
        payload = {
            "model": self._cfg.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            async with self._http.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
        except Exception as e:
            logger.error(f"Ollama 流式调用失败: {e}")
            raise

    # --- OpenAI 兼容 ---

    async def _chat_openai(self, messages: list[dict], temperature: float) -> str:
        url = f"{self._cfg.openai_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._cfg.openai_api_key}"}
        payload = {
            "model": self._cfg.openai_model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            resp = await self._http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI 调用失败: {e}")
            raise

    async def _stream_openai(
        self, messages: list[dict], temperature: float
    ) -> AsyncIterator[str]:
        url = f"{self._cfg.openai_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._cfg.openai_api_key}"}
        payload = {
            "model": self._cfg.openai_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        try:
            async with self._http.stream(
                "POST", url, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
        except Exception as e:
            logger.error(f"OpenAI 流式调用失败: {e}")
            raise

    async def close(self) -> None:
        await self._http.aclose()
