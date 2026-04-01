"""
全系统集成测试

启动后端 (Agent + WS + API)，然后用 WebSocket 模拟前端交互。
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import websockets


async def main():
    ws_url = "ws://localhost:8765"
    print(f"🔗 连接 WebSocket: {ws_url}")
    print("   (请先在另一个终端启动后端: python -m toio_pet_agent.main)")
    print()

    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ 已连接!")

            # 接收初始状态
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            state = json.loads(raw)
            print(f"📦 初始状态: {json.dumps(state, ensure_ascii=False, indent=2)}")
            print()

            # 测试聊天
            tests = [
                "你好呀，你叫什么名字？",
                "今天天气怎么样？",
                "你能在桌上走走吗？",
                "帮我换个开心的表情！",
            ]

            for msg in tests:
                print(f"📤 发送: {msg}")
                await ws.send(json.dumps({
                    "type": "chat",
                    "data": {"message": msg}
                }))

                # 等待回复
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    resp = json.loads(raw)
                    if resp["type"] == "chat_response":
                        d = resp["data"]
                        print(f"📥 回复: {d['text']}")
                        print(f"   情绪: {d['mood']}, 能量: {d['energy']:.0f}")
                        if d.get("tool_calls"):
                            for tc in d["tool_calls"]:
                                print(f"   [工具] {tc['tool']}: {tc['result']}")
                    print()
                except asyncio.TimeoutError:
                    print("⚠️ 回复超时")
                    print()

                await asyncio.sleep(1)

            # 测试位置更新
            print("📤 模拟桌宠走到屏幕边缘")
            await ws.send(json.dumps({
                "type": "pet_position",
                "data": {"x": 1900, "y": 1060}  # 接近右下角
            }))

            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                resp = json.loads(raw)
                print(f"📥 响应: {json.dumps(resp, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                print("   (无过渡事件 — 可能未到达边缘)")

            print()
            print("✅ 集成测试完成!")

    except ConnectionRefusedError:
        print("❌ 连接失败 — 请先启动后端服务")
        print("   运行: cd toio-pet-agent && python -m toio_pet_agent.main")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
