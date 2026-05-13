"""
校准工具 - 在截图上点选坐标，自动写入配置
用法:
    python calibrate.py --backend adb --serial 127.0.0.1:5555
    python calibrate.py --backend unity --url http://127.0.0.1:8765

操作说明:
  1. 截图会显示在窗口中
  2. 按对应数字键进入校准模式：
     1 - 摇杆位置
     2 - 任务按钮
     3 - 副本入口
     4 - 副本确认按钮
     5 - 结算返回按钮
  3. 在图上点击设置位置
  4. 按 s 保存配置
  5. 按 q 退出
"""
import cv2
import sys
import argparse
import numpy as np

from config import cfg
from backend import ADBBackend, UnityBackend


# 校准点定义
CALIBRATE_POINTS = {
    '1': ('摇杆位置', 'joystick_center_x', 'joystick_center_y'),
    '2': ('任务按钮', 'task_button_x', 'task_button_y'),
    '3': ('副本入口', 'dungeon_entry_x', 'dungeon_entry_y'),
    '4': ('副本确认', 'dungeon_confirm_x', 'dungeon_confirm_y'),
    '5': ('结算返回', 'settlement_return_x', 'settlement_return_y'),
}

current_mode = None
points = {}
img_display = None
img_original = None
w, h = 0, 0


def mouse_callback(event, x, y, flags, param):
    global img_display, points, current_mode, w, h
    if event == cv2.EVENT_LBUTTONDOWN and current_mode:
        rel_x = x / w
        rel_y = y / h
        name, key_x, key_y = CALIBRATE_POINTS[current_mode]
        points[current_mode] = (rel_x, rel_y, key_x, key_y)
        setattr(cfg, key_x, rel_x)
        setattr(cfg, key_y, rel_y)

        # 重新绘制
        img_display = img_original.copy()
        draw_all_points()
        cv2.putText(img_display, f"{name}: ({rel_x:.3f}, {rel_y:.3f})",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Calibrate", img_display)


def draw_all_points():
    global img_display, points, w, h
    colors = {
        '1': (255, 0, 0),   # 蓝
        '2': (0, 255, 0),   # 绿
        '3': (0, 0, 255),   # 红
        '4': (255, 255, 0), # 青
        '5': (0, 255, 255), # 黄
    }
    for key, (rel_x, rel_y, _, _) in points.items():
        px = int(rel_x * w)
        py = int(rel_y * h)
        color = colors.get(key, (255, 255, 255))
        cv2.circle(img_display, (px, py), 8, color, -1)
        cv2.circle(img_display, (px, py), 10, (255, 255, 255), 2)


def main():
    global img_display, img_original, w, h, current_mode

    parser = argparse.ArgumentParser(description="坐标校准工具")
    parser.add_argument('--backend', choices=['adb', 'unity'], default='adb')
    parser.add_argument('--serial', default='127.0.0.1:5555')
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()

    # 加载已有配置
    cfg.load(args.config)

    # 连接
    if args.backend == 'adb':
        backend = ADBBackend(serial=args.serial)
    else:
        backend = UnityBackend(url=args.url)

    if not backend.connect():
        print("连接失败")
        sys.exit(1)

    # 截屏
    print("正在截屏...")
    screen = backend.screenshot()
    h, w = screen.shape[:2]
    img_original = screen.copy()
    img_display = screen.copy()

    # 窗口
    cv2.namedWindow("Calibrate", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Calibrate", 640, 1440)
    cv2.setMouseCallback("Calibrate", mouse_callback)

    print("\n=== 坐标校准工具 ===")
    print("按数字键选择要校准的项目:")
    for key, (name, _, _) in CALIBRATE_POINTS.items():
        print(f"  {key} - {name}")
    print("  s - 保存配置")
    print("  r - 重新截屏")
    print("  q - 退出")
    print()

    while True:
        cv2.imshow("Calibrate", img_display)
        key = cv2.waitKey(50) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('s'):
            cfg.save(args.config)
        elif key == ord('r'):
            screen = backend.screenshot()
            img_original = screen.copy()
            img_display = screen.copy()
            draw_all_points()
            print("已重新截屏")
        elif chr(key) in CALIBRATE_POINTS:
            current_mode = chr(key)
            name = CALIBRATE_POINTS[current_mode][0]
            print(f"校准模式: {name} - 请在图上点击目标位置")
        elif key != 255:
            pass  # 忽略其他按键

    cv2.destroyAllWindows()
    backend.disconnect()
    print("校准完成")


if __name__ == '__main__':
    main()
