"""
AI 短视频流水线 - 图片采集模块
橘鸦Juya AI 早报风格：为每个新闻段落单独获取横屏配图

优先级：豆包 Seedream 4.0 > 通义万相 AI 生图 > Unsplash > Lorem Picsum
"""
import os
import re
import json
import time
import requests


# ============================================================
# 通义万相（DashScope）AI 生图
# ============================================================

def _load_dashscope_key():
    """从环境变量或 .env 文件读取 DashScope API Key"""
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if key:
        return key
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DASHSCOPE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


def _load_ark_key():
    """从环境变量或 .env 文件读取火山方舟 ARK API Key"""
    key = os.environ.get("ARK_API_KEY", "")
    if key:
        return key
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ARK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


# ============================================================
# 豆包 Seedream 4.0（火山方舟 ARK API）
# ============================================================

# Seedream 模型配置（4.0 为主，5.0-lite 已停用）
SEEDREAM_MODELS = [
    "doubao-seedream-4-0-250828",
]


def _generate_from_seedream(prompt: str, output_path: str, api_key: str, size: str = "2560x1440", model: str = None) -> bool:
    """
    使用豆包 Seedream 生成图片（火山方舟 ARK API）
    自动尝试 Seedream 4.0

    参数:
        prompt: 图片描述（英文效果更好）
        output_path: 输出路径
        api_key: ARK API Key
        size: 图片尺寸（最低 3686400 像素，16:9 用 2560x1440）
        model: 指定模型（默认自动降级）
    """
    models_to_try = [model] if model else SEEDREAM_MODELS

    for model_id in models_to_try:
        try:
            resp = requests.post(
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "size": size,
                    "n": 1,
                    "response_format": "url",
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                err_msg = data['error'].get('message', 'unknown')
                print(f"[图片] {model_id} 错误: {err_msg}")
                # 如果是配额/权限错误，尝试下一个模型
                if any(kw in err_msg.lower() for kw in ["quota", "limit", "permission", "exceed", "余额", "额度"]):
                    continue
                return False

            images = data.get("data", [])
            if not images or not images[0].get("url"):
                print(f"[图片] {model_id} 无返回图片")
                continue

            img_url = images[0]["url"]
            img_resp = requests.get(img_url, timeout=30)
            if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(img_resp.content)
                short_prompt = prompt[:40]
                print(f"[图片] {model_id}: '{short_prompt}' ({len(img_resp.content)//1024}KB)")
                return True

            print(f"[图片] {model_id} 图片下载失败")
            continue

        except Exception as e:
            print(f"[图片] {model_id} 错误: {e}")
            continue

    return False


def _generate_from_dashscope(prompt: str, output_path: str, api_key: str, size: str = "1280*720") -> bool:
    """
    通义万相 wanx2.1-t2i-turbo 生成图片（异步流程）

    参数:
        prompt: 英文描述
        output_path: 输出路径
        api_key: DashScope API Key
        size: 图片尺寸（横屏用 1280*720）
    """
    try:
        # Step 1: 提交生成任务
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json={
                "model": "wanx2.1-t2i-turbo",
                "input": {"prompt": prompt},
                "parameters": {"size": size, "n": 1},
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            print(f"[图片] DashScope 无 task_id: {data}")
            return False

        # Step 2: 轮询等待结果（最多 30 秒）
        for attempt in range(10):
            time.sleep(3)
            poll_resp = requests.get(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            poll_data = poll_resp.json()
            status = poll_data.get("output", {}).get("task_status", "")

            if status == "SUCCEEDED":
                results = poll_data.get("output", {}).get("results", [])
                if results and results[0].get("url"):
                    img_url = results[0]["url"]
                    img_resp = requests.get(img_url, timeout=20)
                    if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        short_prompt = prompt[:40]
                        print(f"[图片] 通义万相: '{short_prompt}' ({len(img_resp.content)//1024}KB)")
                        return True
                print(f"[图片] DashScope 成功但无图片 URL")
                return False

            elif status == "FAILED":
                error = poll_data.get("output", {}).get("message", "unknown")
                print(f"[图片] DashScope 生成失败: {error}")
                return False

        print(f"[图片] DashScope 超时 (task: {task_id})")
        return False

    except Exception as e:
        print(f"[图片] DashScope 错误: {e}")
        return False


def _enhance_prompt(query: str) -> str:
    """
    将简短的 image_query 增强为适合 AI 生图的英文 prompt

    橘鸦风格：真实感科技新闻配图，每个新闻主题独立画面
    """
    # 基础风格前缀 — 模拟真实新闻摄影
    style = (
        "Ultra realistic photojournalism, tech news broadcast style, "
        "professional editorial photography, sharp focus, natural lighting, "
        "modern corporate or technology setting, 16:9 wide angle, "
        "no text, no watermark, high resolution. "
    )

    # 如果 query 已经比较详细（>30 字符），直接用
    if len(query) > 30:
        return style + query

    # 简短 query 加上具体场景描述
    return style + f"Realistic scene about {query}, tech company office, product launch, or technology concept, editorial news photography"


# ============================================================
# Unsplash
# ============================================================

def _load_unsplash_key():
    """从环境变量或 .env 文件读取 Unsplash API Key"""
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if key:
        return key
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("UNSPLASH_ACCESS_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


def _fetch_from_unsplash(query: str, output_path: str, api_key: str) -> bool:
    """从 Unsplash 搜索并下载一张横屏图片"""
    headers = {"Authorization": f"Client-ID {api_key}"}
    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            headers=headers,
            params={"query": query, "per_page": 3, "orientation": "landscape"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])

        if not results:
            return False

        for photo in results:
            if not isinstance(photo, dict):
                continue
            urls = photo.get("urls")
            if urls and isinstance(urls, dict):
                img_url = urls.get("regular", "") or urls.get("small", "")
                desc = (photo.get("description") or photo.get("alt_description") or "")[:30]
                if img_url:
                    img_resp = requests.get(img_url, timeout=20)
                    if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        print(f"[图片] Unsplash: '{query}' -> {desc} ({len(img_resp.content)//1024}KB)")
                        return True

        return False

    except Exception as e:
        print(f"[图片] Unsplash '{query}' 失败: {e}")
        return False


# ============================================================
# Lorem Picsum（兜底）
# ============================================================

def _fetch_from_lorem(output_path: str, seed: int = 42) -> bool:
    """从 Lorem Picsum 获取一张随机横屏图片"""
    url = f"https://picsum.photos/seed/{seed}/1920/1080"
    try:
        resp = requests.get(url, timeout=20, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print(f"[图片] Lorem Picsum: seed={seed} ({len(resp.content)//1024}KB)")
            return True
        return False
    except Exception as e:
        print(f"[图片] Lorem Picsum seed={seed} 错误: {e}")
        return False


# ============================================================
# 主入口
# ============================================================

def fetch_images_for_segments(segments: list[dict], output_dir: str) -> list[str]:
    """
    为每个 segment 单独获取配图

    优先级：豆包 Seedream 4.0 > 通义万相 AI 生图 > Unsplash > Lorem Picsum

    参数:
        segments: 脚本中的 segments 列表，每个包含 image_query 字段
        output_dir: 图片保存目录

    返回: 每个 segment 对应的图片路径列表（与 segments 一一对应）
    """
    os.makedirs(output_dir, exist_ok=True)
    images = []

    ark_key = _load_ark_key()
    dashscope_key = _load_dashscope_key()
    unsplash_key = _load_unsplash_key()

    use_seedream = bool(ark_key)
    use_dashscope = bool(dashscope_key)
    use_unsplash = bool(unsplash_key)

    if use_seedream:
        print(f"[图片] 主图片源: 豆包 Seedream 4.0 (火山方舟 ARK)")
    elif use_dashscope:
        print(f"[图片] 主图片源: 通义万相 (wanx2.1-t2i-turbo)")
    elif use_unsplash:
        print(f"[图片] 主图片源: Unsplash")
    else:
        print(f"[图片] 仅使用 Lorem Picsum 兜底")

    for i, seg in enumerate(segments):
        query = seg.get("image_query", "technology")
        img_path = os.path.join(output_dir, f"segment_{i:02d}.jpg")

        downloaded = False

        # 1. 豆包 Seedream 4.0（火山方舟 ARK）
        if use_seedream:
            enhanced_prompt = _enhance_prompt(query)
            downloaded = _generate_from_seedream(enhanced_prompt, img_path, ark_key)

        # 2. 通义万相 AI 生图
        if not downloaded and use_dashscope:
            enhanced_prompt = _enhance_prompt(query)
            downloaded = _generate_from_dashscope(enhanced_prompt, img_path, dashscope_key)

        # 3. Unsplash
        if not downloaded and use_unsplash:
            downloaded = _fetch_from_unsplash(query, img_path, unsplash_key)

        # 4. Lorem Picsum 兜底
        if not downloaded:
            downloaded = _fetch_from_lorem(img_path, seed=i + 42)

        if downloaded:
            images.append(img_path)
        else:
            print(f"[图片] ⚠️ segment {i} 无图片")
            images.append("")

    n_ok = sum(1 for p in images if p)
    print(f"[图片] 获取完成: {n_ok}/{len(images)} 张")
    return images


def fetch_images_for_script(
    script: dict,
    output_dir: str,
    count: int = 5,
    source: str = "auto",
) -> list[str]:
    """兼容旧接口"""
    os.makedirs(output_dir, exist_ok=True)

    keywords = _extract_keywords(script)
    print(f"[图片] 关键词: {keywords}")

    images = []
    ark_key = _load_ark_key()
    dashscope_key = _load_dashscope_key()
    unsplash_key = _load_unsplash_key()

    for i, kw in enumerate(keywords[:count]):
        img_path = os.path.join(output_dir, f"image_{i:02d}.jpg")
        downloaded = False

        if source in ("auto", "seedream") and ark_key:
            downloaded = _generate_from_seedream(_enhance_prompt(kw), img_path, ark_key)

        if not downloaded and source in ("auto", "dashscope") and dashscope_key:
            downloaded = _generate_from_dashscope(_enhance_prompt(kw), img_path, dashscope_key)

        if not downloaded and source in ("auto", "unsplash") and unsplash_key:
            downloaded = _fetch_from_unsplash(kw, img_path, unsplash_key)

        if not downloaded and source in ("auto", "lorem"):
            downloaded = _fetch_from_lorem(img_path, seed=i + 42)

        if downloaded:
            images.append(img_path)

    print(f"[图片] 获取完成: {len(images)} 张")
    return images[:count]


def _extract_keywords(script: dict) -> list[str]:
    """从脚本中提取图片搜索关键词"""
    keywords = []

    tags = script.get("tags", [])
    keywords.extend(tags[:3])

    title = script.get("title", "")
    if title:
        clean = re.sub('[，。！？、；：""''《》【】\\s]+', ' ', title)
        words = [w.strip() for w in clean.split() if len(w.strip()) >= 2]
        keywords.extend(words[:3])

    cn_to_en = {
        "AI": "artificial intelligence",
        "人工智能": "artificial intelligence",
        "科技": "technology",
        "数码": "digital",
        "芯片": "chip semiconductor",
        "机器人": "robot",
        "数据": "data visualization",
        "网络": "network",
        "编程": "programming",
        "手机": "smartphone",
        "电脑": "computer",
        "未来": "futuristic",
        "太空": "space",
        "量子": "quantum",
        "电商": "ecommerce",
        "金融": "finance",
        "医疗": "medical",
        "教育": "education",
        "游戏": "gaming",
        "汽车": "automobile",
        "豆包": "chatbot AI",
        "字节跳动": "social media",
        "腾讯": "technology company",
        "工作": "work office",
        "赚钱": "business",
    }

    en_keywords = []
    for kw in keywords:
        if kw in cn_to_en:
            en_keywords.append(cn_to_en[kw])
        elif re.match(r'^[\x00-\x7F]+$', kw):
            en_keywords.append(kw)
        else:
            en_keywords.append("technology")

    if not en_keywords:
        en_keywords = ["technology", "artificial intelligence"]

    return list(dict.fromkeys(en_keywords))


if __name__ == "__main__":
    test_segments = [
        {"index": 1, "headline": "AI巨头大变天", "image_query": "artificial intelligence robot in modern office"},
        {"index": 2, "headline": "苹果新品曝光", "image_query": "apple smartphone product launch event"},
    ]
    images = fetch_images_for_segments(test_segments, "output/test_images")
    print(f"\n获取到 {len(images)} 张图片:")
    for i, img in enumerate(images):
        print(f"  segment {i}: {img}")
