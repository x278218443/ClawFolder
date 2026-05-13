#!/usr/bin/env python3
"""
初始化配置脚本 - 引导用户配置 API 密钥
"""
import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "api_keys.json")


def main():
    print("=" * 50)
    print("🔧 B站全自动短视频流水线 - 配置向导")
    print("=" * 50)

    config = {}

    # 加载已有配置
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        print("\n检测到已有配置，将保留未修改的值。\n")

    # ===== MiMo 模型 (必填) =====
    print("\n📌 [1/4] MiMo 模型配置 (必填)")
    print("用于 AI 生成视频脚本和配音")
    print("获取方式: https://platform.xiaomimimo.com/#/console/api-keys")
    print(f"当前值: {config.get('mimo_api_key', '未配置')[:20]}...")

    mimo_key = input("MiMo API Key (留空保持当前值): ").strip()
    if mimo_key:
        config["mimo_api_key"] = mimo_key

    mimo_url = input(f"MiMo Base URL [{config.get('mimo_base_url', 'https://token-plan-cn.xiaomimimo.com/v1')}]: ").strip()
    if mimo_url:
        config["mimo_base_url"] = mimo_url
    elif "mimo_base_url" not in config:
        config["mimo_base_url"] = "https://token-plan-cn.xiaomimimo.com/v1"

    # ===== 即梦 API (可选) =====
    print("\n📌 [2/4] 即梦 API 配置 (可选)")
    print("用于 AI 生成视频画面")
    print("获取方式: https://console.volcengine.com/iam/keymanage/")
    print(f"当前值: AK={config.get('jimeng_access_key', '未配置')[:15]}...")

    jimeng_ak = input("火山引擎 Access Key (留空保持, 输入skip跳过): ").strip()
    if jimeng_ak and jimeng_ak != "skip":
        config["jimeng_access_key"] = jimeng_ak

    jimeng_sk = input("火山引擎 Secret Key (留空保持): ").strip()
    if jimeng_sk:
        config["jimeng_secret_key"] = jimeng_sk

    # ===== B站账号 (可选) =====
    print("\n📌 [3/4] B站账号配置 (可选)")
    print("用于自动发布视频到B站")
    print("获取方式: 登录B站 → F12 → Application → Cookies")
    print(f"当前值: SESSDATA={config.get('bili_sessdata', '未配置')[:15]}...")

    bili_sess = input("B站 SESSDATA (留空保持): ").strip()
    if bili_sess:
        config["bili_sessdata"] = bili_sess

    bili_jct = input("B站 bili_jct (留空保持): ").strip()
    if bili_jct:
        config["bili_jct"] = bili_jct

    # ===== 保存 =====
    print("\n📌 [4/4] 保存配置...")
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 配置已保存到: {CONFIG_PATH}")
    print("\n配置摘要:")
    for key, value in config.items():
        if value:
            display = value[:20] + "..." if len(str(value)) > 20 else value
            print(f"  ✅ {key}: {display}")
        else:
            print(f"  ❌ {key}: 未配置")

    print("\n下一步:")
    print("  1. 试运行: python3 scheduler.py run --dry-run")
    print("  2. 正式运行: python3 scheduler.py run")
    print("  3. 安装定时任务: python3 scheduler.py install")


if __name__ == "__main__":
    main()
