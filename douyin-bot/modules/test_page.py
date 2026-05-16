#!/usr/bin/env python3
"""
抖音创作者平台 - 页面探测脚本
打开 creator.douyin.com，截图看状态
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
    """保存 cookies 到文件"""
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"[抖音] Cookies 已保存: {COOKIES_PATH}")


def load_cookies(context):
    """从文件加载 cookies"""
    if not os.path.exists(COOKIES_PATH):
        return False
    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print(f"[抖音] 已加载 cookies: {len(cookies)} 条")
        return True
    except Exception as e:
        print(f"[抖音] 加载 cookies 失败: {e}")
        return False


def test_page():
    """打开创作者平台，截图检查"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 尝试加载已有 cookies
        load_cookies(context)

        page = context.new_page()

        print("[抖音] 打开创作者平台...")
        page.goto("https://creator.douyin.com/", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        # 截图
        screenshot_path = os.path.join(SCREENSHOTS_DIR, "creator_page.png")
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"[抖音] 截图已保存: {screenshot_path}")

        # 检查页面状态
        url = page.url
        title = page.title()
        print(f"[抖音] 当前 URL: {url}")
        print(f"[抖音] 页面标题: {title}")

        # 检查是否需要登录
        content = page.content()
        if "登录" in content or "login" in url.lower() or "passport" in url.lower():
            print("[抖音] ⚠️  需要登录！")
            # 保存二维码截图
            qr_path = os.path.join(SCREENSHOTS_DIR, "login_qr.png")
            page.screenshot(path=qr_path, full_page=True)
            print(f"[抖音] 登录页截图: {qr_path}")

            # 尝试找到二维码图片
            qr_imgs = page.query_selector_all('img[src*="qrcode"], img[src*="qr"], canvas')
            if qr_imgs:
                print(f"[抖音] 找到 {len(qr_imgs)} 个可能的二维码元素")

            # 检查是否有扫码区域
            scan_area = page.query_selector('[class*="qrcode"], [class*="scan"], [class*="login-scan"]')
            if scan_area:
                box = scan_area.bounding_box()
                if box:
                    print(f"[抖音] 扫码区域位置: {box}")

            return {"status": "need_login", "screenshot": qr_path}

        # 已登录，检查页面元素
        print("[抖音] ✅ 看起来已登录")
        
        # 查找上传按钮
        upload_btns = page.query_selector_all('[class*="upload"], [class*="publish"], button:has-text("上传"), button:has-text("发布")')
        print(f"[抖音] 找到 {len(upload_btns)} 个上传/发布相关元素")
        for btn in upload_btns[:5]:
            text = btn.inner_text().strip()[:50]
            cls = btn.get_attribute("class") or ""
            print(f"  - [{cls[:40]}] {text}")

        return {"status": "logged_in", "screenshot": screenshot_path}


if __name__ == "__main__":
    result = test_page()
    print(f"\n结果: {json.dumps(result, ensure_ascii=False)}")
