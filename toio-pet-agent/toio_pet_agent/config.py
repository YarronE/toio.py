"""
Toio Pet Agent 全局配置管理

从 .env 和环境变量中读取配置，提供类型安全的访问接口。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class LLMConfig(BaseModel):
    """LLM 配置"""

    provider: Literal["ollama", "openai"] = "ollama"

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:7b")

    # OpenAI 兼容
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o")


class ToioConfig(BaseModel):
    """Toio 蓝牙配置"""

    auto_connect: bool = True
    max_cubes: int = 2
    scan_timeout: int = 10

    # BLE UUIDs (toio Core Cube 官方规格)
    service_uuid: str = "10B20100-5B3B-4571-9508-CF3EFCD7BBAE"
    id_uuid: str = "10B20101-5B3B-4571-9508-CF3EFCD7BBAE"
    motor_uuid: str = "10B20102-5B3B-4571-9508-CF3EFCD7BBAE"
    light_uuid: str = "10B20103-5B3B-4571-9508-CF3EFCD7BBAE"
    sound_uuid: str = "10B20104-5B3B-4571-9508-CF3EFCD7BBAE"
    sensor_uuid: str = "10B20106-5B3B-4571-9508-CF3EFCD7BBAE"
    button_uuid: str = "10B20107-5B3B-4571-9508-CF3EFCD7BBAE"
    battery_uuid: str = "10B20108-5B3B-4571-9508-CF3EFCD7BBAE"
    config_uuid: str = "10B201FF-5B3B-4571-9508-CF3EFCD7BBAE"


class AIGCConfig(BaseModel):
    """AIGC 生成配置"""

    # 生图
    image_gen_provider: Literal["comfyui", "api"] = "comfyui"
    comfyui_base_url: str = Field(default="http://localhost:8188")
    image_gen_api_key: str = Field(default="")
    image_gen_api_url: str = Field(default="")

    # 生3D模型
    model3d_gen_provider: Literal["triposr", "meshy"] = "triposr"
    triposr_api_url: str = Field(default="http://localhost:8080")
    triposr_api_key: str = Field(default="")
    meshy_api_key: str = Field(default="")


class ServerConfig(BaseModel):
    """服务配置"""

    websocket_port: int = 8765
    api_port: int = 8000


class DesktopConfig(BaseModel):
    """桌面端配置"""

    transparent: bool = True
    always_on_top: bool = True
    pet_size: int = 128


class AppConfig(BaseModel):
    """应用总配置"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    toio: ToioConfig = Field(default_factory=ToioConfig)
    aigc: AIGCConfig = Field(default_factory=AIGCConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    desktop: DesktopConfig = Field(default_factory=DesktopConfig)

    log_level: str = "INFO"
    log_file: str = "logs/toio_pet.log"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量构建配置"""
        return cls(
            llm=LLMConfig(
                provider="openai" if os.getenv("OPENAI_API_KEY") else "ollama",
                ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            ),
            toio=ToioConfig(
                auto_connect=os.getenv("TOIO_AUTO_CONNECT", "true").lower() == "true",
                max_cubes=int(os.getenv("TOIO_MAX_CUBES", "2")),
                scan_timeout=int(os.getenv("TOIO_SCAN_TIMEOUT", "10")),
            ),
            aigc=AIGCConfig(
                image_gen_provider=os.getenv("IMAGE_GEN_PROVIDER", "comfyui"),  # type: ignore
                comfyui_base_url=os.getenv("COMFYUI_BASE_URL", "http://localhost:8188"),
                image_gen_api_key=os.getenv("IMAGE_GEN_API_KEY", ""),
                image_gen_api_url=os.getenv("IMAGE_GEN_API_URL", ""),
                model3d_gen_provider=os.getenv("MODEL3D_GEN_PROVIDER", "triposr"),  # type: ignore
                triposr_api_url=os.getenv("TRIPOSR_API_URL", "http://localhost:8080"),
                triposr_api_key=os.getenv("TRIPOSR_API_KEY", ""),
                meshy_api_key=os.getenv("MESHY_API_KEY", ""),
            ),
            server=ServerConfig(
                websocket_port=int(os.getenv("WEBSOCKET_PORT", "8765")),
                api_port=int(os.getenv("API_PORT", "8000")),
            ),
            desktop=DesktopConfig(
                transparent=os.getenv("DESKTOP_TRANSPARENT", "true").lower() == "true",
                always_on_top=os.getenv("DESKTOP_ALWAYS_ON_TOP", "true").lower() == "true",
                pet_size=int(os.getenv("DESKTOP_PET_SIZE", "128")),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/toio_pet.log"),
        )


# 全局单例
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config
