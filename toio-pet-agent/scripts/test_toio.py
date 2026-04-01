"""
Toio 连接测试脚本

独立运行，用于验证 BLE 连接和基础控制。
"""

import asyncio
import sys
import os

# 将项目根目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from toio_pet_agent.toio.controller import ToioCube, ToioManager
from toio_pet_agent.toio.protocol import hsv_to_rgb


async def test_scan():
    """仅扫描设备"""
    print("🔍 扫描 Toio 设备...")
    mgr = ToioManager()
    devices = await mgr.scan(timeout=5)
    if not devices:
        print("❌ 未找到任何 Toio 设备")
        print("   请确保:")
        print("   1. Toio Core Cube 已开机")
        print("   2. 蓝牙已开启")
        print("   3. 没有其他程序正在连接该设备")
        return
    print(f"✅ 找到 {len(devices)} 个设备:")
    for d in devices:
        print(f"   - {d.name} ({d.address})")


async def test_connect():
    """扫描 + 连接 + 基础测试"""
    print("🔗 连接 Toio...")
    mgr = ToioManager()
    cubes = await mgr.scan_and_connect(max_cubes=1)
    if not cubes:
        print("❌ 连接失败")
        return

    cube = cubes[0]
    print(f"✅ 已连接")

    try:
        # 测试 LED
        print("💡 LED 测试: 红→绿→蓝")
        for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            await cube.led(*color)
            await asyncio.sleep(0.5)
        await cube.led_off()

        # 测试音效
        print("🔊 音效测试")
        await cube.sound(0)
        await asyncio.sleep(1)

        # 测试位置读取
        print("📍 位置读取")
        pos = await cube.get_position()
        if pos:
            print(f"   位置: ({pos.center_x}, {pos.center_y}), 角度: {pos.center_angle}")
        else:
            print("   ⚠️ 未检测到位置 (可能不在 mat 上)")

        # 测试电池
        bat = await cube.get_battery()
        if bat:
            print(f"🔋 电量: {bat.level}%")

        # 测试电机 (短时前进)
        print("🚗 电机测试: 前进 1 秒")
        await cube.motor_timed(30, 30, 1000)
        await asyncio.sleep(1.5)

        # 测试旋转
        print("🔄 旋转 180°")
        await cube.motor_timed(30, -30, 800)
        await asyncio.sleep(1)

        await cube.motor_stop()
        print("✅ 所有测试完成!")

    except Exception as e:
        print(f"❌ 测试出错: {e}")
    finally:
        await mgr.disconnect_all()
        print("🔌 已断开")


async def test_move_to():
    """测试 PID 移动到目标点"""
    print("🎯 PID 移动测试")
    mgr = ToioManager()
    cubes = await mgr.scan_and_connect(max_cubes=1)
    if not cubes:
        return

    cube = cubes[0]
    targets = [(200, 200), (350, 150), (250, 300), (250, 250)]

    try:
        for tx, ty in targets:
            print(f"   → 移动到 ({tx}, {ty})")
            await cube.led(255, 200, 0)
            arrived = await cube.move_to(tx, ty, speed=60, threshold=30, timeout=8)
            status = "✅ 到达" if arrived else "⚠️ 超时"
            pos = cube.position
            if pos:
                print(f"   {status} 当前: ({pos.center_x}, {pos.center_y})")
            await asyncio.sleep(0.5)

        await cube.led(0, 255, 0, duration_ms=2000)
        await cube.sound(7)
        print("✅ 移动测试完成!")

    except Exception as e:
        print(f"❌ 出错: {e}")
    finally:
        await mgr.disconnect_all()


if __name__ == "__main__":
    commands = {
        "scan": test_scan,
        "connect": test_connect,
        "move": test_move_to,
    }

    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd not in commands:
        print(f"用法: python test_toio.py [{'/'.join(commands.keys())}]")
        sys.exit(1)

    print(f"=== Toio 测试: {cmd} ===")
    asyncio.run(commands[cmd]())
