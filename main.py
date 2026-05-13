"""
游戏测试脚本 - 主入口
用法:
    python main.py --backend adb --serial 127.0.0.1:5555
    python main.py --backend unity --url http://127.0.0.1:8765
"""
import argparse
import sys
import time
import signal

from config import cfg
from backend import ADBBackend, UnityBackend
from vision import Vision
from state_machine import StateMachine


def parse_args():
    parser = argparse.ArgumentParser(description="游戏冒烟测试脚本")
    parser.add_argument('--backend', choices=['adb', 'unity'], default='adb',
                        help='输入后端: adb(模拟器) 或 unity(Unity Editor)')
    parser.add_argument('--serial', default='127.0.0.1:5555',
                        help='ADB 设备地址 (默认: 127.0.0.1:5555)')
    parser.add_argument('--url', default='http://127.0.0.1:8765',
                        help='Unity HTTP 接口地址 (默认: http://127.0.0.1:8765)')
    parser.add_argument('--config', default='config.json',
                        help='配置文件路径 (默认: config.json)')
    parser.add_argument('--templates', default='templates',
                        help='模板图片目录 (默认: templates/)')
    parser.add_argument('--duration', type=int, default=0,
                        help='运行时长（秒），0=无限 (默认: 0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式：只截屏检测状态，不执行操作')
    return parser.parse_args()


def main():
    args = parse_args()

    # 加载配置
    cfg.load(args.config)

    # 创建后端
    if args.backend == 'adb':
        backend = ADBBackend(serial=args.serial)
    else:
        backend = UnityBackend(url=args.url)

    # 连接
    print(f"正在连接 ({args.backend})...")
    if not backend.connect():
        print("连接失败，退出")
        sys.exit(1)

    # 创建视觉引擎
    vision = Vision(template_dir=args.templates)

    # 创建状态机
    sm = StateMachine(backend, vision)

    # Ctrl+C 优雅退出
    def signal_handler(sig, frame):
        print("\n收到退出信号，正在停止...")
        sm.stop()
        sm.save_log()
        backend.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 启动
    sm.start()
    print("=" * 40)
    print("  游戏冒烟测试已启动")
    print("  按 Ctrl+C 停止")
    print("=" * 40)

    start_time = time.time()

    while sm.running:
        # 检查运行时长
        if args.duration > 0:
            elapsed = time.time() - start_time
            if elapsed >= args.duration:
                print(f"已达到设定时长 {args.duration} 秒，停止")
                break

        try:
            sm.tick()
        except Exception as e:
            sm.log(f"异常: {e}")
            time.sleep(1)

    # 清理
    sm.stop()
    sm.save_log()
    backend.disconnect()
    print("测试结束")


if __name__ == '__main__':
    main()
