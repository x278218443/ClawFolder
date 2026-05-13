#!/usr/bin/env python3
"""
B站自动发布脚本 — AI早知道系列
用法:
  python3 bilibili_publish.py                           # 自动找最新视频发布
  python3 bilibili_publish.py --video /path/to/video.mp4
  python3 bilibili_publish.py --dry-run                  # 只打印信息，不实际发布
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# bilibili-api-python
from bilibili_api import video_uploader, Credential, video_zone
from bilibili_api.utils.picture import Picture

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

# B站凭据 — 从环境变量或 .env 文件读取
def load_env():
    """从 .env 文件加载环境变量"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

SESSDATA = os.environ.get("BILI_SESSDATA", "")
BILI_JCT = os.environ.get("BILI_JCT", "")
BUVID3 = os.environ.get("BILI_BUVID3", "")
DEDE_USER_ID = os.environ.get("BILI_DEDEUSERID", "")

# 视频分区 — AI/科技内容
DEFAULT_TID = 231  # 科技 > 计算机技术

# 固定标签
DEFAULT_TAGS = ["AI", "AI日报", "AI大模型", "AI毁灭人类", "大模型进化", "程序", "人工智能"]


def get_credential() -> Credential:
    """构建 B站 Credential"""
    if not SESSDATA or not BILI_JCT:
        print("❌ 错误: 缺少 B站凭据")
        print("   请在 ai-video-pipeline/.env 中配置:")
        print("   BILI_SESSDATA=xxx")
        print("   BILI_JCT=xxx")
        print("   BILI_BUVID3=xxx  (可选)")
        sys.exit(1)
    return Credential(
        sessdata=SESSDATA,
        bili_jct=BILI_JCT,
        buvid3=BUVID3 if BUVID3 else None,
        dedeuserid=DEDE_USER_ID if DEDE_USER_ID else None,
    )


def find_latest_video() -> str:
    """查找最新的视频文件"""
    pipeline_dir = Path(__file__).parent
    output_dir = pipeline_dir / "output"

    # 优先读取 latest_video.txt
    latest_file = output_dir / "latest_video.txt"
    if latest_file.exists():
        video_path = latest_file.read_text().strip()
        if os.path.isfile(video_path):
            return video_path

    # 备选：按时间找最新的 board_live_* 目录
    candidates = []
    if output_dir.exists():
        for d in sorted(output_dir.iterdir(), reverse=True):
            if d.is_dir() and d.name.startswith("board_live_"):
                mp4 = d / "ai_news_board_live.mp4"
                if mp4.exists():
                    candidates.append(str(mp4))
                    break

    if candidates:
        return candidates[0]

    print("❌ 未找到视频文件，请用 --video 参数指定路径")
    sys.exit(1)


def make_title() -> str:
    """生成标题: AI早知道 + 当天日期"""
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"AI早知道 {today}"


def make_desc(title: str) -> str:
    """生成视频简介"""
    return (
        f"🤖 {title}\n\n"
        "每日 AI 资讯速递，带你了解 AI 前沿动态。\n\n"
        "#AI #AI日报 #AI大模型 #AI毁灭人类"
    )


