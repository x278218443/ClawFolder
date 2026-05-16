#!/usr/bin/env python3
"""抖音手机号登录 - 第一步：输入手机号，发验证码"""
import os, sys, json, time
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(PROJECT_DIR, "output", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

phone = sys.argv[1]

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
        phone_input.first.click()
        phone_input.first.fill(phone)
        print(f"[抖音] 已输入手机号: {phone[:3]}****{phone[-4:]}", flush=True)
    else:
        print("[抖音] ❌ 找不到手机号输入框", flush=True)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "phone_fail.png"))
        browser.close()
        sys.exit(1)

    time.sleep(1)

    # 点击「获取验证码」
    send_btn = page.locator('text=获取验证码')
    if send_btn.count() > 0:
        send_btn.first.click()
        print("[抖音] 已点击获取验证码", flush=True)
    else:
        # 尝试其他按钮
        send_btn2 = page.locator('button:has-text("获取"), span:has-text("获取验证码")')
        if send_btn2.count() > 0:
            send_btn2.first.click()
            print("[抖音] 已点击获取验证码(备选)", flush=True)
        else:
            print("[抖音] ⚠️ 找不到获取验证码按钮", flush=True)

    time.sleep(2)

    # 截图
    screenshot_path = os.path.join(SCREENSHOTS_DIR, "phone_code_sent.png")
    page.screenshot(path=screenshot_path)
    print(f"[抖音] 截图: {screenshot_path}", flush=True)

    # 保存浏览器状态供第二步使用
    state_path = os.path.join(PROJECT_DIR, "config", "browser_state.json")
    context.storage_state(path=state_path)
    print(f"[抖音] BROWSER_STATE={state_path}", flush=True)
    print("[抖音] NEED_CODE", flush=True)

    browser.close()
