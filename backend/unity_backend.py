"""
Unity Editor 后端 - 通过 HTTP 接口与 Unity 通信
需要在 Unity 中运行 GameTestServer.cs 脚本
"""
import base64
import time
import numpy as np
import cv2
import requests
from .base import InputBackend


class UnityBackend(InputBackend):
    """通过 HTTP 接口控制 Unity Editor 中的游戏"""

    def __init__(self, url: str = "http://127.0.0.1:8765"):
        self.url = url.rstrip('/')
        self._connected = False

    def _request(self, endpoint: str, data: dict = None, timeout: int = 10) -> dict:
        """发送 HTTP 请求到 Unity"""
        try:
            resp = requests.post(
                f"{self.url}/{endpoint}",
                json=data or {},
                timeout=timeout
            )
            return resp.json()
        except requests.ConnectionError:
            print(f"Unity 连接失败: {self.url}")
            return {"ok": False, "error": "connection refused"}
        except Exception as e:
            print(f"Unity 请求失败: {e}")
            return {"ok": False, "error": str(e)}

    def connect(self) -> bool:
        """连接 Unity Editor"""
        result = self._request("ping")
        self._connected = result.get("ok", False)
        if self._connected:
            print(f"Unity Editor 已连接: {self.url}")
        else:
            print(f"Unity Editor 连接失败: {self.url}")
            print("请确保 Unity 中已运行 GameTestServer.cs 脚本")
        return self._connected

    def screenshot(self) -> np.ndarray:
        """通过 Unity 截屏"""
        result = self._request("screenshot")
        if result.get("ok"):
            img_bytes = base64.b64decode(result["image"])
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                return img
        return np.zeros((1440, 640, 3), dtype=np.uint8)

    def tap(self, x: int, y: int):
        """点击"""
        self._request("tap", {"x": x, "y": y})
        time.sleep(0.1)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """滑动"""
        self._request("swipe", {
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
            "duration": duration_ms
        })

    def long_press(self, x: int, y: int, duration_ms: int = 500):
        """长按"""
        self.swipe(x, y, x, y, duration_ms)

    def press_and_hold(self, x: int, y: int):
        """按住不放"""
        self._request("touch_down", {"x": x, "y": y})

    def release(self):
        """释放按住"""
        self._request("touch_up")

    def disconnect(self):
        """断开连接"""
        self._connected = False
        print("Unity Editor 已断开")
