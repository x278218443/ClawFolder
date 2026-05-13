"""
TTS 配音模块 - 使用 MiMo TTS 生成旁白音频
"""
import os
import json
import requests
from datetime import datetime

# MiMo TTS API
TTS_API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"


def get_tts_config():
    """获取 TTS 配置"""
    from config.settings import MIMO_API_KEY
    return {
        "api_key": MIMO_API_KEY,
        "base_url": TTS_API_BASE,
        "model": "mimo-v2.5-tts",
        "voice": "default_zh",
    }


def generate_tts(text: str, output_path: str, voice: str = None) -> str:
    """生成语音文件
    Args:
        text: 要转换的文字
        output_path: 输出音频路径
        voice: 音色名称
    Returns:
        音频文件路径，失败返回 None
    """
    config = get_tts_config()
    if voice:
        config["voice"] = voice

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "input": text,
        "voice": config["voice"],
        "response_format": "mp3",
        "speed": 1.1,  # 稍快语速，适合短视频
    }

    try:
        resp = requests.post(
            f"{config['base_url']}/audio/speech",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        file_size = os.path.getsize(output_path)
        print(f"[TTS] 生成完成: {output_path} ({file_size/1024:.1f}KB)")
        return output_path

    except Exception as e:
        print(f"[TTS] 生成失败: {e}")
        return None


def generate_scene_audio(script: dict, output_dir: str = ".") -> list[dict]:
    """为脚本的每个场景生成单独的音频文件
    返回: [{"scene_id": 1, "audio_path": "xxx.mp3", "duration": 5.2}, ...]
    """
    scenes = script.get("scenes", [])
    audio_files = []

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        if not narration:
            print(f"[TTS] 跳过场景 {i+1}: 无旁白")
            continue

        output_path = os.path.join(output_dir, f"audio_{i:02d}.mp3")
        result = generate_tts(narration, output_path)

        if result:
            # 获取音频时长
            duration = get_audio_duration(result)
            audio_files.append({
                "scene_id": scene.get("scene_id", i + 1),
                "audio_path": result,
                "duration": duration,
                "narration": narration,
            })

    print(f"[TTS] 总共生成 {len(audio_files)}/{len(scenes)} 段音频")
    return audio_files


def generate_full_audio(script: dict, output_path: str) -> str:
    """生成完整旁白音频（所有场景合并）
    返回: 音频文件路径
    """
    full_narration = script.get("narration", "")
    if not full_narration:
        # 拼接所有场景的旁白
        scenes = script.get("scenes", [])
        full_narration = " ".join(s.get("narration", "") for s in scenes)

    if not full_narration:
        print("[TTS] 无旁白内容")
        return None

    return generate_tts(full_narration, output_path)


def get_audio_duration(filepath: str) -> float:
    """获取音频时长(秒) - 使用 ffprobe"""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 5.0  # 默认5秒


if __name__ == "__main__":
    # 测试
    test_text = "大家好，今天给大家分享一个震撼的消息。胖东来正式起诉了博主惊梦人，这件事在网上引发了巨大争议。"
    result = generate_tts(test_text, "/tmp/test_tts.mp3")
    if result:
        print(f"测试成功: {result}")
    else:
        print("测试失败，请检查 API 配置")
