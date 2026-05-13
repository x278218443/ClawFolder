"""
AI 短视频流水线 - 内容采集模块
AI 早报风格：从多个 AI 科技媒体 RSS/API 抓取当日热点新闻
"""
import requests
import json
import re
from datetime import datetime, timedelta


# ============================================================
# 数据源配置
# ============================================================

AI_KEYWORDS = [
    # === 大模型名称（核心） ===
    "大模型", "LLM", "大语言模型", "多模态", "全模态",
    "GPT", "ChatGPT", "OpenAI", "Claude", "Anthropic",
    "DeepSeek", "豆包", "Doubao", "文心", "通义", "智谱",
    "ChatGLM", "Kimi", "月之暗面", "百川", "混元", "MiniMax",
    "Gemini", "Llama", "Qwen", "Mistral", "Yi", "零一",
    "Sora", "Midjourney", "Stable Diffusion", "DALL-E",
    "Copilot", "Cursor", "Claude Code", "Devin",
    # === 模型能力/训练/推理 ===
    "幻觉", "对齐", "alignment", "微调", "fine-tune", "RLHF",
    "推理模型", "reasoning", "思维链", "Chain of Thought",
    "token", "上下文窗口", "context window",
    "多模态理解", "视觉语言模型",
    "语音模型", "TTS", "ASR", "语音合成", "语音识别",
    "文生图", "图生图", "文生视频", "图生视频",
    "AI视频生成", "AI绘画", "AI编程", "AI写作", "AI搜索",
    "AIGC", "AGI", "transformer", "扩散模型",
    # === AI 产品/商业化 ===
    "AI订阅", "AI付费", "API调用", "AI安全", "越狱", "jailbreak",
    "提示注入", "prompt injection", "AI伦理", "AI监管",
    # === 开源模型 ===
    "开源模型", "开源大模型", "模型发布", "模型升级", "模型更新",
]

# 排除关键词（命中则直接跳过）
EXCLUDE_KEYWORDS = [
    "游戏本", "游戏手机", "显卡", "RTX", "锐龙", "Radeon",
    "短剧", "外卖", "电商", "直播带货",
    "iPhone", "iPad", "MacBook", "安卓", "鸿蒙",
    "一加", "realme", "华硕天选", "刺客信条", "Xbox", "PlayStation",
    "市值", "股价", "盘前", "暴涨", "财报", "营收", "净利润",
    "机器人", "具身智能", "自动驾驶", "智能驾驶", "无人车",
    "硬件", "可穿戴", "手环", "手表", "耳机",
    # 观点/评价/推荐（非事件）— 注意：只在标题中检查，不用 summary
    "安利", "在线安利", "评测", "感悟", "心得",
    "认为", "发声",
    # 传统行业应用
    "养殖", "农业", "养猪", "种植", "制造业",
    # 非模型公司动态
    "商汤", "卓驭", "爱彼迎", "Airbnb",
    "物理AI", "转型", "生存法则",
]

# 进展信号词（标题中必须至少命中一个，才算"AI 模型进步"）
PROGRESS_SIGNALS = [
    "发布", "推出", "上线", "升级", "更新", "开源", "开放",
    "突破", "超越", "刷新", "首次", "首个", "首发",
    "融资", "收购", "合并", "投资",
    "漏洞", "泄露", "攻击", "越狱", "破解", "攻破",
    "暂停", "关闭", "停止", "下架",
    "涨价", "降价", "调价", "订阅", "付费", "免费",
    "造出", "打造", "发布新", "新版", "新款",
]

RSS_SOURCES = [
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "encoding": "utf-8",
    },
    {
        "name": "IT之家",
        "url": "https://www.ithome.com/rss/",
        "encoding": "utf-8",
    },
    {
        "name": "少数派",
        "url": "https://sspai.com/feed",
        "encoding": "utf-8",
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/rss",
        "encoding": "utf-8",
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/feed",
        "encoding": "utf-8",
    },
]


# ============================================================
# RSS 解析
# ============================================================

def _parse_rss_items(xml_content: str, source_name: str) -> list[dict]:
    """解析 RSS XML 中的 <item> 条目"""
    items = []
    blocks = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)

    for block in blocks:
        # 提取标题
        title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', block)
        if not title_m:
            title_m = re.search(r'<title>(.*?)</title>', block)
        title = title_m.group(1).strip() if title_m else ""

        # 提取链接
        link_m = re.search(r'<link>(.*?)</link>', block)
        if not link_m:
            link_m = re.search(r'<link[^>]*href="([^"]*)"', block)
        link = link_m.group(1).strip() if link_m else ""

        # 提取描述
        desc_m = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', block, re.DOTALL)
        if not desc_m:
            desc_m = re.search(r'<description>(.*?)</description>', block, re.DOTALL)
        description = desc_m.group(1).strip() if desc_m else ""
        # 清理 HTML 标签
        description = re.sub(r'<[^>]+>', '', description).strip()[:300]

        # 提取发布日期
        pubdate_m = re.search(r'<pubDate>(.*?)</pubDate>', block)
        pub_date = pubdate_m.group(1).strip() if pubdate_m else ""

        if title and len(title) > 4:
            items.append({
                "title": title,
                "summary": description,
                "url": link,
                "source": source_name,
                "pub_date": pub_date,
                "topic": "AI科技",
            })

    return items


