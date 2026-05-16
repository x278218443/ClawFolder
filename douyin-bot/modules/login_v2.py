#!/usr/bin/env python3
"""
抖音创作者平台 - 登录脚本 v2
支持两种方式：
1. 扫码登录（截图发给用户）
2. 手机号登录（自动填写，用户输入验证码）

用法：
  python3 modules/login_v2.py              # 默认扫码
  python3 modules/login_v2.py --phone 手机号  # 手机号登录
"""
import os
import sys
import json
import time
import argparse
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
COOKIES_PATH = os.path.join(PROJECT_DIR, "config", "cookies.json")
SCREENSHOTS_DIR = os.path.join(PROJECT_DIR, "output", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def save_cookies(context):
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"[抖音] Cookies 已保存 ({len(cookies)} 条)", flush=True)


def is_logged_in(page):
    """检查是否已登录 - 通过检测页面元素判断"""
    try:
        # 方法1: 检查 URL 是否跳转到非登录页
        url = page.url
        if "passport" in url or "sso" in url:
            return False

        # 方法2: 检查页面是否有用户头像/用户名（登录后才有）
        avatar = page.query_selector('[class*="avatar"], [class*="user-info"], [class*="header-user"]')
        if avatar:
            return True

        # 方法3: 检查是否有创作者中心的功能菜单
        menu = page.query_selector('[class*="menu"], [class*="sidebar"], [class*="nav"]')
        # 同时不存在登录按钮
        login_btn = page.query_selector('button:has-text("登录"), [class*="login-btn"], [class*="qrcode-login"]')
        if menu and not login_btn:
            return True

        # 方法4: 检查是否有"上传视频"按钮（登录后才有）
        upload = page.query_selector(':has-text("上传视频"), :has-text("发布视频"), [class*="upload"]')
        if upload:
            return True

        return False
    except:
        return False


def wait_for_login(page, timeout_sec=180):
    """等待用户扫码或输入验证码完成登录"""
    print(f"[抖音] 等待登录...（最多 {timeout_sec} 秒）", flush=True)
    
    for i in range(timeout_sec // 2):
        time.sleep(2)
        
        if is_logged_in(page):
            print(f"[抖音] ✅ 登录成功!", flush=True)
            return True

        # 检查是否跳转到了新页面
        url = page.url
        if "creator.douyin.com" in url and "login" not in url.lower():
            # 可能已登录，再等一下让页面加载完
            time.sleep(3)
            if is_logged_in(page):
                print(f"[抖音] ✅ 登录成功!", flush=True)
                return True

        if i % 10 == 0 and i > 0:
            # 每20秒截图一次看进度
            progress_path = os.path.join(SCREENSHOTS_DIR, f"waiting_{i*2}s.png")
            page.screenshot(path=progress_path)
            print(f"[抖音] 还在等待... ({i*2}s)", flush=True)

    print(f"[抖音] ❌ 超时", flush=True)
    return False


def login_qr():
    """扫码登录流程"""
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
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass  # 网络一直有活动也无所谓
        time.sleep(3)

        # 截二维码
        qr_path = os.path.join(SCREENSHOTS_DIR, "qr_code.png")
        page.screenshot(path=qr_path)
        print(f"[抖音] 二维码截图: {qr_path}", flush=True)
        print(f"[抖音] QR_IMAGE_PATH={qr_path}", flush=True)

        # 等待扫码
        if wait_for_login(page, timeout_sec=180):
            save_cookies(context)
            confirm_path = os.path.join(SCREENSHOTS_DIR, "logged_in.png")
            page.screenshot(path=confirm_path)
            print(f"[抖音] 登录后截图: {confirm_path}", flush=True)
            browser.close()
            return True

        browser.close()
        return False


def login_phone(phone: str):
    """手机号登录流程"""
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

        print(f"[抖音] 打开登录页...", flush=True)
        page.goto("https://creator.douyin.com/", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        time.sleep(3)

        # 切换到手机号登录
        print("[抖音] 切换到手机号登录...", flush=True)
        
        # 尝试点击"手机号登录"或类似按钮
        phone_tab = page.query_selector(':has-text("手机号"), :has-text("密码登录"), :has-text("账号登录")')
        if phone_tab:
            phone_tab.click()
            time.sleep(1)

        # 输入手机号
        phone_input = page.query_selector('input[type="tel"], input[placeholder*="手机号"], input[name*="phone"], input[name*="mobile"]')
        if phone_input:
            phone_input.fill(phone)
            print(f"[抖音] 已输入手机号: {phone[:3]}****{phone[-4:]}", flush=True)
        else:
            print("[抖音] ❌ 找不到手机号输入框", flush=True)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "phone_login_fail.png"))
            browser.close()
            return False

        # 点击发送验证码
        send_btn = page.query_selector('button:has-text("验证码"), button:has-text("获取"), button:has-text("发送")')
        if send_btn:
            send_btn.click()
            print("[抖音] 已点击发送验证码", flush=True)
        else:
            print("[抖音] ⚠️  找不到发送验证码按钮", flush=True)

        # 截图
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "phone_code_sent.png"))

        # 等待用户输入验证码（从 stdin 读取）
        print("[抖音] VERIFICATION_CODE_NEEDED", flush=True)
        print("[抖音] 请查看手机验证码，然后输入:", flush=True)
        
        code = input().strip()
        if not code:
            print("[抖音] ❌ 未输入验证码", flush=True)
            browser.close()
            return False

        # 输入验证码
        code_input = page.query_selector('input[placeholder*="验证码"], input[placeholder*="code"], input[name*="code"], input[name*="captcha"]')
        if code_input:
            code_input.fill(code)
            time.sleep(0.5)

        # 点击登录
        login_btn = page.query_selector('button:has-text("登录"), button[type="submit"]')
        if login_btn:
            login_btn.click()
            print("[抖音] 已点击登录", flush=True)

        time.sleep(5)

        if wait_for_login(page, timeout_sec=30):
            save_cookies(context)
            confirm_path = os.path.join(SCREENSHOTS_DIR, "logged_in.png")
            page.screenshot(path=confirm_path)
            print(f"[抖音] 登录后截图: {confirm_path}", flush=True)
            browser.close()
            return True

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "login_fail.png"))
        browser.close()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", type=str, help="手机号登录（不指定则扫码）")
    args = parser.parse_args()

    if args.phone:
        success = login_phone(args.phone)
    else:
        success = login_qr()

    print(f"\n{'✅ 登录完成' if success else '❌ 登录失败'}")
    sys.exit(0 if success else 1)
