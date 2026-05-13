"""
AI 短视频流水线 - TTS 语音合成模块
支持 MiMo v2.5 TTS（小米 Token Plan）和 edge-tts（免费降级方案）
"""
import os
import json
import asyncio
import base64
import subprocess
import requests


# === MiMo TTS 音色表 ===
MIMO_VOICES = {
    "冰糖": "冰糖",   # 中文女声，明亮活泼
    "茉莉": "茉莉",   # 中文女声，温柔
    "苏打": "苏打",   # 中文男声
    "白桦": "白桦",   # 中文男声，沉稳
    "Mia": "Mia",     # 英文女声
    "Chloe": "Chloe", # 英文女声
    "Milo": "Milo",   # 英文男声
    "Dean": "Dean",   # 英文男声
}

# === edge-tts 音色表 ===
EDGE_TTS_VOICES = {
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunjian": "zh-CN-YunjianNeural",
}


def _load_mimo_key():
    """从 OpenClaw 配置读取 MiMo API Key"""
    key = os.environ.get("MIMO_API_KEY", "")
    if key:
        return key
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_path) as f:
            cfg = json.load(f)
        providers = cfg.get("models", {}).get("providers", {})
        xiaomicoding = providers.get("xiaomicoding", {})
        return xiaomicoding.get("apiKey", "")
    except Exception:
        return ""


MIMO_API_KEY = _load_mimo_key()
MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MIMO_MODEL = "mimo-v2.5-tts"


def synthesize_speech(
    text: str,
    output_path: str,
    voice_id: str = None,
    speed: float = 1.1,
    engine: str = "mimo",
    style: str = "",
) -> dict:
    """
    将文本转为语音文件

    参数:
        text: 旁白文本
        output_path: 输出音频路径
        voice_id: 音色名称（mimo: 冰糖/茉莉/苏打/白桦, edge-tts: xiaoyi 等）
        speed: 语速倍率
        engine: "mimo" 或 "edge-tts"
        style: MiMo 风格指令（自然语言，如"明亮活泼的播报语气"）

    返回: {"duration_sec": float, "output": str, "format": str, "engine": str}
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if engine == "mimo":
        if not MIMO_API_KEY:
            print("[TTS] MiMo API Key 未配置，降级到 edge-tts")
            engine = "edge-tts"

    if engine == "mimo":
        result = _mimo_tts(text, output_path, voice_id or "冰糖", speed, style)
    else:
        result = _edge_tts(text, output_path, voice_id or "zh-CN-XiaoyiNeural", speed)

    result["engine"] = engine
    print(f"[TTS] 生成完成: {output_path} ({result['duration_sec']:.1f}s) [engine={engine}]")
    return result


def _mimo_tts(text: str, output_path: str, voice: str, speed: float, style: str) -> dict:
    """使用 MiMo v2.5 TTS（小米 Token Plan）"""
    messages = []

    # 用户消息：风格指令（可选）
    if style:
        messages.append({"role": "user", "content": style})
    else:
        # 默认播报风格
        rate_desc = "语速稍快" if speed > 1.0 else ("语速偏慢" if speed < 1.0 else "正常语速")
        messages.append({
            "role": "user",
            "content": f"明亮清晰的播报语气，{rate_desc}，适合短视频资讯"
        })

    # 助手消息：要合成的文本
    messages.append({"role": "assistant", "content": text})

    payload = {
        "model": MIMO_MODEL,
        "messages": messages,
        "audio": {
            "format": "mp3",
            "voice": voice,
        },
        "stream": False,
    }

    resp = requests.post(
        f"{MIMO_BASE_URL}/chat/completions",
        headers={
            "api-key": MIMO_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    # 提取音频数据
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"MiMo TTS 无返回: {json.dumps(data, ensure_ascii=False)[:300]}")

    msg = choices[0].get("message", {})
    audio_info = msg.get("audio", {})
    audio_b64 = audio_info.get("data", "")

    if not audio_b64:
        raise RuntimeError(f"MiMo TTS 无音频数据: {json.dumps(msg, ensure_ascii=False)[:300]}")

    audio_bytes = base64.b64decode(audio_b64)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    duration = _get_audio_duration(output_path)
    return {"output": output_path, "format": "mp3", "duration_sec": duration}


def _edge_tts(text: str, output_path: str, voice: str, speed: float) -> dict:
    """使用 edge-tts（免费降级方案）"""
    rate_pct = int((speed - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

    async def _generate():
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        await communicate.save(output_path)

    asyncio.run(_generate())

    duration = _get_audio_duration(output_path)
    return {"output": output_path, "format": "mp3", "duration_sec": duration}


def list_voices(engine: str = "mimo") -> list:
    """列出可用音色"""
    if engine == "mimo":
        return [{"id": v, "name": k} for k, v in MIMO_VOICES.items()]
    elif engine == "edge-tts":
        return [{"id": v, "name": k} for k, v in EDGE_TTS_VOICES.items()]
    return []


def _get_audio_duration(path: str) -> float:
    """用 ffprobe 获取音频时长"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


if __name__ == "__main__":
    test_text = "大家好，今天我们来聊聊最新的AI热点。豆包突然要收费了，这背后到底是什么原因？"
    result = synthesize_speech(test_text, "output/test_mimo_full.mp3", voice_id="冰糖")
    print(json.dumps(result, ensure_ascii=False, indent=2))
