"""
热点发现模块 - 从多个平台抓取热搜/热榜
数据源: 今日热榜 (tophub.today)
"""
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# 热榜源配置
HOT_SOURCES = [
    {
        "name": "微博热搜",
        "url": "https://tophub.today/n/KqndgxeLl9",
        "platform": "weibo",
        "weight": 1.0,  # 热度权重
    },
    {
        "name": "知乎热榜",
        "url": "https://tophub.today/n/mproPpoq6O",
        "platform": "zhihu",
        "weight": 0.9,
    },
    {
        "name": "B站热榜",
        "url": "https://tophub.today/n/74KvxwokxM",
        "platform": "bilibili",
        "weight": 1.2,  # B站内容更匹配
    },
    {
        "name": "抖音热榜",
        "url": "https://tophub.today/n/DpQvNABoNE",
        "platform": "douyin",
        "weight": 0.8,
    },
    {
        "name": "头条热榜",
        "url": "https://tophub.today/n/x9ozB4KoXb",
        "platform": "toutiao",
        "weight": 0.7,
    },
]


def parse_tophub(html: str) -> list[dict]:
    """解析今日热榜页面，提取标题和热度"""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # 今日热榜的结构: table tbody tr
    rows = soup.select("table tbody tr")

    for row in rows:
        try:
            # 第一个 <a> 标签是标题
            links = row.find_all("a")
            if not links:
                continue

            # 取第一个有效链接
            link = None
            for a in links:
                text = a.get_text(strip=True)
                if text and len(text) >= 4 and text not in ("", "更多"):
                    link = a
                    break

            if not link:
                continue

            title = link.get_text(strip=True)

            # 提取热度值 (格式: "151万", "1.2亿" 等)
            row_text = row.get_text()
            hot_value = 0

            # 匹配 "数字+万" 或 "数字+亿"
            hot_match = re.search(r"(\d+\.?\d*)(万|亿)", row_text)
            if hot_match:
                val = float(hot_match.group(1))
                unit = hot_match.group(2)
                if unit == "亿":
                    hot_value = val * 10000
                else:
                    hot_value = val

            items.append({
                "title": title,
                "hot_value": hot_value,
                "url": link.get("href", ""),
            })
        except Exception:
            continue

    return items


def fetch_source(source: dict) -> list[dict]:
    """抓取单个热榜源"""
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = parse_tophub(resp.text)

        # 添加来源信息
        for item in items:
            item["platform"] = source["platform"]
            item["weight"] = source["weight"]
            item["weighted_score"] = item.get("hot_value", 0) * source["weight"]

        return items[:30]  # 每个源取前30
    except Exception as e:
        print(f"[热点] 抓取失败 {source['name']}: {e}")
        return []


def fetch_all_hot_topics() -> list[dict]:
    """抓取所有平台热榜，去重并按综合热度排序"""
    all_items = []

    for source in HOT_SOURCES:
        items = fetch_source(source)
        all_items.extend(items)
        print(f"[热点] {source['name']}: 抓到 {len(items)} 条")

    # 去重 (相似标题合并)
    seen_titles = set()
    unique_items = []
    for item in all_items:
        # 简单去重: 标题前10个字
        key = item["title"][:10]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_items.append(item)

    # 按加权热度排序
    unique_items.sort(key=lambda x: x.get("weighted_score", 0), reverse=True)

    print(f"[热点] 总计: {len(unique_items)} 条去重后热点")
    return unique_items


def filter_for_video(topics: list[dict], max_count: int = 5) -> list[dict]:
    """筛选适合做短视频的热点
    标准:
    - 有故事性/争议性/趣味性
    - 不是纯文字梗（需要有画面感）
    - 时效性够强
    """
    # 排除的关键词 (不适合做视频)
    exclude_keywords = [
        "如何看待", "怎样评价", "什么感受", "你认为",
        "怎么理解", "有哪些", "怎么办",
    ]

    filtered = []
    for topic in topics:
        title = topic["title"]
        # 排除问答类
        if any(kw in title for kw in exclude_keywords):
            continue
        # 排除太短的标题
        if len(title) < 6:
            continue
        filtered.append(topic)
        if len(filtered) >= max_count:
            break

    return filtered


def save_hot_topics(topics: list[dict], output_dir: str = "."):
    """保存热点到文件"""
    filepath = f"{output_dir}/hot_topics_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print(f"[热点] 保存到 {filepath}")
    return filepath


if __name__ == "__main__":
    # 测试: 抓取热点
    topics = fetch_all_hot_topics()
    filtered = filter_for_video(topics, max_count=10)
    print("\n=== 适合做视频的热点 ===")
    for i, t in enumerate(filtered, 1):
        print(f"{i}. [{t['platform']}] {t['title']} (热度: {t.get('hot_value', 0)})")
