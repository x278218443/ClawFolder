"""
即梦视频生成模块 - 调用火山引擎即梦 API 生成视频片段
支持: 文生图、图生视频、文生视频
"""
import os
import json
import time
import base64
import hashlib
import hmac
import requests
from datetime import datetime


class JimengClient:
    """即梦 API 客户端 (火山引擎)"""

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = "https://visual.volcengineapi.com"
        self.service = "cv"

    def _sign(self, method, path, body="", timestamp=None):
        """火山引擎 API 签名"""
        if timestamp is None:
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        # 简化签名 (实际使用需要完整的火山引擎签名 V4)
        string_to_sign = f"{method}\n{path}\n{body}"
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode(),
                string_to_sign.encode(),
                hashlib.sha256
            ).digest()
        ).decode()

        return {
            "Authorization": f"HMAC-SHA256 Credential={self.access_key}, Signature={signature}",
            "X-Date": timestamp,
            "Content-Type": "application/json",
        }

    def text_to_image(self, prompt: str, width=1080, height=1920, num_images=1) -> list[str]:
        """文生图 - 生成关键帧图片
        返回: 图片路径列表
        """
        payload = {
            "req_key": "jimeng_high_aes",
            "prompt": prompt,
            "width": width,
            "height": height,
            "num": num_images,
            "scale": 3.5,  # 引导系数
            "seed": -1,    # 随机种子
        }

        try:
            headers = self._sign("POST", "/api/v1/jimeng/text2image")
            resp = requests.post(
                f"{self.endpoint}/api/v1/jimeng/text2image",
                headers=headers,
                json=payload,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()

            images = []
            for img_data in data.get("data", {}).get("binary_data_base64", []):
                img_bytes = base64.b64decode(img_data)
                filepath = f"/tmp/jimeng_img_{int(time.time()*1000)}.png"
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                images.append(filepath)

            return images

        except Exception as e:
            print(f"[即梦] 文生图失败: {e}")
            return []

    def image_to_video(self, image_path: str, prompt: str, duration=5) -> str:
        """图生视频 - 让图片动起来
        返回: 视频路径
        """
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()

        payload = {
            "req_key": "jimeng_video_generation",
            "prompt": prompt,
            "image_url": f"data:image/png;base64,{img_base64}",
            "duration": duration,
            "width": 1080,
            "height": 1920,
        }

        try:
            headers = self._sign("POST", "/api/v1/jimeng/image2video")
            resp = requests.post(
                f"{self.endpoint}/api/v1/jimeng/image2video",
                headers=headers,
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()

            video_data = data.get("data", {}).get("binary_data_base64", "")
            if video_data:
                video_bytes = base64.b64decode(video_data)
                filepath = f"/tmp/jimeng_vid_{int(time.time()*1000)}.mp4"
                with open(filepath, "wb") as f:
                    f.write(video_bytes)
                return filepath

            return None

        except Exception as e:
            print(f"[即梦] 图生视频失败: {e}")
            return None

    def text_to_video(self, prompt: str, width=1080, height=1920, duration=5) -> str:
        """文生视频 - 直接从文字生成视频
        返回: 视频路径
        """
        payload = {
            "req_key": "jimeng_video_generation",
            "prompt": prompt,
            "duration": duration,
            "width": width,
            "height": height,
        }

        try:
            headers = self._sign("POST", "/api/v1/jimeng/text2video")
            resp = requests.post(
                f"{self.endpoint}/api/v1/jimeng/text2video",
                headers=headers,
                json=payload,
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()

            video_data = data.get("data", {}).get("binary_data_base64", "")
            if video_data:
                video_bytes = base64.b64decode(video_data)
                filepath = f"/tmp/jimeng_vid_{int(time.time()*1000)}.mp4"
                with open(filepath, "wb") as f:
                    f.write(video_bytes)
                return filepath

            return None

        except Exception as e:
            print(f"[即梦] 文生视频失败: {e}")
            return None


def generate_clips_for_script(script: dict, client: JimengClient, output_dir: str = ".") -> list[str]:
    """根据脚本的每个场景生成视频片段
    流程: 文生图 → 图生视频 (效果更好)
    """
    clips = []
    scenes = script.get("scenes", [])

    for i, scene in enumerate(scenes):
        print(f"[即梦] 正在生成第 {i+1}/{len(scenes)} 个场景...")

        prompt = scene.get("jimeng_prompt", scene.get("visual_desc", ""))
        duration = scene.get("duration", 5)

        if not prompt:
            print(f"[即梦] 跳过场景 {i+1}: 无提示词")
            continue

        # 方案1: 文生图 + 图生视频 (质量更高)
        images = client.text_to_image(prompt, width=1080, height=1920, num_images=1)
        if images:
            clip_path = client.image_to_video(images[0], prompt, duration=duration)
            if clip_path:
                # 移动到输出目录
                final_path = os.path.join(output_dir, f"clip_{i:02d}.mp4")
                os.rename(clip_path, final_path)
                clips.append(final_path)
                print(f"[即梦] 场景 {i+1} 完成: {final_path}")
                continue

        # 方案2: 文生视频 (备选)
        clip_path = client.text_to_video(prompt, duration=duration)
        if clip_path:
            final_path = os.path.join(output_dir, f"clip_{i:02d}.mp4")
            os.rename(clip_path, final_path)
            clips.append(final_path)
            print(f"[即梦] 场景 {i+1} 完成(文生视频): {final_path}")
        else:
            print(f"[即梦] 场景 {i+1} 失败，跳过")

        # 控制调用频率
        time.sleep(2)

    print(f"[即梦] 总共生成 {len(clips)}/{len(scenes)} 个片段")
    return clips


# ====== 即梦 API 备选方案: 使用 HTTP API 通用调用 ======

def call_jimeng_api(action: str, params: dict, access_key: str, secret_key: str) -> dict:
    """通用即梦 API 调用 (适配不同版本的 API)"""
    endpoint = "https://visual.volcengineapi.com"
    url = f"{endpoint}/api/v1/jimeng/{action}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_key}",
    }

    try:
        resp = requests.post(url, headers=headers, json=params, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[即梦API] 调用 {action} 失败: {e}")
        return None


if __name__ == "__main__":
    # 测试 (需要配置 API Key)
    from config.settings import JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY

    if JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY:
        client = JimengClient(JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY)
        images = client.text_to_image("一个年轻人在电脑前编程，电影质感，暖色调", num_images=1)
        print(f"生成图片: {images}")
    else:
        print("请先配置即梦 API Key (JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY)")
