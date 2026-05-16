#!/usr/bin/env python3
"""抖音手机号登录 - 一体化脚本
用法: python3 phone_login.py <手机号> [验证码]
  不传验证码 = 只发验证码并等待
  传验证码 = 输入验证码完成登录
"""
import os, sys, json, time
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIES_PATH = os.path.join(PROJECT_DIR, "config", "cookies.json")
STATE_PATH = os.path.join(PROJECT_DIR, "config", "browser_state.json")
SCREENSHOTS_DIR = os.path.join(PROJECT_DIR, "output", "screenshots")
CODE_FILE = os.path.join(PROJECT_DIR, "config", "pending_code.txt")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

phone = sys.argv[1]
code = sys.argv[2] if len(sys.argv) > 2 else None


def save_cookies(context):
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"[抖音] Cookies 已保存 ({len(cookies)} 条)", flush=True)


def is_logged_in(page):
    try:
        text = page.inner_text("body")
        if "扫码登录" in text:
            return False
        if "工作台" in text or "内容管理" in text or "数据中心" in text:
            return True
        return False
    except:
        return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    )

    # 如果有保存的状态，加载
    if os.path.exists(STATE_PATH):
        try:
            context.close()
            context = browser.new_context(storage_state=STATE_PATH)
            print("[抖音] 已加载浏览器状态", flush=True)
        except:
            pass

    page = context.new_page()

    if code is None:
        # ===== 第一步：输入手机号，发验证码 =====
        print("[抖音] 打开登录页...", flush=True)
        page.goto("https://creator.douyin.com/", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        time.sleep(3)

        # 切到验证码登录
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

        # 点击获取验证码
        send_btn = page.locator('text=获取验证码')
        if send_btn.count() > 0:
            send_btn.first.click()
            print("[抖音] 已点击获取验证码", flush=True)
        else:
            print("[抖音] ⚠️ 找不到获取验证码按钮", flush=True)

        time.sleep(3)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "code_sent.png"))
        print(f"[抖音] 截图: {os.path.join(SCREENSHOTS_DIR, 'code_sent.png')}", flush=True)

        # 保存状态
        context.storage_state(path=STATE_PATH)
        print(f"[抖音] STATE_SAVED", flush=True)

        # 等待验证码文件
        print(f"[抖音] WAITING_CODE_FILE={CODE_FILE}", flush=True)
        print(f"[抖音] 请将验证码写入: {CODE_FILE}", flush=True)

        # 清空旧验证码
        if os.path.exists(CODE_FILE):
            os.remove(CODE_FILE)

        # 等待最多 120 秒
        for i in range(60):
            time.sleep(2)
            if os.path.exists(CODE_FILE):
                with open(CODE_FILE) as f:
                    code = f.read().strip()
                if code:
                    print(f"[抖音] 收到验证码: {code}", flush=True)
                    break
            if i % 10 == 0:
                print(f"[抖音] 等待验证码... ({i*2}s)", flush=True)

        if not code:
            print("[抖音] ❌ 超时未收到验证码", flush=True)
            browser.close()
            sys.exit(1)

    # ===== 第二步：输入验证码，完成登录 =====
    # 重新加载状态
    if os.path.exists(STATE_PATH):
        try:
            context.close()
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                storage_state=STATE_PATH,
            )
            page = context.new_page()
            page.goto("https://creator.douyin.com/", timeout=30000)
            time.sleep(3)
            print("[抖音] 已重新加载页面", flush=True)
        except Exception as e:
            print(f"[抖音] 重新加载失败: {e}", flush=True)

    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "before_code.png"))

    # 输入验证码
    code_input = page.locator('input[placeholder*="验证码"], input[placeholder*="输入验证码"], input[type="tel"]:not([placeholder*="手机号"])')
    if code_input.count() > 0:
        code_input.first.fill(code)
        print(f"[抖音] 已输入验证码: {code}", flush=True)
    else:
        # 尝试找所有 input
        all_inputs = page.locator('input')
        print(f"[抖音] 找到 {all_inputs.count()} 个 input 元素", flush=True)
        for i in range(all_inputs.count()):
            inp = all_inputs.nth(i)
            placeholder = inp.get_attribute("placeholder") or ""
            input_type = inp.get_attribute("type") or ""
            print(f"  input[{i}]: type={input_type}, placeholder={placeholder}", flush=True)

    time.sleep(1)

    # 点击登录按钮
    login_btn = page.locator('button:has-text("登录/注册"), button:has-text("登录")')
    if login_btn.count() > 0:
        login_btn.first.click()
        print("[抖音] 已点击登录", flush=True)
    else:
        print("[抖音] ⚠️ 找不到登录按钮", flush=True)

    time.sleep(5)

    # 检查是否登录成功
    for i in range(15):
        time.sleep(2)
        if is_logged_in(page):
            print("[抖音] ✅ 登录成功!", flush=True)
            save_cookies(context)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "logged_in.png"))
            browser.close()
            sys.exit(0)
        # 检查是否有错误提示
        text = page.inner_text("body")
        if "验证码错误" in text or "验证码不正确" in text:
            print("[抖音] ❌ 验证码错误", flush=True)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "code_error.png"))
            browser.close()
            sys.exit(1)
        if i % 5 == 0:
            print(f"[抖音] 等待登录... ({i*2}s)", flush=True)

    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "login_timeout.png"))
    print("[抖音] ❌ 登录超时", flush=True)
    browser.close()
    sys.exit(1)
