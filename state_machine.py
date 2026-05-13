"""
状态机 - 主逻辑
处理大地图 → 导航 → 跑路 → 副本 → 结算的完整流程
"""
import time
import math
from config import cfg
from backend.base import InputBackend
from vision import Vision, GameState, TaskState


class StateMachine:
    """游戏测试状态机"""

    def __init__(self, backend: InputBackend, vision: Vision):
        self.backend = backend
        self.vision = vision
        self.state = GameState.MAIN_MAP
        self.run_attempts = 0          # 当前任务跑路尝试次数
        self.is_holding_joystick = False
        self.running = False
        self.frame_count = 0
        self.log_lines = []

    def log(self, msg: str):
        """记录日志"""
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        self.log_lines.append(line)

    def tick(self):
        """主循环每帧调用"""
        self.frame_count += 1

        # 截屏
        screen = self.backend.screenshot()
        if screen is None:
            time.sleep(0.5)
            return

        h, w = screen.shape[:2]

        # 检测当前状态
        detected = self.vision.detect_state(screen)

        # 状态转换
        if detected != self.state:
            self.log(f"状态变更: {self.state.value} → {detected.value}")
            self.state = detected

        # 根据状态执行动作
        if self.state == GameState.MAIN_MAP:
            self._handle_main_map(screen, w, h)
        elif self.state == GameState.DUNGEON_PREP:
            self._handle_dungeon_prep(screen, w, h)
        elif self.state == GameState.IN_BATTLE:
            self._handle_in_battle()
        elif self.state == GameState.SETTLEMENT:
            self._handle_settlement(screen, w, h)
        elif self.state == GameState.DIALOG:
            self._handle_dialog(screen, w, h)

        time.sleep(cfg.state_check_interval)

    def _handle_main_map(self, screen, w: int, h: int):
        """大地图状态处理"""
        # 检测任务状态
        task_state = self.vision.detect_task_state(screen)

        if task_state == TaskState.CLAIMABLE:
            # 可领奖 → 点击任务按钮
            self.log("任务可领奖，点击领取")
            tx = cfg.scale(cfg.task_button_x, w)
            ty = cfg.scale(cfg.task_button_y, h)
            self.backend.tap(tx, ty)
            time.sleep(cfg.tap_delay)
            self.run_attempts = 0

        elif task_state == TaskState.INCOMPLETE:
            # 未完成 → 点击导航，然后跑路
            if self.run_attempts >= cfg.run_max_attempts:
                self.log(f"跑路已达最大次数 {cfg.run_max_attempts}，跳过当前任务")
                self.run_attempts = 0
                return

            self.log(f"任务未完成，开始导航 (尝试 {self.run_attempts + 1}/{cfg.run_max_attempts})")

            # 点击任务按钮（导航）
            tx = cfg.scale(cfg.task_button_x, w)
            ty = cfg.scale(cfg.task_button_y, h)
            self.backend.tap(tx, ty)
            time.sleep(cfg.navigation_wait)  # 等镜头移动

            # 检测副本入口（导航后可能直接在副本门口）
            screen2 = self.backend.screenshot()
            if self.vision.detect_dungeon_entry(screen2):
                self.log("导航后发现副本入口")
                self.run_attempts = 0
                return

            # 呼出摇杆并跑路
            self._run_towards_target(w, h)
            self.run_attempts += 1

        else:
            # 任务不可见，可能需要等一下
            time.sleep(0.5)

    def _run_towards_target(self, w: int, h: int):
        """摇杆拖拽跑路"""
        # 摇杆位置
        jx = cfg.scale(cfg.joystick_center_x, w)
        jy = cfg.scale(cfg.joystick_center_y, h)

        # 拖拽方向：向上（屏幕上方），因为导航后目标通常在上方
        # 角色在屏幕中央，目标在镜头中显示的位置
        # 先用固定方向（向上）作为默认，后续可以优化
        drag_dist = cfg.scale(cfg.joystick_drag_max, h)
        drag_dx = 0
        drag_dy = -drag_dist  # 向上拖拽 = 角色向上移动

        # 计算拖拽终点
        to_x = jx + drag_dx
        to_y = jy + drag_dy

        self.log(f"摇杆拖拽: ({jx},{jy}) → ({to_x},{to_y})")

        # 使用 swipe 模拟拖拽
        duration_ms = int(cfg.run_duration_sec * 1000)
        self.backend.swipe(jx, jy, to_x, to_y, duration_ms)

        # 跑完后等一下
        time.sleep(0.5)

    def _handle_dungeon_prep(self, screen, w: int, h: int):
        """副本准备界面处理"""
        self.log("副本准备界面，点击确认进入")

        # 查找确认按钮（模板匹配优先）
        btn = self.vision.find_button(screen, "dungeon_confirm")
        if btn:
            self.backend.tap(btn[0], btn[1])
        else:
            # 使用配置坐标
            cx = cfg.scale(cfg.dungeon_confirm_x, w)
            cy = cfg.scale(cfg.dungeon_confirm_y, h)
            self.backend.tap(cx, cy)

        time.sleep(cfg.tap_delay)

    def _handle_in_battle(self):
        """战斗中 - 全自动，等待"""
        self.log("战斗中，等待结束...")
        time.sleep(2.0)  # 每 2 秒检查一次

    def _handle_settlement(self, screen, w: int, h: int):
        """结算画面处理"""
        self.log("结算画面，点击返回")

        # 查找返回按钮
        btn = self.vision.find_button(screen, "settlement_return")
        if btn:
            self.backend.tap(btn[0], btn[1])
        else:
            cx = cfg.scale(cfg.settlement_return_x, w)
            cy = cfg.scale(cfg.settlement_return_y, h)
            self.backend.tap(cx, cy)

        time.sleep(cfg.tap_delay)
        self.run_attempts = 0

    def _handle_dialog(self, screen, w: int, h: int):
        """对话框处理 - 点击屏幕跳过"""
        self.log("对话框，点击跳过")
        self.backend.tap(w // 2, h // 2)
        time.sleep(0.5)

    def start(self):
        """启动状态机"""
        self.running = True
        self.log("状态机启动")

    def stop(self):
        """停止状态机"""
        self.running = False
        if self.is_holding_joystick:
            self.backend.release()
        self.log("状态机停止")

    def save_log(self, path: str = "test_log.txt"):
        """保存日志"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_lines))
        print(f"日志已保存到 {path}")
