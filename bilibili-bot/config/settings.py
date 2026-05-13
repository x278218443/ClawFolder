"""
全自动 B站短视频流水线 - 配置文件
"""
import os
import json

CONFIG_PATH = os.path.expanduser("~/.openclaw/workspace/bilibili-bot/config/api_keys.json")

def load_config():
    """加载 API 配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

# ====== API 配置 ======
CONFIG = load_config()

# MiMo 模型 (用于脚本生成)
MIMO_API_KEY = CONFIG.get("mimo_api_key", os.environ.get("MIMO_API_KEY", ""))
MIMO_BASE_URL = CONFIG.get("mimo_base_url", "https://token-plan-cn.xiaomimimo.com/v1")
MIMO_MODEL = CONFIG.get("mimo_model", "mimo-v2.5-pro")

# 即梦 API (火山引擎)
JIMENG_ACCESS_KEY = CONFIG.get("jimeng_access_key", os.environ.get("JIMENG_AK", ""))
JIMENG_SECRET_KEY = CONFIG.get("jimeng_secret_key", os.environ.get("JIMENG_SK", ""))
JIMENG_API_ENDPOINT = "https://visual.volcengineapi.com"

# B站账号
BILI_SESSDATA = CONFIG.get("bili_sessdata", "")
BILI_JCT = CONFIG.get("bili_jct", "")
BILI_BUVID = CONFIG.get("bili_buvid", "")

# ====== 流水线配置 ======
# 热点抓取
HOT_SOURCES = [
    {"name": "微博热搜", "url": "https://tophub.today/n/KqndgxeLl9", "type": "weibo"},
    {"name": "知乎热榜", "url": "https://tophub.today/n/mproPpoq6O", "type": "zhihu"},
    {"name": "B站热榜", "url": "https://tophub.today/n/74KvxwokxM", "type": "bilibili"},
    {"name": "抖音热榜", "url": "https://tophub.today/n/DpQvNABoNE", "type": "douyin"},
    {"name": "头条热榜", "url": "https://tophub.today/n/x9ozB4KoXb", "type": "toutiao"},
]

# 内容领域筛选 (留空=不过滤)
CONTENT_CATEGORIES = ["科技", "社会", "娱乐", "生活", "游戏"]

# 视频参数
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 竖屏
VIDEO_FPS = 30
VIDEO_DURATION = 60  # 目标时长(秒)
CLIP_DURATION = 5    # 每个片段时长(秒)

# 配音参数
TTS_API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
TTS_VOICE = "default_zh"  # MiMo TTS 音色

# 发布参数
PUBLISH_TIMES = ["11:30", "19:30"]  # 每天发布时段
MAX_VIDEOS_PER_DAY = 2

# 输出路径
OUTPUT_DIR = os.path.expanduser("~/.openclaw/workspace/bilibili-bot/output")
SCRIPTS_DIR = os.path.join(OUTPUT_DIR, "scripts")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
CLIPS_DIR = os.path.join(OUTPUT_DIR, "clips")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")
LOGS_DIR = os.path.expanduser("~/.openclaw/workspace/bilibili-bot/logs")
