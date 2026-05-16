#!/usr/bin/env python3
"""
抖音创作者平台 - 登录脚本 v3
检测逻辑：有「扫码登录」文字 = 未登录，有「工作台」= 已登录
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


def save_cookies(context):
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"[抖音] Cookies 已保存 ({len(cookies)} 条)", flush=True)


def is_logged_in(page):
    """严格检测：必须有「工作台」或页面不含「扫码登录」"""
    try:
        text = page.inner_text("body")
        # 有这些文字说明还在登录页
        if "扫码登录" in text:
            return False
        if "验证码登录" in text and "工作台" not in text:
            return False
        # 有这些说明到了创作者后台
        if "工作台" in text or "内容管理" in text or "数据中心" in text:
            return True
        # URL 跳转到了具体功能页
        url = page.url
        if "creator.douyin.com" in url and "login" not in url and "passport" not in url:
            # 再等一下看有没有后台内容
            time.sleep(2)
            text2 = page.inner_text("body")
            if "扫码登录" not in text2 and ("工作台" in text2 or "发布" in text2 or "首页" in text2):
                return True
        return False
    except:
        return False


def login_qr():
    """扫码登录"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        print("[抖音] 打开登录页...", flush=True)
        page.goto("https://creator.douyin.com/", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        time.sleep(3)

        # 截图
        qr_path = os.path.join(SCREENSHOTS_DIR, "qr_code.png")
        page.screenshot(path=qr_path)
        print(f"[抖音] QR_IMAGE_PATH={qr_path}", flush=True)

        # 等待扫码（最多 180 秒）
        print("[抖音] 等待扫码登录...", flush=True)
        for i in range(90):
            time.sleep(2)
            if is_logged_in(page):
                print(f"[抖音] ✅ 登录成功!", flush=True)
                save_cookies(context)
                page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "logged_in.png"))
                browser.close()
                return True
            if i % 10 == 0 and i > 0:
                print(f"[抖音] 还在等... ({i*2}s)", flush=True)

        print("[抖音] ❌ 超时", flush=True)
        browser.close()
        return False


def login_phone(phone: str):
    """手机号验证码登录"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        print("[抖音] 打开登录页...", flush=True)
        page.goto("https://creator.douyin.com/", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        time.sleep(3)

        # 点击「验证码登录」tab
        print("[抖音] 切换到验证码登录...", flush=True)
        sms_tab = page.locator('text=验证码登录')
        if sms_tab.count() > 0:
            sms_tab.first.click()
            time.sleep(1)

        # 输入手机号
        phone_input = page.locator('input[placeholder*="手机号"], input[type="tel"]')
        if phone_input.count() > 0:
            phone_input.first.fill(phone)
            print(f"[抖音] 已输入手机号: {phone[:3]}****{phone[-4:]}", flush=True)
        else:
            print("[抖音] ❌ 找不到手机号输入框", flush=True)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "phone_fail.png"))
            browser.close()
            return False

        # 点击「获取验证码」
        send_btn = page.locator('text=获取验证码')
        if send_btn.count() > 0:
            send_btn.first.click()
            print("[抖音] 已点击获取验证码", flush=True)
            time.sleep(2)
        else:
            print("[抖音] ⚠️  找不到获取验证码按钮", flush=True)

        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "phone_code_sent.png"))

        # 输出信号，让外层知道需要验证码
        print("[抖音] NEED_VERIFICATION_CODE", flush=True)

        # 从 stdin 读取验证码
        code = input().strip()
        if not code:
            print("[抖音] ❌ 未输入验证码", flush=True)
            browser.close()
            return False

        # 输入验证码
        code_input = page.locator('input[placeholder*="验证码"], input[placeholder*="输入验证码"]')
        if code_input.count() > 0:
            code_input.first.fill(code)
            time.sleep(0.5)

        # 点击登录
        login_btn = page.locator('button:has-text("登录"), button:has-text("登录/注册")')
        if login_btn.count() > 0:
            login_btn.first.click()
            print("[抖音] 已点击登录", flush=True)

        time.sleep(5)

        # 等待登录完成
        for i in range(15):
            time.sleep(2)
            if is_logged_in(page):
                print(f"[抖音] ✅ 登录成功!", flush=True)
                save_cookies(context)
                page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "logged_in.png"))
                browser.close()
                return True

        print("[抖音] ❌ 登录失败", flush=True)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "login_fail.png"))
        browser.close()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--phone" and len(sys.argv) > 2:
        success = login_phone(sys.argv[2])
    else:
        success = login_qr()

    print(f"\n{'✅ 登录完成' if success else '❌ 登录失败'}")
    sys.exit(0 if success else 1)
