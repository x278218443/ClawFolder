#!/usr/bin/env python3
"""
AI 早报新闻抓取器 v3

v3 变更：
- 新增 IT之家 AI 源（覆盖 OpenAI/Codex/国内大模型等热点）
- AIBase 切换到中文页 /zh/news
- 移除机器之心（SPA 无法抓取）和量子位（403 被封）
- 放宽排除规则：AI 公司融资/投资不再排除
- 新增"公司动态"品类，优先级高于硬件
- 排序调整：大模型/产品发布 > 公司动态 > 工具 > 硬件
"""
import sys
import os
import json
import re
import requests
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

CST = timezone(timedelta(hours=8))
TODAY = datetime.now(CST).strftime("%Y-%m-%d")

# ──────────────────────────────────────────────
# 新闻源配置
# ──────────────────────────────────────────────

SOURCES = [
    {
        "name": "AIBase",
        "url": "https://www.aibase.com/zh/news",
        "parser": "aibase_zh",
        "priority": 1,
    },
    {
        "name": "IT之家 AI",
        "url": "https://www.ithome.com/tag/AI",
        "parser": "ithome",
        "priority": 1,
    },
    {
        "name": "36kr AI",
        "url": "https://36kr.com/information/AI/",
        "parser": "36kr",
        "priority": 2,
    },
]

# ──────────────────────────────────────────────
# 品类关键词（命中任一即归类）
# ──────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "model_release": {
        "label": "🟢 模型/产品发布",
        "priority": 100,
        "keywords": [
            "发布", "推出", "上线", "开放", "release", "launch", "announce",
            "开源", "open.source", "发布新版本", "更新", "升级", "新版",
            "模型", "model", "LLM", "GPT", "Claude", "Gemini", "DeepSeek",
            "GLM", "Qwen", "通义", "文心", "混元", "豆包", "千问",
            "Turbo", "Flash", "Pro", "Lite", "Mini", "Max", "Grok",
            "Codex", "Sora", "Llama", "Mistral", "o1", "o3", "o4",
            "消息", "传", "现身", "曝光", "爆料", "泄露", "leak",
            "大模型", "基座", "推理", "多模态", "Agent", "智能体",
        ],
    },
    "company": {
        "label": "🏢 公司动态",
        "priority": 80,
        "keywords": [
            "OpenAI", "Anthropic", "Google", "谷歌", "微软", "Microsoft",
            "Meta", "百度", "阿里", "腾讯", "字节", "华为", "小米",
            "英伟达", "NVIDIA", "AMD", "苹果", "Apple", "三星", "Samsung",
            "融资", "注资", "投资", "估值", "收购", "合并",
            "DeepSeek", "月之暗面", "Moonshot", "智谱", "百川", "MiniMax",
            "零一万物", "阶跃星辰", "科大讯飞", "商汤",
        ],
    },
    "outage": {
        "label": "🔴 事故/宕机",
        "priority": 90,
        "keywords": [
            "中断", "宕机", "故障", "挂了", "异常", "服务中断", "大规模中断",
            "outage", "down", "incident", "downtime", "服务不可用", "API 异常",
            "断线", "无法访问", "错误率飙升", "起诉", "安全", "漏洞",
        ],
    },
    "opensource": {
        "label": "🔵 开源项目",
        "priority": 70,
        "keywords": [
            "开源", "open.source", "GitHub", "github.com", "HuggingFace",
            "huggingface.co", "仓库", "repo", "MIT", "Apache", "许可证",
            "模型权重", "权重发布", "代码开源",
        ],
    },
    "tools": {
        "label": "🟡 工具/基建更新",
        "priority": 60,
        "keywords": [
            "工具", "框架", "SDK", "API", "插件", "扩展", "平台", "基建",
            "Chrome", "VSCode", "Cursor", "Copilot", "MCP",
            "部署", "推理引擎", "推理优化", "量化", "推理框架",
            "WebRTC", "传输", "延迟", "协同", "移动端", "客户端",
            "应用", "APP", "功能", "体验", "升级",
        ],
    },
    "hardware": {
        "label": "📱 硬件/AI设备",
        "priority": 40,
        "keywords": [
            "手机", "硬件", "芯片", "GPU", "TPU", "NPU", "设备", "穿戴",
            "眼镜", "耳机", "机器人", "phone", "hardware", "chip",
            "量产", "联发科", "高通", "NVIDIA", "AMD", "服务器",
        ],
    },
    "cost_analysis": {
        "label": "📊 成本/数据",
        "priority": 50,
        "keywords": [
            "成本", "价格", "定价", "降幅", "涨幅", "增幅", "百分比",
            "cost", "pricing", "用户成本", "Token价格", "性价比",
            "分析", "统计", "数据", "报告", "白皮书", "调用量",
        ],
    },
}

