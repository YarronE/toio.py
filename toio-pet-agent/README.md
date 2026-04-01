# 🐾 Toio Pet Agent - 虚实融合桌宠助手

> 基于 Toio + AI Agent + 本地LLM 的桌面虚拟端 + 物理实体端个人桌宠助手

## ✨ 特性

- 🎨 **AI 创作** — 用照片/语言描述创建独一无二的虚拟桌宠形象
- 🖥️ **桌面伴侣** — 透明窗口桌宠，跟随你的桌面活动
- 🤖 **物理实体** — 控制 Toio Core Cube 在真实桌面移动
- 🔄 **虚实切换** — 桌宠无缝从屏幕走入物理世界
- 🥽 **AR 增强** — Vision Pro 可见 Toio 上的 3D 虚拟形象
- 🧠 **AI 对话** — 本地 LLM 驱动的智能交互

## 🏗️ 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  桌面虚拟端   │────▶│  AI Agent 核心 │◀────│  Vision Pro  │
│ Electron+React│     │ LangGraph+LLM│     │  RealityKit  │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  空间协调器   │◀───▶│ Toio BLE 控制 │
│ 坐标映射+WS  │     │  bleak async  │
└──────────────┘     └──────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (桌面端)
- Bluetooth 4.0+ (BLE)
- Ollama (本地 LLM，推荐)

### 安装

```bash
# 1. 克隆 & 进入项目
cd toio-pet-agent

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 复制环境变量
cp .env.example .env

# 5. 启动 Ollama (另开终端)
ollama serve
ollama pull qwen2.5:7b

# 6. 运行
toio-pet
```

## 📁 项目结构

```
toio-pet-agent/
├── toio_pet_agent/          # Python 核心包
│   ├── toio/                # Toio BLE 控制
│   ├── agent/               # AI Agent 引擎
│   ├── spatial/             # 空间协调器
│   ├── aigc/                # AIGC 生成管线
│   ├── server/              # WebSocket + API
│   └── main.py              # 主入口
├── desktop/                 # Electron 桌面端
│   ├── src/
│   └── package.json
├── assets/                  # 静态资源
├── pyproject.toml
└── README.md
```

## 📝 License

MIT