def _is_today_or_recent(pub_date: str, days: int = 2) -> bool:
    """判断日期是否在最近 N 天内"""
    if not pub_date:
        return True  # 没日期的保留

    now = datetime.now()

    # 尝试解析 RSS 标准日期格式
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",      # Tue, 05 May 2026 12:00:00 +0800
        "%a, %d %b %Y %H:%M:%S GMT",      # Tue, 05 May 2026 12:00:00 GMT
        "%Y-%m-%d %H:%M:%S",               # 2026-05-05 12:00:00
        "%Y-%m-%dT%H:%M:%S",               # 2026-05-05T12:00:00
        "%Y-%m-%dT%H:%M:%SZ",              # 2026-05-05T12:00:00Z
    ]:
        try:
            dt = datetime.strptime(pub_date.strip(), fmt)
            # 转为 naive datetime 比较
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt >= now - timedelta(days=days)
        except ValueError:
            continue

    return True  # 解析失败的保留


def _is_ai_related(title: str, summary: str = "") -> bool:
    """判断新闻是否 AI/大模型相关（严格模式：AI关键词 + 进展信号）"""
    text = (title + " " + summary).lower()
    title_lower = title.lower()

    # 1. 先排除非 AI 新闻（只检查标题，避免 summary 中的无关词误伤）
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in title_lower:
            return False

    # 2. 必须命中 AI 关键词
    has_ai = False
    for kw in AI_KEYWORDS:
        if kw.lower() in text:
            has_ai = True
            break
    if not has_ai:
        return False

    # 3. 标题中必须有进展信号词（确保是实际事件，不是观点/评论）
    for kw in PROGRESS_SIGNALS:
        if kw.lower() in title_lower:
            return True

    # 4. 如果标题没有信号词但摘要中有具体事件，也保留
    for kw in PROGRESS_SIGNALS:
        if kw.lower() in summary.lower():
            return True

    return False


# ============================================================
# 各数据源采集
# ============================================================

def fetch_from_rss(source: dict, max_items: int = 30) -> list[dict]:
    """从 RSS 源抓取新闻"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml",
        }
        resp = requests.get(source["url"], headers=headers, timeout=15)
        resp.encoding = source.get("encoding", "utf-8")

        items = _parse_rss_items(resp.text, source["name"])
        print(f"[采集] {source['name']}: {len(items)} 条 (原始)")
        return items[:max_items]

    except Exception as e:
        print(f"[采集] {source['name']} 失败: {e}")
        return []


def fetch_weibo_hot() -> list[dict]:
    """获取微博热搜 Top 10"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        results = []
        for item in data.get("data", {}).get("realtime", [])[:10]:
            results.append({
                "title": item.get("word", ""),
                "summary": item.get("label_name", ""),
                "url": f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                "source": "微博热搜",
                "topic": "热搜",
                "hot": item.get("num", 0),
            })
        return results
    except Exception as e:
        print(f"[采集] 微博热搜获取失败: {e}")
        return []


# ============================================================
# 主入口
# ============================================================

def fetch_news(topics: list[str] = None, count_per_topic: int = 5) -> list[dict]:
    """
    主采集入口

    策略：
    1. 从多个 RSS 源抓取科技新闻
    2. 优先保留 AI 相关内容
    3. 按日期排序，优先当日新闻
    4. 兜底保留非 AI 新闻以凑够数量

    返回去重后的新闻列表
    """
    all_news = []

    # 1. 从 RSS 源采集
    for source in RSS_SOURCES:
        items = fetch_from_rss(source)
        all_news.extend(items)

    # 2. 尝试微博
    weibo = fetch_weibo_hot()
    if weibo:
        all_news.extend(weibo)
        print(f"[采集] 微博热搜: {len(weibo)} 条")

    # 3. 去重
    seen = set()
    unique = []
    for item in all_news:
        key = item["title"][:20]
        if key not in seen and item["title"]:
            seen.add(key)
            unique.append(item)

    # 4. 过滤：只保留 AI/大模型相关 + 最近 2 天
    ai_news = []

    for item in unique:
        if not _is_today_or_recent(item.get("pub_date", "")):
            continue
        if _is_ai_related(item["title"], item.get("summary", "")):
            item["topic"] = "AI大模型"
            ai_news.append(item)

    print(f"[采集] AI/大模型相关: {len(ai_news)} 条")

    # 5. 只返回 AI 相关新闻，不兜底补其他新闻
    return ai_news


if __name__ == "__main__":
    news = fetch_news()
    print(f"\n{'='*50}")
    print(f"AI 相关新闻：")
    print(f"{'='*50}")
    for i, n in enumerate(news[:15]):
        ai_tag = "🤖" if _is_ai_related(n["title"], n.get("summary", "")) else "📰"
        print(f"\n{ai_tag} {i+1}. [{n['source']}] {n['title']}")
        if n.get("summary"):
            print(f"    {n['summary'][:80]}")
