"""
抖音自动发布模块
关键：必须上传自定义封面，否则 create_v2 会被静默拒绝
"""
import time
import re
import os

COVER_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'ai-video-pipeline', 'assets', 'cover.jpg')

def publish_video(page, video_path, title, description='', cover_path=None):
    """
    通过 Playwright page 发布视频到抖音
    
    Args:
        page: Playwright page 对象（已登录抖音创作者平台）
        video_path: 视频文件路径
        title: 视频标题
        description: 视频描述（可选，最多30字）
        cover_path: 封面图路径（可选，默认用 assets/cover.jpg）
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    if cover_path is None:
        cover_path = COVER_PATH
    
    cover_path = os.path.abspath(cover_path)
    video_path = os.path.abspath(video_path)
    
    if not os.path.exists(video_path):
        return {'success': False, 'message': '视频文件不存在: %s' % video_path}
    
    if not os.path.exists(cover_path):
        return {'success': False, 'message': '封面文件不存在: %s' % cover_path}
    
    try:
        # Step 1: Navigate to upload page
        print("[抖音] 打开上传页面...")
        page.goto('https://creator.douyin.com/creator-micro/content/upload', 
                   wait_until='networkidle', timeout=30000)
        time.sleep(3)
        
        # Step 2: Upload video
        print("[抖音] 上传视频...")
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(video_path)
        
        # Step 3: Wait for upload to complete
        print("[抖音] 等待上传完成...")
        for i in range(120):
            time.sleep(3)
            body = page.inner_text('body')
            has_uploading = '上传中' in body or '正在上传' in body
            has_form = '作品描述' in body and '选择封面' in body
            
            if has_form and not has_uploading:
                print("[抖音] 上传完成")
                break
            if i % 10 == 0 and i > 0:
                print("[抖音] 处理中... (%ds)" % ((i+1)*3))
        else:
            return {'success': False, 'message': '上传超时'}
        
        time.sleep(5)
        
        # Step 4: Upload custom cover (CRITICAL!)
        print("[抖音] 上传自定义封面...")
        cover_inputs = page.locator('input[type="file"][accept*="image"]')
        if cover_inputs.count() > 0:
            cover_inputs.last.set_input_files(cover_path)
            print("[抖音] 封面已上传")
            time.sleep(5)
            
            # Click "裁切" to crop
            crop_btn = page.locator('button:has-text("裁切")')
            if crop_btn.count() > 0:
                crop_btn.first.click(force=True, timeout=5000)
                print("[抖音] 已裁切")
                time.sleep(3)
            
            # Click "完成" to confirm cover
            done_btn = page.locator('button:has-text("完成")')
            if done_btn.count() > 0:
                done_btn.first.click(force=True, timeout=5000)
                print("[抖音] 封面已确认")
                time.sleep(3)
        else:
            # Try clicking "选择封面" to open cover panel first
            cover_area = page.locator('text=选择封面')
            if cover_area.count() > 0:
                cover_area.first.click(timeout=5000)
                time.sleep(3)
                # Now try uploading
                cover_inputs = page.locator('input[type="file"][accept*="image"]')
                if cover_inputs.count() > 0:
                    cover_inputs.last.set_input_files(cover_path)
                    time.sleep(5)
                    crop_btn = page.locator('button:has-text("裁切")')
                    if crop_btn.count() > 0:
                        crop_btn.first.click(force=True, timeout=5000)
                        time.sleep(3)
                    done_btn = page.locator('button:has-text("完成")')
                    if done_btn.count() > 0:
                        done_btn.first.click(force=True, timeout=5000)
                        time.sleep(3)
        
        # Step 4.5: 确保裁切弹窗已关闭
        print("[抖音] 关闭裁切弹窗...")
        time.sleep(3)
        # 先尝试点击遮罩层上的“完成”
        for attempt in range(15):
            # 检查是否有弹窗
            has_modal = page.evaluate('''() => {
                const portals = document.querySelectorAll('.semi-portal, .semi-modal-wrap');
                for (const el of portals) {
                    if (el.offsetParent !== null || el.style.display !== 'none') return true;
                }
                return false;
            }''')
            if not has_modal:
                print("[抖音] 弹窗已关闭")
                break
            
            if attempt < 5:
                # 尝试点击“完成”按钮
                page.evaluate('''() => {
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.textContent.includes('完成') || btn.textContent.includes('确认')) {
                            btn.click();
                            return true;
                        }
                    }
                    // 没找到按钮，直接移除弹窗
                    document.querySelectorAll('.semi-portal').forEach(el => el.remove());
                    return false;
                }''')
            else:
                # 强制移除所有弹窗 DOM
                page.evaluate('''() => {
                    document.querySelectorAll('.semi-portal, .semi-modal-wrap').forEach(el => el.remove());
                    document.querySelectorAll('[role="modal"]').forEach(el => el.remove());
                    document.querySelectorAll('.ReactCrop').forEach(el => el.remove());
                }''')
            time.sleep(2)
        time.sleep(2)
        
        # Step 5: Fill title
        print("[抖音] 填写标题...")
        title_input = page.locator('input[placeholder*="标题"]').first
        title_input.click(force=True)
        title_input.fill('')
        page.keyboard.type(title, delay=50)
        time.sleep(1)
        print("[抖音] 标题: %s" % title_input.input_value())
        
        # Step 6: Fill description (optional)
        if description:
            print("[抖音] 填写描述...")
            desc = page.locator('[contenteditable="true"]').first
            desc.click()
            page.keyboard.type(description, delay=50)
            time.sleep(1)
        
        # Step 7: Click publish
        print("[抖音] 点击发布...")
        publish_btn = page.locator('button:has-text("发布")').last
        publish_btn.click(force=True, timeout=10000)
        
        # Step 8: Handle confirm dialog
        time.sleep(5)
        body = page.inner_text('body')
        if '确认要发布' in body or '是否确认' in body:
            print("[抖音] 确认弹窗出现")
            confirm_btn = page.locator('button:has-text("确认")')
            if confirm_btn.count() > 0:
                confirm_btn.first.click(force=True, timeout=5000)
                print("[抖音] 已确认发布")
        
        # Step 9: Wait for redirect to manage page
        print("[抖音] 等待发布结果...")
        for i in range(30):
            time.sleep(3)
            url = page.url
            if 'manage' in url:
                print("[抖音] 已跳转到管理页")
                break
        else:
            return {'success': False, 'message': '发布超时, URL: %s' % page.url}
        
        # Step 10: Verify work count
        time.sleep(5)
        body_text = page.inner_text('body')
        match = re.search(r'共\s*(\d+)\s*个作品', body_text)
        if match:
            count = int(match.group(1))
            print("[抖音] 共 %d 个作品" % count)
            return {'success': True, 'message': '发布成功，共%d个作品' % count}
        else:
            return {'success': True, 'message': '已跳转管理页，但无法确认作品数'}
    
    except Exception as e:
        return {'success': False, 'message': '发布出错: %s' % str(e)}