# 排除：纯商业/非AI新闻（裁员、财报、IPO等，但AI公司融资/投资不排除）
EXCLUDE_KEYWORDS = [
    "裁员", "layoff", "上市", "IPO",
    "营收", "财报", "利润", "亏损",
    "股价", "市值", "股东", "分红",
]

# 排除但例外：如果标题同时包含这些AI关键词，则不排除
AI_EXEMPT_KEYWORDS = [
    "AI", "人工智能", "大模型", "GPT", "Claude", "Gemini", "DeepSeek",
    "OpenAI", "Anthropic", "模型", "智能", "Agent", "LLM", "千问", "豆包",
    "通义", "文心", "混元", "Codex", "Sora", "Llama", "Grok",
    "芯片", "GPU", "算力", "推理",
]

# ──────────────────────────────────────────────
# 各源解析器
# ──────────────────────────────────────────────

def parse_aibase_zh(html, today):
    """解析 AIBase 中文页 /zh/news"""
    news = []
    # HTML结构: <span>时间</span><span>.</span><span...>AIbase</span></div><div...><h3...>标题</h3>
    pattern = r'<span>(刚刚|[\d\s]+分钟前|[\d\s]+小时前|昨天)</span><span>\.</span><span[^>]*>AIbase</span></div><div[^>]*><h3[^>]*>(.*?)</h3>'
    for match in re.finditer(pattern, html, re.DOTALL):
        time_str, raw_title = match.groups()
        title = re.sub(r'<[^>]+>', '', raw_title).strip()
        if not title or len(title) < 10:
            continue
        if len(title) > 80:
            title = title[:78] + "…"
        news.append({
            "title": title,
            "url": "https://www.aibase.com/zh/news",
            "source": "AIBase",
            "id": f"aibase_{len(news)}",
        })
    return news


def parse_ithome(html, today):
    """解析 IT之家 AI 标签页"""
    news = []
    # IT之家新闻链接格式：/0/MMDD/ID.htm
    pattern = r'<a[^>]*href=["\']([^"\']*?/0/\d+/\d+\.htm)["\'][^>]*>([^<]{10,100})</a>'
    seen = set()
    for match in re.finditer(pattern, html):
        href, title = match.groups()
        title = title.strip()
        if title in seen or len(title) < 10:
            continue
        # 过滤非新闻链接
        if any(skip in title for skip in ["下载", "描述文件", "壁纸", "报价", "价格"]):
            continue
        seen.add(title)
        url = href if href.startswith("http") else f"https://www.ithome.com{href}"
        # 提取ID
        id_match = re.search(r'/(\d+)\.htm', href)
        news.append({
            "title": title,
            "url": url,
            "source": "IT之家",
            "id": id_match.group(1) if id_match else f"ithome_{len(news)}",
        })
    return news


def parse_36kr(html, today):
    """解析 36kr AI 新闻"""
    news = []
    # 36kr 主标题行带 sensors_operation_list="page_flow" 标记
    pattern = r'<a[^>]*href=["\']([^"\']*?/p/(\d+))["\'][^>]*sensors_operation_list=["\']page_flow["\'][^>]*>(.*?)</a>'
    for match in re.finditer(pattern, html, re.DOTALL):
        href, article_id, raw_title = match.groups()
        title = re.sub(r'<[^>]+>', '', raw_title).strip()
        if not title or len(title) < 8 or len(title) > 80:
            continue
        url = href if href.startswith("http") else f"https://36kr.com{href}"
        news.append({
            "title": title,
            "url": url,
            "source": "36kr",
            "id": article_id,
        })
    return news


