"""
输入后端抽象基类
支持 ADB（模拟器）和 Unity Editor 两种方式
"""
from abc import ABC, abstractmethod
import numpy as np


class InputBackend(ABC):
    """所有输入后端的基类"""

    @abstractmethod
    def connect(self) -> bool:
        """连接设备，成功返回 True"""
        ...

    @abstractmethod
    def screenshot(self) -> np.ndarray:
        """截屏，返回 BGR numpy 数组 (H, W, 3)"""
        ...

    @abstractmethod
    def tap(self, x: int, y: int):
        """点击屏幕 (x, y) 坐标"""
        ...

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """从 (x1,y1) 滑动到 (x2,y2)，持续 duration_ms 毫秒"""
        ...

    @abstractmethod
    def long_press(self, x: int, y: int, duration_ms: int = 500):
        """长按 (x, y)，持续 duration_ms 毫秒"""
        ...

    def press_and_hold(self, x: int, y: int):
        """按住不放（用于摇杆），需要配合 release 使用"""
        self.long_press(x, y, duration_ms=999999)

    def release(self):
        """释放按住（松开摇杆）"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        ...
