#!/usr/bin/env python3
"""
抖音发布 CLI
用法: python3 douyin_publish_cli.py --video /path/to/video.mp4 --title "标题" --desc "描述"
"""
import argparse
import sys
import os
import subprocess
import time

def get_ws_url():
    """获取 MCP 浏览器的 WebSocket URL（通过 daemon acquire 接口）"""
    import json
    try:
        # 检查 daemon 是否运行
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', '3', 'http://127.0.0.1:40225/health'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 or '"ok":true' not in (result.stdout or ''):
            # Daemon 没运行，用 xvfb 启动
            subprocess.Popen(
                ['xvfb-run', '-a', 'node', 'src/daemon/server.js'],
                cwd=os.path.expanduser('~/.openclaw/workspace/skills/douyin-upload-mcp-skill'),
                stdout=open('/tmp/douyin-daemon.log', 'a'),
                stderr=subprocess.STDOUT
            )
            time.sleep(6)
        
        # 通过 acquire 接口启动/获取浏览器
        result = subprocess.run(
            ['curl', '-s', 'http://127.0.0.1:40225/browser/acquire'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('ok'):
                return data.get('wsEndpoint', '')
            else:
                print("acquire 失败: %s" % data.get('error', ''))
    except Exception as e:
        print("获取浏览器URL失败: %s" % e)
    return ''

def main():
    parser = argparse.ArgumentParser(description='抖音视频发布')
    parser.add_argument('--video', required=True, help='视频文件路径')
    parser.add_argument('--title', required=True, help='视频标题')
    parser.add_argument('--desc', default='', help='视频描述')
    parser.add_argument('--cover', default='', help='封面图路径')
    parser.add_argument('--ws-url', default='', help='浏览器 WebSocket URL')
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print("视频文件不存在: %s" % args.video)
        sys.exit(1)
    
    # 默认封面（抖音用竖屏）
    cover_path = args.cover
    if not cover_path:
        cover_path = os.path.join(os.path.dirname(__file__), 'assets', 'cover_douyin.jpg')
        if not os.path.exists(cover_path):
            cover_path = os.path.join(os.path.dirname(__file__), '..', 'ai-video-pipeline', 'assets', 'cover_douyin.jpg')
        if not os.path.exists(cover_path):
            cover_path = os.path.join(os.path.dirname(__file__), 'assets', 'cover.jpg')
    
    if not os.path.exists(cover_path):
        print("封面文件不存在: %s" % cover_path)
        sys.exit(1)
    
    # 获取浏览器 URL
    ws_url = args.ws_url
    if not ws_url:
        ws_url = get_ws_url()
    
    if not ws_url:
        print("无法获取浏览器 URL，请确保 MCP 浏览器在运行")
        sys.exit(1)
    
    print("浏览器: %s" % ws_url[:50])
    print("视频: %s" % args.video)
    print("标题: %s" % args.title)
    print("描述: %s" % args.desc)
    print("封面: %s" % cover_path)
    
    # 导入发布模块
    sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/douyin-bot/modules'))
    from douyin_publish import publish_video
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(ws_url)
        # 使用已有 context，不要关闭现有页面（会导致 daemon 退出）
        if browser.contexts:
            ctx = browser.contexts[0]
        else:
            ctx = browser.new_context()
        time.sleep(1)
        
        page = ctx.new_page()
        page.set_default_timeout(30000)
        
        result = publish_video(
            page=page,
            video_path=args.video,
            title=args.title,
            description=args.desc,
            cover_path=cover_path
        )
        
        print("\n结果: %s" % result['message'])
        
        if result['success']:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