PARSERS = {
    "aibase_zh": parse_aibase_zh,
    "ithome": parse_ithome,
    "36kr": parse_36kr,
}


# ──────────────────────────────────────────────
# 新闻抓取
# ──────────────────────────────────────────────

def fetch_source(source_config):
    """从单个源抓取新闻"""
    name = source_config["name"]
    url = source_config["url"]
    parser_name = source_config["parser"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception as e:
        print(f"[抓取] {name} 失败: {e}", file=sys.stderr)
        return []

    parser_func = PARSERS.get(parser_name)
    if not parser_func:
        print(f"[抓取] {name} 无对应解析器", file=sys.stderr)
        return []

    items = parser_func(html, TODAY)
    print(f"[抓取] {name} 获取 {len(items)} 条原始新闻", file=sys.stderr)
    return items


def fetch_all_sources(max_per_source=20):
    """从所有源抓取新闻，按优先级排序"""
    all_news = []
    for source in sorted(SOURCES, key=lambda s: s["priority"]):
        items = fetch_source(source)
        all_news.extend(items[:max_per_source])
    return all_news


# ──────────────────────────────────────────────
# 新闻过滤与分类
# ──────────────────────────────────────────────

def categorize_news(title):
    """根据标题关键词判断新闻品类"""
    title_lower = title.lower()
    categories = []

    for cat_id, cat_info in CATEGORY_KEYWORDS.items():
        for kw in cat_info["keywords"]:
            if kw.lower() in title_lower:
                categories.append(cat_id)
                break

    return categories


def is_excluded(title):
    """检查是否属于排除品类，但AI相关公司动态例外"""
    title_lower = title.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in title_lower:
            # 检查是否有AI例外关键词
            for exempt in AI_EXEMPT_KEYWORDS:
                if exempt.lower() in title_lower:
                    return False  # AI相关，不排除
            return True
    return False


def has_numbers(title):
    """检查标题是否包含关键数字"""
    patterns = [
        r'\d+[\d,.]*\s*(?:亿|万|%|倍|万亿|GB|TB|MB|亿次|万次|美元|元|周活)',
        r'\d+\s*(?:倍|万|亿)',
        r'\d+%',
        r'\d+\.\d+',
    ]
    for p in patterns:
        if re.search(p, title):
            return True
    return False


def calc_score(item):
    """计算新闻优先级分数"""
    score = 0
    categories = item.get("categories", [])

    # 品类优先级
    for cat_id in categories:
        cat_info = CATEGORY_KEYWORDS.get(cat_id, {})
        score += cat_info.get("priority", 0)

    # 有数字加分
    if item.get("has_numbers"):
        score += 15

    # 标题包含核心AI关键词加分
    title = item.get("title", "")
    core_keywords = ["大模型", "GPT", "DeepSeek", "OpenAI", "Claude", "Gemini",
                     "千问", "豆包", "通义", "文心", "Llama", "Grok", "Codex",
                     "Agent", "智能体", "AI", "模型"]
    for kw in core_keywords:
        if kw in title:
            score += 8
            break

    return score


def filter_news(news_items, max_items=7):
    """
    按规则过滤新闻：
    1. 排除无关新闻（但AI公司动态例外）
    2. 优先选择有品类命中的
    3. 按综合评分排序
    4. 去重
    """
    filtered = []

    for item in news_items:
        title = item["title"]

        # 排除规则
        if is_excluded(title):
            continue

        # 品类判断
        categories = categorize_news(title)
        item["categories"] = categories
        item["category_labels"] = [CATEGORY_KEYWORDS[c]["label"] for c in categories if c in CATEGORY_KEYWORDS]
        item["has_numbers"] = has_numbers(title)

        # 有品类命中的优先
        if categories:
            filtered.append(item)
        # 没命中品类但标题看起来像硬事件（长度适中、有动词）也可以
        elif len(title) > 15 and any(v in title for v in ["发布", "推出", "开源", "更新", "上线", "中断", "故障"]):
            filtered.append(item)

    # 去重：标题相似度 > 60% 的只保留第一条
    deduped = []
    seen_titles = []
    for item in filtered:
        title = item["title"]
        is_dup = False
        for seen in seen_titles:
            if _title_similarity(title, seen) > 0.6:
                is_dup = True
                break
        if not is_dup:
            deduped.append(item)
            seen_titles.append(title)

    # 按综合评分排序
    deduped.sort(key=calc_score, reverse=True)
    return deduped[:max_items]


def _title_similarity(a, b):
    """简单的标题相似度（字符交集比）"""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0
    return len(set_a & set_b) / max(len(set_a), len(set_b))


# ──────────────────────────────────────────────
# 详情补充（可选，从源链接抓取摘要）
# ──────────────────────────────────────────────

def extract_image_url(html, source=""):
    """从新闻页面 HTML 中提取第一张有意义的配图 URL"""
    # 常见的新闻配图模式
    patterns = [
        # <img src="..."> 或 <img data-src="...">
        r'<img[^>]*(?:src|data-src|data-original)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?)["\']',
        # og:image meta 标签
        r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        # background-image
        r'background-image:\s*url\(["\']?([^"\')\s]+\.(?:jpg|jpeg|png|webp))["\']?\)',
    ]

    # 排除的域名/路径（logo、icon、广告等）
    skip_patterns = [
        'logo', 'icon', 'avatar', 'favicon', 'ad_', 'banner_ad',
        'tracking', 'pixel', 'spacer', 'loading', 'placeholder',
        'app.aibase.com/icon', 'chinaz.com/picmap/thumb/2018',
        'chinaz.com/picmap/thumb/2023', 'beian', 'badge',
    ]

    candidates = []
    for pat in patterns:
        for match in re.finditer(pat, html, re.IGNORECASE):
            url = match.group(1)
            # 过滤掉明显的非内容图
            if any(skip in url.lower() for skip in skip_patterns):
                continue
            # 过滤掉太小的图（通过 URL 判断）
            if '1x1' in url or 'spacer' in url:
                continue
            # 补全协议
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith('http'):
                continue
            candidates.append(url)

    # 去重保持顺序
    seen = set()
    unique = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique[0] if unique else None


def enrich_details(item):
    """尝试从新闻链接抓取详情要点 + 配图 URL"""
    url = item.get("url", "")
    if not url or not url.startswith("http"):
        return item

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        text = resp.text

        # 提取配图 URL
        image_url = extract_image_url(text, item.get("source", ""))
        if image_url:
            item["image_url"] = image_url

        # 去掉 script/style 标签及内容
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<meta[^>]*>', '', text)
        text = re.sub(r'<link[^>]*>', '', text)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # 提取正文段落（通常在 <p> 标签中）
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL)

        # 提取包含数字的关键句
        details = []
        for para in paragraphs:
            line = re.sub(r'<[^>]+>', '', para).strip()
            # 过滤掉太短、太长、或像元数据的行
            if 15 < len(line) < 150:
                if any(skip in line.lower() for skip in ["viewport", "charset", "width=device", "user-scalable", "share"]):
                    continue
                if re.search(r'\d+', line) or any(kw in line for kw in ["发布", "推出", "开源", "支持", "模型", "API"]):
                    details.append(line)
                    if len(details) >= 3:
                        break

        if details:
            item["details"] = details

    except:
        pass

    return item


