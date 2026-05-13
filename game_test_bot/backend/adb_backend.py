"""
ADB 后端 - 通过 ADB 连接模拟器（雷电/MuMu/夜神通用）
"""
import subprocess
import time
import numpy as np
import cv2
from .base import InputBackend


class ADBBackend(InputBackend):
    """通过 ADB 控制模拟器"""

    def __init__(self, serial: str = "127.0.0.1:5555"):
        self.serial = serial
        self._connected = False

    def _run(self, cmd: str, timeout: int = 10) -> bytes:
        """执行 ADB 命令"""
        full_cmd = f"adb -s {self.serial} {cmd}"
        try:
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True,
                timeout=timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            print(f"ADB 命令超时: {full_cmd}")
            return b""
        except Exception as e:
            print(f"ADB 命令失败: {full_cmd}, 错误: {e}")
            return b""

    def connect(self) -> bool:
        """连接模拟器"""
        # 先尝试 adb connect
        subprocess.run(f"adb connect {self.serial}", shell=True,
                       capture_output=True, timeout=5)
        # 检查连接
        output = self._run("shell echo ok")
        self._connected = b"ok" in output
        if self._connected:
            print(f"ADB 已连接: {self.serial}")
        else:
            print(f"ADB 连接失败: {self.serial}")
        return self._connected

    def screenshot(self) -> np.ndarray:
        """通过 ADB 截屏"""
        png_data = self._run("exec-out screencap -p", timeout=5)
        if not png_data:
            # 降级方案：先存文件再拉取
            self._run("shell screencap -p /sdcard/screen.png")
            png_data = self._run("pull /sdcard/screen.png -", timeout=5)
        if png_data:
            img_array = np.frombuffer(png_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                return img
        # 返回黑色图片作为 fallback
        return np.zeros((1440, 640, 3), dtype=np.uint8)

    def tap(self, x: int, y: int):
        """点击"""
        self._run(f"shell input tap {x} {y}")
        time.sleep(0.1)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """滑动"""
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def long_press(self, x: int, y: int, duration_ms: int = 500):
        """长按（通过 swipe 原地不动实现）"""
        self._run(f"shell input swipe {x} {y} {x} {y} {duration_ms}")

    def press_and_hold(self, x: int, y: int):
        """按住不放 - ADB 模式下用 sendevent 实现更可靠"""
        # 使用 input touchscreen sendevent 按下
        # 简化方案：启动一个后台 swipe
        self._hold_x = x
        self._hold_y = y
        # 先 tap 按下
        self._run(f"shell input touchscreen sendevent /dev/input/event1 3 57 0")
        self._run(f"shell input touchscreen sendevent /dev/input/event1 1 330 1")
        self._run(f"shell input touchscreen sendevent /dev/input/event1 3 53 {x}")
        self._run(f"shell input touchscreen sendevent /dev/input/event1 3 54 {y}")
        self._run(f"shell input touchscreen sendevent /dev/input/event1 3 48 5")
        self._run(f"shell input touchscreen sendevent /dev/input/event1 0 0 0")

    def release(self):
        """释放按住"""
        self._run("shell input touchscreen sendevent /dev/input/event1 3 57 -1")
        self._run("shell input touchscreen sendevent /dev/input/event1 1 330 0")
        self._run("shell input touchscreen sendevent /dev/input/event1 0 0 0")

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration_ms: int = 500):
        """拖拽（swipe 的别名，更直观）"""
        self.swipe(from_x, from_y, to_x, to_y, duration_ms)

    def disconnect(self):
        """断开连接"""
        self._connected = False
        print("ADB 已断开")


# 常见模拟器 ADB 端口
EMULATOR_PORTS = {
    "雷电": "127.0.0.1:5555",
    "mumu": "127.0.0.1:7555",
    "夜神": "127.0.0.1:62001",
}
