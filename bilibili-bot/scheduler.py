#!/usr/bin/env python3
"""
定时调度器 - 每天定时运行流水线
支持: Linux cron / systemd timer / 直接运行
"""
import os
import sys
import json
import subprocess
from datetime import datetime

# 项目路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_SCRIPT = os.path.join(PROJECT_DIR, "pipeline.py")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "api_keys.json")


def check_config() -> bool:
    """检查配置是否完整"""
    if not os.path.exists(CONFIG_PATH):
        print("❌ 配置文件不存在: config/api_keys.json")
        print("请先运行: python3 setup.py")
        return False

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    required = ["mimo_api_key"]
    optional = ["jimeng_access_key", "jimeng_secret_key", "bili_sessdata", "bili_jct"]

    for key in required:
        if not config.get(key):
            print(f"❌ 缺少必要配置: {key}")
            return False

    missing_optional = [k for k in optional if not config.get(k)]
    if missing_optional:
        print(f"⚠️ 可选配置缺失: {', '.join(missing_optional)}")
        print("  → 即梦未配置将使用占位视频，B站未配置将跳过发布")

    return True


def run_pipeline(topic: str = None, count: int = 1):
    """运行流水线"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"🚀 流水线启动: {timestamp}")
    print(f"{'='*50}\n")

    cmd = [sys.executable, PIPELINE_SCRIPT, "--count", str(count)]
    if topic:
        cmd.extend(["--topic", topic])

    log_file = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            cwd=PROJECT_DIR,
        )

        # 保存日志
        with open(log_file, "w") as f:
            f.write(f"=== STDOUT ===\n{result.stdout}\n")
            f.write(f"=== STDERR ===\n{result.stderr}\n")
            f.write(f"=== Return Code: {result.returncode} ===\n")

        if result.returncode == 0:
            print(f"✅ 流水线完成! 日志: {log_file}")
        else:
            print(f"❌ 流水线失败 (code={result.returncode})")
            print(f"日志: {log_file}")
            if result.stderr:
                print(f"错误: {result.stderr[:500]}")

    except subprocess.TimeoutExpired:
        print("❌ 流水线超时 (>10分钟)")
    except Exception as e:
        print(f"❌ 流水线异常: {e}")


def install_cron(schedule: str = "0 11,19 * * *"):
    """安装 cron 定时任务
    默认: 每天 11:00 和 19:00 运行
    """
    cron_cmd = f"cd {PROJECT_DIR} && {sys.executable} {os.path.join(PROJECT_DIR, 'scheduler.py')} >> {LOG_DIR}/cron.log 2>&1"

    # 获取现有 crontab
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""
    except Exception:
        existing = ""

    # 检查是否已存在
    marker = "# bilibili-bot-pipeline"
    if marker in existing:
        print("⚠️ 已存在 crontab 任务，先移除旧任务...")
        lines = [l for l in existing.split("\n") if marker not in l and l.strip()]
        existing = "\n".join(lines)

    # 添加新任务
    new_cron = f"{existing}\n{schedule} {cron_cmd} {marker}\n".strip() + "\n"

    try:
        proc = subprocess.run(["crontab", "-"], input=new_cron, text=True)
        if proc.returncode == 0:
            print(f"✅ Cron 任务已安装: {schedule}")
            print(f"   命令: {cron_cmd}")
        else:
            print("❌ 安装 cron 任务失败")
    except Exception as e:
        print(f"❌ 安装 cron 异常: {e}")


def uninstall_cron():
    """卸载 cron 定时任务"""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            print("没有已安装的 crontab 任务")
            return

        marker = "# bilibili-bot-pipeline"
        lines = [l for l in result.stdout.split("\n") if marker not in l and l.strip()]
        new_cron = "\n".join(lines).strip() + "\n"

        proc = subprocess.run(["crontab", "-"], input=new_cron, text=True)
        if proc.returncode == 0:
            print("✅ Cron 任务已卸载")
        else:
            print("❌ 卸载失败")
    except Exception as e:
        print(f"❌ 卸载异常: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="B站视频流水线调度器")
    parser.add_argument("action", choices=["run", "install", "uninstall", "check"],
                       help="run=运行, install=安装定时, uninstall=卸载定时, check=检查配置")
    parser.add_argument("--topic", type=str, help="指定话题")
    parser.add_argument("--count", type=int, default=1, help="视频数量")
    parser.add_argument("--schedule", type=str, default="0 11,19 * * *",
                       help="Cron 表达式 (默认: 每天11点和19点)")
    args = parser.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)

    if args.action == "check":
        check_config()
    elif args.action == "run":
        if check_config():
            run_pipeline(topic=args.topic, count=args.count)
    elif args.action == "install":
        if check_config():
            install_cron(args.schedule)
    elif args.action == "uninstall":
        uninstall_cron()


if __name__ == "__main__":
    main()