# ──────────────────────────────────────────────
# 生成 NEWS_SEGMENTS 格式
# ──────────────────────────────────────────────

def _smart_truncate(text, max_len=35):
    """智能截断：在标点或空格处断开，不切碎词语"""
    if len(text) <= max_len:
        return text
    # 在 max_len 范围内找最后一个标点/空格
    cut = text[:max_len]
    for sep in ["，", "。", "、", "；", " ", ",", "："]:
        idx = cut.rfind(sep)
        if idx > max_len // 2:
            return cut[:idx + 1].rstrip("，、；, ")
    return cut + "…"


def generate_segments(news_items):
    """将过滤后的新闻转换为 NEWS_SEGMENTS 格式"""
    segments = []
    today_str = datetime.now(CST).strftime("%Y 年 %m 月 %d 日")
    weekday = "一二三四五六日"[datetime.now(CST).weekday()]

    # 标题卡
    segments.append({
        "id": 1,
        "type": "title",
        "headline": "AI 早报",
        "subline": f"{today_str} 星期{weekday}",
        "narration": "欢迎收看今天的 AI 早报。",
    })

    # 新闻段落
    for i, item in enumerate(news_items):
        seg_id = i + 2
        title = item["title"]

        # 提取高亮数字
        highlights = re.findall(r'\d+[\d,.]*\s*(?:亿|万|%|倍|万亿|GB|TB|MB|美元|元|周活)', title)
        if not highlights:
            highlights = re.findall(r'\d+%', title)

        # 详情
        details = item.get("details", [title])
        if isinstance(details, list) and len(details) > 3:
            details = details[:3]

        # 旁白
        narration = item.get("narration", title + "。")
        if not narration.endswith("。"):
            narration += "。"

        # 品类标签
        cat_label = item.get("category_labels", ["📰 新闻"])[0] if item.get("category_labels") else "📰 新闻"

        seg = {
            "id": seg_id,
            "type": "news",
            "headline": _smart_truncate(title, 35),
            "details": details if isinstance(details, list) else [details],
            "highlight_nums": highlights[:2],
            "narration": narration,
            "category": cat_label,
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        }
        # 传递配图 URL（如有）
        if item.get("image_url"):
            seg["image_url"] = item["image_url"]
        segments.append(seg)

    # 结尾卡
    segments.append({
        "id": len(news_items) + 2,
        "type": "ending",
        "headline": "感谢收看",
        "subline": "关注频道，每天获取 AI 最新资讯",
        "narration": "以上就是今天的 AI 早报，感谢收看，我们明天见。",
    })

    return segments


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    max_items = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"[新闻抓取] 日期: {TODAY}", file=sys.stderr)
    print(f"[新闻抓取] 从 {len(SOURCES)} 个源获取新闻...", file=sys.stderr)

    # 1. 抓取
    raw_news = fetch_all_sources(max_per_source=20)
    print(f"[新闻抓取] 共获取 {len(raw_news)} 条原始新闻", file=sys.stderr)

    if not raw_news:
        print("[新闻抓取] 未获取到任何新闻，退出", file=sys.stderr)
        sys.exit(1)

    # 2. 过滤
    filtered = filter_news(raw_news, max_items=max_items)
    print(f"[新闻抓取] 过滤后保留 {len(filtered)} 条", file=sys.stderr)

    if not filtered:
        print("[新闻抓取] 过滤后无新闻，使用原始列表前5条", file=sys.stderr)
        filtered = raw_news[:5]
        for item in filtered:
            item["categories"] = []
            item["category_labels"] = ["📰 新闻"]
            item["has_numbers"] = False
            item["details"] = [item["title"]]
            item["narration"] = item["title"] + "。"

    # 3. 补充详情（可选，失败不阻塞）
    for item in filtered:
        try:
            enrich_details(item)
        except:
            pass

    # 4. 生成 segments
    segments = generate_segments(filtered)

    # 5. 输出
    result = json.dumps(segments, ensure_ascii=False, indent=2)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[新闻抓取] 已写入 {output_file}", file=sys.stderr)
    else:
        print(result)

    # 打印摘要
    print(f"\n[新闻摘要] 共 {len(filtered)} 条:", file=sys.stderr)
    for i, item in enumerate(filtered, 1):
        cats = ", ".join(item.get("category_labels", []))
        nums = "✓" if item.get("has_numbers") else "✗"
        score = calc_score(item)
        print(f"  {i}. [{cats}] {item['title'][:50]}... (数字:{nums}, 分:{score}, 来源:{item.get('source','')})", file=sys.stderr)


if __name__ == "__main__":
    main()