async def upload_video(
    video_path: str,
    title: str,
    desc: str,
    tags: list[str],
    tid: int = DEFAULT_TID,
    cover_path: str = None,
    credential: Credential = None,
    dry_run: bool = False,
) -> dict:
    """
    上传视频到 B站

    Args:
        video_path: 视频文件路径
        title: 标题
        desc: 简介
        tags: 标签列表
        tid: 分区 ID
        cover_path: 封面图路径（可选）
        credential: B站凭据
        dry_run: 只打印信息，不实际上传

    Returns:
        上传结果 dict
    """
    video_path = os.path.abspath(video_path)
    if not os.path.isfile(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

    print("=" * 50)
    print("  B站视频发布")
    print("=" * 50)
    print(f"  标题: {title}")
    print(f"  简介: {desc[:80]}...")
    print(f"  标签: {', '.join(tags)}")
    print(f"  分区: {tid} (科技 > 计算机技术)")
    print(f"  视频: {video_path}")
    print(f"  大小: {file_size_mb:.1f} MB")
    if cover_path:
        print(f"  封面: {cover_path}")
    print("=" * 50)

    if dry_run:
        print("\n🔸 DRY RUN — 不实际上传")
        return {"dry_run": True, "title": title, "video": video_path}

    # 构建 VideoMeta
    meta = video_uploader.VideoMeta(
        tid=tid,
        title=title,
        desc=desc,
        cover=cover_path or "",  # 空字符串表示用视频首帧
        tags=tags,
        original=True,           # 自制
        no_reprint=True,         # 禁止转载
    )

    # 构建页面（单P视频）
    page = video_uploader.VideoUploaderPage(
        path=video_path,
        title=title,
        description=desc,
    )

    # 如果有自定义封面，先上传获取 URL
    cover_url = ""
    if cover_path and os.path.isfile(cover_path):
        print("\n📎 上传封面...")
        pic = Picture()
        pic.content = open(cover_path, "rb").read()
        pic.imageType = cover_path.rsplit(".", 1)[-1].lower()
        try:
            cover_url = await video_uploader.upload_cover(cover=pic, credential=credential)
            print(f"  ✅ 封面上传成功: {cover_url}")
            meta = video_uploader.VideoMeta(
                tid=tid,
                title=title,
                desc=desc,
                cover=cover_url,
                tags=tags,
                original=True,
                no_reprint=True,
            )
        except Exception as e:
            print(f"  ⚠️ 封面上传失败，将使用视频首帧: {e}")

    # 创建上传器
    uploader = video_uploader.VideoUploader(
        pages=[page],
        meta=meta,
        credential=credential,
        cover=cover_url if cover_path else "",
    )

    # 事件监听
    results = {}

    @uploader.on(video_uploader.VideoUploaderEvents.PREUPLOAD)
    async def on_preupload(data):
        print(f"\n📤 预上传... (upload_id: {data.get('upload_id', '?')})")

    @uploader.on(video_uploader.VideoUploaderEvents.PRE_PAGE)
    async def on_pre_page(data):
        print(f"  ⬆️ 开始上传视频文件...")

    @uploader.on(video_uploader.VideoUploaderEvents.AFTER_PAGE)
    async def on_after_page(data):
        print(f"  ✅ 视频文件上传完成")

    @uploader.on(video_uploader.VideoUploaderEvents.PRE_SUBMIT)
    async def on_pre_submit(data):
        print(f"\n📝 提交视频信息...")

    @uploader.on(video_uploader.VideoUploaderEvents.AFTER_SUBMIT)
    async def on_after_submit(data):
        results["result"] = data
        print(f"\n🎉 发布成功！")
        if isinstance(data, dict) and "bvid" in data:
            print(f"   BV号: {data['bvid']}")
            print(f"   链接: https://www.bilibili.com/video/{data['bvid']}")

    @uploader.on(video_uploader.VideoUploaderEvents.FAILED)
    async def on_failed(data):
        results["error"] = data
        print(f"\n❌ 上传失败: {data}")

    # 开始上传
    try:
        result = await uploader.start()
        results["result"] = result
        return results
    except Exception as e:
        print(f"\n❌ 上传异常: {e}")
        results["error"] = str(e)
        return results


async def main():
    parser = argparse.ArgumentParser(description="B站自动发布 — AI早知道")
    parser.add_argument("--video", type=str, help="视频文件路径（默认自动查找最新）")
    parser.add_argument("--title", type=str, help="自定义标题（默认: AI早知道 + 日期）")
    parser.add_argument("--tags", type=str, help="自定义标签，逗号分隔")
    parser.add_argument("--tid", type=int, default=DEFAULT_TID, help="分区 ID（默认: 95 科技>数码）")
    parser.add_argument("--cover", type=str, help="封面图路径")
    parser.add_argument("--desc", type=str, help="自定义简介")
    parser.add_argument("--dry-run", action="store_true", help="只打印信息，不实际上传")
    args = parser.parse_args()

    # 获取凭据
    credential = get_credential() if not args.dry_run else None

    # 查找视频
    video_path = args.video or find_latest_video()

    # 生成标题
    title = args.title or make_title()

    # 生成简介
    desc = args.desc or make_desc(title)

    # 标签
    tags = args.tags.split(",") if args.tags else DEFAULT_TAGS

    # 上传
    result = await upload_video(
        video_path=video_path,
        title=title,
        desc=desc,
        tags=tags,
        tid=args.tid,
        cover_path=args.cover,
        credential=credential,
        dry_run=args.dry_run,
    )

    # 输出结果 JSON
    result_path = Path(__file__).parent / "output" / "bilibili_publish_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as f:
        # Filter non-serializable items
        safe_result = {}
        for k, v in result.items():
            try:
                json.dumps(v)
                safe_result[k] = v
            except (TypeError, ValueError):
                safe_result[k] = str(v)
        json.dump(safe_result, f, ensure_ascii=False, indent=2)

    print(f"\n📄 结果已保存: {result_path}")


if __name__ == "__main__":
    asyncio.run(main())
