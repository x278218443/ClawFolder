"""
画面识别模块
通过 OpenCV 模板匹配 + 颜色检测判断游戏状态
"""
import cv2
import numpy as np
import os
from enum import Enum


class GameState(Enum):
    """游戏状态"""
    MAIN_MAP = "main_map"           # 大地图
    NAVIGATING = "navigating"       # 导航中（镜头移动）
    DUNGEON_PREP = "dungeon_prep"   # 副本准备界面
    IN_BATTLE = "in_battle"         # 战斗中
    SETTLEMENT = "settlement"       # 结算画面
    DIALOG = "dialog"               # 对话框
    UNKNOWN = "unknown"             # 未知状态


class TaskState(Enum):
    """任务按钮状态"""
    CLAIMABLE = "claimable"    # 可领奖
    INCOMPLETE = "incomplete"  # 未完成
    HIDDEN = "hidden"          # 不可见


class Vision:
    """画面识别引擎"""

    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """加载所有模板图片"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
            print(f"模板目录已创建: {self.template_dir}/")
            print("请将截取的 UI 元素图片放入此目录")
            return

        for fname in os.listdir(self.template_dir):
            if fname.endswith(('.png', '.jpg')):
                name = os.path.splitext(fname)[0]
                path = os.path.join(self.template_dir, fname)
                self.templates[name] = cv2.imread(path, cv2.IMREAD_COLOR)
                print(f"  已加载模板: {name}")

    def _match_template(self, screen: np.ndarray, template_name: str,
                        threshold: float = 0.8) -> list:
        """模板匹配，返回所有匹配位置 [(x, y, w, h, confidence), ...]"""
        if template_name not in self.templates:
            return []
        template = self.templates[template_name]
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        h, w = template.shape[:2]
        matches = []
        for pt in zip(*locations[::-1]):
            conf = result[pt[1], pt[0]]
            matches.append((pt[0], pt[1], w, h, conf))
        return self._non_max_suppression(matches)

    def _non_max_suppression(self, matches: list, overlap_thresh: float = 0.3) -> list:
        """非极大值抑制，去除重叠的匹配"""
        if not matches:
            return []
        # 按置信度排序
        matches.sort(key=lambda x: x[4], reverse=True)
        keep = []
        for m in matches:
            is_overlap = False
            for k in keep:
                # 计算 IoU
                x1 = max(m[0], k[0])
                y1 = max(m[1], k[1])
                x2 = min(m[0]+m[2], k[0]+k[2])
                y2 = min(m[1]+m[3], k[1]+k[3])
                if x2 > x1 and y2 > y1:
                    overlap = (x2-x1) * (y2-y1)
                    area = m[2] * m[3]
                    if overlap / area > overlap_thresh:
                        is_overlap = True
                        break
            if not is_overlap:
                keep.append(m)
        return keep

    def detect_state(self, screen: np.ndarray) -> GameState:
        """
        检测当前游戏状态
        优先级：结算 > 副本准备 > 战斗 > 对话 > 导航 > 大地图
        """
        # 结算画面 - 通常有明显的"完成"/"返回"按钮
        if self._match_template(screen, "settlement_return", 0.7):
            return GameState.SETTLEMENT

        # 副本准备界面 - 有"进入"/"开始"按钮
        if self._match_template(screen, "dungeon_confirm", 0.7):
            return GameState.DUNGEON_PREP

        # 战斗中 - 检测战斗 UI（血条、技能按钮等）
        if self._match_template(screen, "battle_hud", 0.7):
            return GameState.IN_BATTLE

        # 对话框
        if self._match_template(screen, "dialog_box", 0.7):
            return GameState.DIALOG

        # 默认认为在大地图
        return GameState.MAIN_MAP

    def detect_task_state(self, screen: np.ndarray) -> TaskState:
        """
        检测任务按钮状态
        通过按钮区域的颜色判断：
        - 可领奖：高亮色（金/绿）
        - 未完成：灰色/普通色
        """
        h, w = screen.shape[:2]
        # 任务按钮区域（左下角）
        x1 = int(w * 0.05)
        y1 = int(h * 0.82)
        x2 = int(w * 0.20)
        y2 = int(h * 0.90)

        roi = screen[y1:y2, x1:x2]
        if roi.size == 0:
            return TaskState.HIDDEN

        # 转 HSV 分析颜色
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]

        # 统计高亮像素占比
        # 绿色/金色色相范围 (大约 35-85)
        bright_mask = (
            (h_channel >= 35) & (h_channel <= 85) &
            (s_channel >= 100) &
            (v_channel >= 150)
        )
        bright_ratio = np.sum(bright_mask) / bright_mask.size

        if bright_ratio > 0.3:
            return TaskState.CLAIMABLE

        # 也检查红色高亮（某些游戏用红色表示可领取）
        red_mask = (
            ((h_channel <= 10) | (h_channel >= 170)) &
            (s_channel >= 100) &
            (v_channel >= 150)
        )
        red_ratio = np.sum(red_mask) / red_mask.size
        if red_ratio > 0.3:
            return TaskState.CLAIMABLE

        return TaskState.INCOMPLETE

    def detect_dungeon_entry(self, screen: np.ndarray) -> bool:
        """检测副本入口是否可见"""
        return len(self._match_template(screen, "dungeon_entry", 0.7)) > 0

    def detect_settlement(self, screen: np.ndarray) -> bool:
        """检测是否在结算画面"""
        return len(self._match_template(screen, "settlement_return", 0.7)) > 0

    def find_button(self, screen: np.ndarray, template_name: str) -> tuple:
        """
        查找按钮位置，返回 (center_x, center_y) 或 None
        """
        matches = self._match_template(screen, template_name, 0.7)
        if matches:
            m = matches[0]
            cx = m[0] + m[2] // 2
            cy = m[1] + m[3] // 2
            return (cx, cy)
        return None

    def get_screen_hash(self, screen: np.ndarray) -> str:
        """生成画面指纹，用于检测画面是否变化"""
        small = cv2.resize(screen, (32, 32))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return hash(gray.tobytes())

    def screen_changed(self, hash1: int, hash2: int, threshold: int = 0) -> bool:
        """判断两个画面指纹是否不同"""
        return hash1 != hash2
