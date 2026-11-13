#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面机器人 ESP32-C3 SuperMini 一键烧录 + 连接自检。

用法:
    python flash_robot.py           # 自检 + 烧录
    python flash_robot.py --check   # 只自检，不写入芯片
    python flash_robot.py --erase   # 烧录前先全片擦除（会清空 NVS 配置）

固件/参数依据：随包「刷机步骤.png」(Flash Download Tool V3.9.8)
    单文件 merged bin @ 0x0 / 40MHz / DIO / 4MB / 115200 / DoNotChgBin
镜像头实测: E9 03 02 20 -> 3 段, DIO(0x02), 4MB+40MHz(0x20), 与截图一致。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLDIR = ROOT / ".flash-tools"
FIRMWARE = (
    ROOT / "达文西君-固件资料" / "固件" / "桌面机器人"
    / "xsd_robot_espidf_20261026_v2.9.90"
    / "merged-std-xsd_robot_espidf_20261026_v2.9.90.bin"
)
EXPECTED_SIZE = 4 * 1024 * 1024  # 4194304 bytes
BAUD = "115200"


def find_esp32_ports() -> list:
    """只认乐鑫原生 USB Serial/JTAG (VID 303A)，排除蓝牙虚拟串口。"""
    sys.path.insert(0, str(TOOLDIR))
    from serial.tools import list_ports
    return [p for p in list_ports.comports() if "303A" in (p.hwid or "").upper()]


def wait_for_device(timeout_s: int) -> list:
    """轮询等待 ESP32 接入，返回端口列表；超时返回空。"""
    import time
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ports = find_esp32_ports()
        if ports:
            print()
            return ports
        remain = int(deadline - time.monotonic())
        print(f"\r[..] 等待 ESP32 接入 ... 剩余 {remain:3d}s", end="", flush=True)
        time.sleep(0.5)
    print()
    return []


def print_no_device_help() -> None:
    print("[X] 当前没有在线的 ESP32 设备 (USB VID 303A:1001)。")
    print("    串口设备不会触发 Windows「自动播放」弹窗，判据是端口枚举，不是弹窗。")
    print("    按下列顺序排除物理连接问题：")
    print("    1. 线必须插在 ESP32-C3 板载的 Type-C 口；充电模块上那个")
    print("       标着「Type-C 输入 5V/1A」的口只供电，D+/D- 未接，插了不会枚举。")
    print("    2. 换一根确认能传数据的线（很多 Type-C 线只有 VCC/GND）。")
    print("    3. 换电脑后置 USB 口，避开无源 HUB 和延长线。")
    print("    4. 仍不行：按住板上 BOOT 不放 -> 插入 USB -> 等 2 秒 -> 松开 BOOT，")
    print("       强制进入下载模式后再跑本脚本。")
    print("    驱动无需另装：本机 usbser.sys 已绑定过 VID_303A&PID_1001。")


def verify_firmware() -> bool:
    if not FIRMWARE.is_file():
        print(f"[X] 找不到固件: {FIRMWARE}")
        return False
    size = FIRMWARE.stat().st_size
    with FIRMWARE.open("rb") as f:
        head = f.read(4)
    if size != EXPECTED_SIZE or head[0] != 0xE9:
        print(f"[X] 镜像校验失败: {size} bytes, head={head.hex(' ')}")
        return False
    print(f"[OK] 镜像校验: {FIRMWARE.name} / {size} bytes / magic 0xE9"
          f" / mode={head[2]:#04x} / size+freq={head[3]:#04x}")
    return True


def main() -> int:
    check_only = "--check" in sys.argv
    do_erase = "--erase" in sys.argv
    wait_s = 0
    if "--wait" in sys.argv:
        i = sys.argv.index("--wait")
        if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            wait_s = int(sys.argv[i + 1])

    if not TOOLDIR.is_dir():
        print(f"[X] 缺少 esptool 目录: {TOOLDIR}")
        return 2

    ports = find_esp32_ports()
    if not ports and wait_s > 0:
        print(f"[..] 未检测到设备，进入监听模式（最长 {wait_s}s），插线后自动开始烧录。")
        ports = wait_for_device(wait_s)
    if not ports:
        print_no_device_help()
        return 1

    for p in ports:
        print(f"[OK] 检测到: {p.device} | {p.description} | {p.hwid}")
    port = ports[0].device
    if len(ports) > 1:
        print(f"    存在多个乐鑫端口，选用 {port}")

    if check_only:
        print("[OK] 自检完成，设备在线，可执行烧录（未写入芯片）。")
        return 0

    if not verify_firmware():
        return 2

    env = dict(os.environ)
    env["PYTHONPATH"] = str(TOOLDIR) + os.pathsep + env.get("PYTHONPATH", "")

    if do_erase:
        print("[..] 全片擦除中 ...")
        rc = subprocess.call(
            [sys.executable, "-m", "esptool", "--chip", "esp32c3",
             "-p", port, "-b", BAUD, "erase_flash"], env=env)
        if rc != 0:
            print("[X] 擦除失败，已停止，未写入固件。")
            return rc

    # 显式 dio/40m/4MB 与镜像头完全一致，等价于截图里勾选 DoNotChgBin。
    cmd = [
        sys.executable, "-m", "esptool",
        "--chip", "esp32c3", "-p", port, "-b", BAUD,
        "--before", "default_reset", "--after", "hard_reset",
        "write_flash",
        "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
        "0x0", str(FIRMWARE),
    ]
    print("[..] 开始烧录（约 40-90 秒，期间不要拔线）...")
    print("    " + " ".join(cmd))
    rc = subprocess.call(cmd, env=env)
    if rc != 0:
        print("[X] 烧录失败。若报 'Failed to connect'，按住 BOOT 再插线重试；")
        print("    也可把 BAUD 改成 921600 之前的更低值或改用 Flash Download Tool GUI。")
        return rc
    print("[OK] 烧录完成，芯片已硬复位。拔线后按机器人电源开关即可开机。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
