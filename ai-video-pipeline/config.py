"""
AI 短视频流水线 - 配置文件
橘鸦Juya AI 早报风格：16:9 横屏，多话题新闻
"""
import os
import json

# === 自动从 OpenClaw 配置读取 API Key ===
def _load_mimo_key():
    """从环境变量或 OpenClaw 配置中读取 MiMo API Key（xiaomicoding provider）"""
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

# === API 配置 ===
MIMO_API_KEY = _load_mimo_key()

# LLM 配置（用于脚本生成 - OpenAI 兼容接口）
# 默认使用 xiaomicoding 的 mimo-v2.5-pro 模型
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://token-plan-cn.xiaomimimo.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", MIMO_API_KEY)
LLM_MODEL = os.environ.get("LLM_MODEL", "mimo-v2.5-pro")

# === 视频配置 ===
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080  # 横屏 16:9
VIDEO_FPS = 30
VIDEO_BG_COLOR = "#0a0a0a"  # 深色背景

# 字幕样式
SUBTITLE_FONT = "Noto Sans CJK SC"
SUBTITLE_FONTSIZE = 48
SUBTITLE_COLOR = "#FFFFFF"
SUBTITLE_OUTLINE_COLOR = "#000000"
SUBTITLE_OUTLINE_WIDTH = 3
SUBTITLE_POSITION_Y = 900  # 字幕 Y 坐标（从顶部算，底部区域）

# === 内容配置 ===
# 默认话题关键词（可通过参数覆盖）
DEFAULT_TOPICS = ["AI人工智能", "科技前沿", "数码产品"]
NEWS_COUNT_PER_TOPIC = 5  # 每个话题取几条
SCRIPT_MAX_CHARS = 900  # 多话题旁白最大字数（约 2-3 分钟）

# === 输出路径 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
