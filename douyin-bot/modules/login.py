#!/usr/bin/env python3
"""
抖音创作者平台 - 登录脚本
打开登录页 → 截取二维码 → 等待扫码 → 保存 cookies
"""
import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
COOKIES_PATH = os.path.join(PROJECT_DIR, "config", "cookies.json")
SCREENSHOTS_DIR = os.path.join(PROJECT_DIR, "output", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

QR_IMAGE_PATH = os.path.join(SCREENSHOTS_DIR, "qr_code.png")


def login():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        print("[抖音] 打开登录页...", flush=True)
        page.goto("https://creator.douyin.com/", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        # 截取二维码区域
        # 先找二维码元素
        qr_area = page.query_selector('[class*="qrcode"], [class*="scan"], [class*="login-scan"]')
        if qr_area:
            qr_area.screenshot(path=QR_IMAGE_PATH)
            print(f"[抖音] 二维码已截取: {QR_IMAGE_PATH}", flush=True)
        else:
            # 整页截图
            page.screenshot(path=QR_IMAGE_PATH)
            print(f"[抖音] 未找到二维码区域，已截整页: {QR_IMAGE_PATH}", flush=True)

        # 等待扫码成功（最多 120 秒）
        print("[抖音] 等待扫码...（请用抖音 APP 扫描二维码）", flush=True)
        print("[抖音] 二维码图片路径: " + QR_IMAGE_PATH, flush=True)

        for i in range(120):
            time.sleep(2)
            current_url = page.url
            content = page.content()

            # 检查是否已跳转到主页（登录成功）
            if "creator.douyin.com" in current_url and "login" not in current_url.lower() and "passport" not in current_url.lower():
                # 再确认一下页面内容
                if "登录" not in content[:500] or "dashboard" in content.lower() or "管理" in content:
                    print(f"[抖音] ✅ 登录成功! URL: {current_url}", flush=True)
                    
                    # 保存 cookies
                    cookies = context.cookies()
                    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    print(f"[抖音] Cookies 已保存: {COOKIES_PATH} ({len(cookies)} 条)", flush=True)

                    # 截图确认
                    confirm_path = os.path.join(SCREENSHOTS_DIR, "logged_in.png")
                    page.screenshot(path=confirm_path)
                    print(f"[抖音] 登录后截图: {confirm_path}", flush=True)

                    browser.close()
                    return True

            # 每 10 秒输出一次状态
            if i % 5 == 0:
                print(f"[抖音] 等待中... ({i*2}s)", flush=True)

        print("[抖音] ❌ 等待超时（120秒），请重试", flush=True)
        browser.close()
        return False


if __name__ == "__main__":
    success = login()
    if success:
        print("\n✅ 登录完成，cookies 已保存")
    else:
        print("\n❌ 登录失败，请重试")
    sys.exit(0 if success else 1)
