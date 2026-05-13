"""
配置文件 - 所有坐标和阈值
基准分辨率: 640x1440 (竖屏)
所有坐标用相对值 (0~1)，运行时自动按实际分辨率换算
"""
import json
import os

# 基准分辨率
BASE_W = 640
BASE_H = 1440


class Config:
    """游戏测试脚本配置"""

    def __init__(self):
        # === 摇杆 ===
        # 摇杆呼出位置（按住屏幕非 UI 区域）
        self.joystick_center_x = 0.25   # 屏幕左侧 1/4 处
        self.joystick_center_y = 0.75   # 屏幕下方 3/4 处
        self.joystick_drag_max = 0.15   # 最大拖拽距离（相对屏幕高度）

        # === 任务按钮 ===
        # 左下角固定位置
        self.task_button_x = 0.12
        self.task_button_y = 0.85

        # === 副本入口 ===
        self.dungeon_entry_x = 0.12
        self.dungeon_entry_y = 0.78

        # === 副本准备界面确认按钮 ===
        self.dungeon_confirm_x = 0.5
        self.dungeon_confirm_y = 0.65

        # === 结算画面返回按钮 ===
        self.settlement_return_x = 0.5
        self.settlement_return_y = 0.75

        # === 跑路参数 ===
        self.run_duration_sec = 3.0     # 每次拖拽跑路时长（秒）
        self.run_max_attempts = 10      # 最大跑路尝试次数

        # === 状态检测 ===
        # 任务按钮颜色阈值（HSV）
        # 可领奖时按钮通常是高亮色（金/绿），未完成是灰色/普通色
        self.task_claimable_h_min = 35  # 绿色/金色范围
        self.task_claimable_h_max = 85
        self.task_claimable_s_min = 100
        self.task_claimable_v_min = 150

        # === 操作间隔 ===
        self.tap_delay = 0.3            # 点击后等待（秒）
        self.state_check_interval = 0.5 # 状态检测间隔（秒）
        self.navigation_wait = 2.0      # 导航镜头移动等待（秒）

        # === ADB ===
        self.adb_serial = "127.0.0.1:5555"  # 默认雷电模拟器

        # === Unity Editor ===
        self.unity_url = "http://127.0.0.1:8765"

    def abs_x(self, rel_x: float) -> int:
        """相对坐标 → 绝对 X"""
        return int(rel_x * BASE_W)

    def abs_y(self, rel_y: float) -> int:
        """相对坐标 → 绝对 Y"""
        return int(rel_y * BASE_H)

    def scale(self, rel_val: float, actual_size: int) -> int:
        """相对坐标按实际分辨率缩放"""
        return int(rel_val * actual_size)

    def save(self, path: str = "config.json"):
        """保存配置到 JSON"""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"配置已保存到 {path}")

    def load(self, path: str = "config.json") -> bool:
        """从 JSON 加载配置"""
        if not os.path.exists(path):
            return False
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)
        print(f"配置已从 {path} 加载")
        return True


# 全局配置实例
cfg = Config()
