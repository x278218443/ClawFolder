"""
AI 短视频流水线 - 主控模块
橘鸦Juya AI 早报风格：多话题新闻，横屏 16:9
串联 采集 → 多话题脚本 → 配图 → TTS → 字幕 → 视频 合成
"""
import os
import sys
import json
import argparse
from datetime import datetime

# 确保当前目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR
from collector import fetch_news
from scriptwriter import generate_script
from tts_engine import synthesize_speech
from image_fetcher import fetch_images_for_segments
from board_maker import compose_board_image
from video_maker import generate_subtitles_for_segments, compose_news_video
from video_generator import generate_videos_for_segments


def run_pipeline(
    topics: list[str] = None,
    count_per_topic: int = 5,
    voice_id: str = None,
    speed: float = 1.1,
    dry_run: bool = False,
) -> dict:
    """
    运行完整流水线（多话题 AI 早报）

    参数:
        topics: 话题关键词列表
        count_per_topic: 每个话题采集数
        voice_id: TTS 音色名称
        speed: 语速 (1.0 = 正常)
        dry_run: True 则只生成脚本不合成视频

    返回:
        {
            "date": str,
            "title": str,
            "segments": list,
            "audio": str,
            "video": str,
            "srt": str,
            "tags": list,
            "news_count": int,
            "segment_count": int,
            "duration_sec": float,
        }
    """
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_dir = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir, exist_ok=True)

    result = {"date": date_str}

    # === Step 1: 内容采集 ===
    print("\n" + "=" * 50)
    print("📰 Step 1/6: 内容采集")
    print("=" * 50)

    news = fetch_news(topics, count_per_topic)
    if not news:
        print("[流水线] ⚠️ 未采集到任何新闻，流程终止")
        return None

    result["news_count"] = len(news)

    # 保存原始素材
    with open(os.path.join(output_dir, "news_raw.json"), "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

    # === Step 2: 多话题脚本生成 ===
    print("\n" + "=" * 50)
    print("✍️  Step 2/6: 多话题脚本生成")
    print("=" * 50)

    script = generate_script(news)
    if not script or not script.get("segments"):
        print("[流水线] ⚠️ 脚本生成失败，流程终止")
        return None

    segments = script["segments"]
    result["title"] = script["title"]
    result["segments"] = segments
    result["tags"] = script.get("tags", [])
    result["segment_count"] = len(segments)

    # 保存脚本
    with open(os.path.join(output_dir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"\n📜 标题: {script['title']}")
    print(f"📜 新闻条数: {len(segments)}")
    total_chars = sum(len(s.get("narration", "")) for s in segments)
    print(f"📜 总字数: {total_chars}")
    for i, seg in enumerate(segments):
        print(f"  [{i+1}] {seg.get('headline', '')} ({len(seg.get('narration', ''))}字)")

    if dry_run:
        # dry-run: 仍然获取配图预览（板书风格）
        print("\n[Dry Run] 获取配图预览（板书风格）...")
        images_dir = os.path.join(output_dir, "images")
        boards_dir = os.path.join(output_dir, "boards")
        os.makedirs(boards_dir, exist_ok=True)
        raw_photo_paths = fetch_images_for_segments(segments, images_dir)
        board_paths = []
        for i, (seg, photo) in enumerate(zip(segments, raw_photo_paths)):
            board_path = os.path.join(boards_dir, f"board_{i:02d}.jpg")
            result_path = compose_board_image(seg, photo, board_path, "AI 早报", i)
            board_paths.append(result_path if result_path else "")
        result["image_paths"] = board_paths
        result["raw_photo_paths"] = raw_photo_paths
        print("\n[Dry Run] 跳过 TTS 和视频合成")
        return result

    # === Step 3: 为每个 segment 获取配图（板书风格）===
    print("\n" + "=" * 50)
    print("🖼️  Step 3/6: 获取配图（板书风格）")
    print("=" * 50)

    images_dir = os.path.join(output_dir, "images")
    boards_dir = os.path.join(output_dir, "boards")
    os.makedirs(boards_dir, exist_ok=True)

    # 3a. 用 Seedream 生成每条新闻的配图（写实照片）
    print("[板书] 生成 Seedream 照片...")
    raw_photo_paths = fetch_images_for_segments(segments, images_dir)

    # 3b. 合成板书风格图片：深色网格背景 + 左侧照片 + 右侧标题/高亮
    print("[板书] 合成板书风格图片...")
    board_paths = []
    for i, (seg, photo) in enumerate(zip(segments, raw_photo_paths)):
        board_path = os.path.join(boards_dir, f"board_{i:02d}.jpg")
        result_path = compose_board_image(
            segment=seg,
            photo_path=photo,
            output_path=board_path,
            logo_text="AI 早报",
            index=i,
        )
        board_paths.append(result_path if result_path else "")

    n_ok = sum(1 for p in board_paths if p)
    print(f"[板书] 完成: {n_ok}/{len(board_paths)} 张")

    # 使用板书图片作为最终配图
    image_paths = board_paths
    result["image_paths"] = image_paths
    result["raw_photo_paths"] = raw_photo_paths

    # === Step 3.5: Seedance 动态视频片段 ===
    print("\n" + "=" * 50)
    print("🎬 Step 3.5/6: Seedance 视频生成")
    print("=" * 50)

    videos_dir = os.path.join(output_dir, "videos")
    video_paths = generate_videos_for_segments(segments, videos_dir)
    result["video_paths"] = video_paths

    # === Step 4: TTS 语音合成（拼接所有 narration）===
    print("\n" + "=" * 50)
    print("🎙️  Step 4/6: 语音合成")
    print("=" * 50)

    # 拼接所有 segment 的 narration，中间加停顿
    full_narration = _assemble_narration(segments)
    print(f"[TTS] 旁白总字数: {len(full_narration)}")

    audio_path = os.path.join(output_dir, "narration.mp3")
    tts_result = synthesize_speech(full_narration, audio_path, voice_id, speed)

    if not tts_result or not os.path.exists(audio_path):
        print("[流水线] ⚠️ TTS 合成失败，流程终止")
        return None

    result["audio"] = audio_path
    result["duration_sec"] = tts_result.get("duration_sec", 0)

    print(f"🎵 音频: {audio_path}")
    print(f"🎵 时长: {result['duration_sec']:.1f} 秒")

    # === Step 5: 生成字幕 ===
    print("\n" + "=" * 50)
    print("📝 Step 5/6: 生成字幕")
    print("=" * 50)

    # 计算每段的时间分配
    duration = result["duration_sec"]
    segment_timings = _calc_segment_timings(segments, duration)

    srt_path = os.path.join(output_dir, "subtitles.srt")
    generate_subtitles_for_segments(segments, segment_timings, srt_path)
    result["srt"] = srt_path

    # === Step 6: 合成横屏多段视频 ===
    print("\n" + "=" * 50)
    print("🎬 Step 6/6: 合成视频")
    print("=" * 50)

    video_path = os.path.join(output_dir, "final_video.mp4")
    compose_news_video(
        audio_path=audio_path,
        srt_path=srt_path,
        image_paths=image_paths,
        segments=segments,
        output_path=video_path,
        video_paths=video_paths,
    )
    result["video"] = video_path

    # 保存元数据
    meta_path = os.path.join(output_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # === 完成 ===
    print("\n" + "=" * 50)
    print("✅ 流水线完成!")
    print("=" * 50)
    print(f"📁 输出目录: {output_dir}")
    print(f"🎬 视频文件: {video_path}")
    print(f"⏱️  时长: {result['duration_sec']:.1f} 秒")
    print(f"📰 新闻条数: {result['segment_count']}")
    print(f"🏷️  标签: {', '.join(result.get('tags', []))}")

    if os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"📦 文件大小: {size_mb:.1f} MB")

    return result


def _assemble_narration(segments: list[dict]) -> str:
    """
    拼接所有 segment 的 narration，每个之间加 0.5 秒停顿
    """
    parts = []
    for seg in segments:
        narration = seg.get("narration", "").strip()
        if narration:
            parts.append(narration)

    # 用"……"表示停顿，TTS 会自然产生间隔
    return "……".join(parts)


def _calc_segment_timings(segments: list[dict], total_duration: float) -> list[dict]:
    """
    计算每段的起止时间（按 narration 字数比例分配）
    """
    narrations = [seg.get("narration", "") for seg in segments]
    total_chars = sum(len(n) for n in narrations)
    if total_chars == 0:
        total_chars = 1

    timings = []
    current = 0.0
    for i, n in enumerate(narrations):
        d = total_duration * len(n) / total_chars
        d = max(2.0, d)  # 每段至少 2 秒
        timings.append({"start": current, "end": current + d})
        current += d

    # 归一化使总时长匹配
    raw_total = current
    if raw_total > 0 and abs(raw_total - total_duration) > 1.0:
        ratio = total_duration / raw_total
        for t in timings:
            t["start"] *= ratio
            t["end"] *= ratio

    return timings


def main():
    parser = argparse.ArgumentParser(description="AI 早报短视频流水线")
    parser.add_argument("--topics", nargs="+", help="话题关键词列表")
    parser.add_argument("--count", type=int, default=5, help="每个话题采集数")
    parser.add_argument("--voice", type=str, default=None, help="TTS 音色名称")
    parser.add_argument("--speed", type=float, default=1.1, help="语速 (1.0=正常)")
    parser.add_argument("--dry-run", action="store_true", help="只生成脚本和配图，不合成视频")

    args = parser.parse_args()

    result = run_pipeline(
        topics=args.topics,
        count_per_topic=args.count,
        voice_id=args.voice,
        speed=args.speed,
        dry_run=args.dry_run,
    )

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
