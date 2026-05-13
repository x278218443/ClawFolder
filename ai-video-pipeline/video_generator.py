"""
AI 短视频流水线 - Seedance 视频生成模块
使用火山方舟 ARK API 调用 Doubao-Seedance-1.5-Pro 为每条新闻生成动态视频片段
"""
import os
import time
import requests


ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"
ARK_MODEL = "doubao-seedance-1-5-pro-251215"
POLL_INTERVAL = 15  # 秒
MAX_WAIT = 300      # 最长等待 5 分钟


def _load_ark_key():
    """从环境变量或 .env 文件读取 ARK API Key"""
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


def _enhance_video_prompt(query: str) -> str:
    """
    将简短的 image_query 增强为适合 Seedance 视频生成的 prompt
    
    Seedance 擅长：运镜、场景转换、人物动作
    """
    style = (
        "Cinematic broadcast news footage, smooth camera movement, "
        "professional lighting, high production value, 4K quality. "
    )

    if len(query) > 30:
        return style + query

    return style + f"Dynamic cinematic scene about {query}, professional news broadcast style footage"


def _create_task(prompt: str, api_key: str) -> dict:
    """创建 Seedance 视频生成任务"""
    resp = requests.post(
        f"{ARK_BASE}/contents/generations/tasks",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": ARK_MODEL,
            "content": [{"type": "text", "text": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _poll_task(task_id: str, api_key: str) -> dict | None:
    """轮询任务状态，返回成功结果或 None"""
    for i in range(MAX_WAIT // POLL_INTERVAL):
        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.get(
                f"{ARK_BASE}/contents/generations/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            print(f"  [{(i+1)*POLL_INTERVAL}s] 轮询错误: {e}")
            continue

        status = data.get("status", "")
        elapsed = (i + 1) * POLL_INTERVAL
        print(f"  [{elapsed}s] {status}")

        if status == "succeeded":
            return data
        elif status == "failed":
            err = data.get("error", {})
            print(f"  失败: {err.get('message', 'unknown')}")
            return None

    print(f"  超时 ({MAX_WAIT}s)")
    return None


def _download(url: str, output_path: str) -> bool:
    """下载视频文件"""
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return True
        print(f"  下载失败: status={r.status_code}, size={len(r.content)}")
        return False
    except Exception as e:
        print(f"  下载错误: {e}")
        return False


def generate_videos_for_segments(
    segments: list[dict],
    output_dir: str,
    timeout_per_video: int = 300,
) -> list[str]:
    """
    为每个 segment 生成 Seedance 视频片段

    参数:
        segments: 脚本 segments 列表（需要 image_query 字段）
        output_dir: 视频保存目录
        timeout_per_video: 每个视频的最长等待时间（秒）

    返回: 每个 segment 对应的视频路径列表（与 segments 一一对应）
    """
    os.makedirs(output_dir, exist_ok=True)

    api_key = _load_ark_key()
    if not api_key:
        print("[Seedance] ⚠️ ARK API Key 未配置，跳过视频生成")
        return [""] * len(segments)

    global MAX_WAIT
    MAX_WAIT = timeout_per_video

    print(f"[Seedance] 开始生成 {len(segments)} 段视频 (Seedance 1.5 Pro)")

    video_paths = []
    for i, seg in enumerate(segments):
        query = seg.get("image_query", "technology")
        prompt = _enhance_video_prompt(query)
        output_path = os.path.join(output_dir, f"clip_{i:02d}.mp4")

        print(f"\n[Seedance] [{i+1}/{len(segments)}] {query[:50]}...")

        try:
            result = _create_task(prompt, api_key)
            task_id = result.get("id", "")
            if not task_id:
                print(f"  无 task ID: {result}")
                video_paths.append("")
                continue

            print(f"  任务: {task_id}")
            task_result = _poll_task(task_id, api_key)

            if not task_result:
                video_paths.append("")
                continue

            video_url = task_result.get("content", {}).get("video_url", "")
            if not video_url:
                print(f"  无视频 URL")
                video_paths.append("")
                continue

            if _download(video_url, output_path):
                size_kb = os.path.getsize(output_path) // 1024
                resolution = task_result.get("resolution", "?")
                duration = task_result.get("duration", "?")
                print(f"  ✅ {size_kb}KB | {resolution} | {duration}s")
                video_paths.append(output_path)
            else:
                video_paths.append("")

        except requests.exceptions.HTTPError as e:
            print(f"  HTTP 错误: {e}")
            video_paths.append("")
        except Exception as e:
            print(f"  错误: {e}")
            video_paths.append("")

    n_ok = sum(1 for p in video_paths if p)
    print(f"\n[Seedance] 完成: {n_ok}/{len(video_paths)} 段成功")
    return video_paths
