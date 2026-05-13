"""
AI 短视频流水线 - 视频合成模块
橘鸦Juya AI 早报风格：横屏 16:9，多段新闻，Ken Burns 效果
"""
import os
import subprocess
import json
import math
import re
from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_BG_COLOR,
    SUBTITLE_FONT, SUBTITLE_FONTSIZE, SUBTITLE_COLOR,
    SUBTITLE_OUTLINE_COLOR, SUBTITLE_OUTLINE_WIDTH, SUBTITLE_POSITION_Y,
)


# ============================================================
# 字幕生成（通用）
# ============================================================

def generate_subtitles_for_segments(segments: list[dict], segment_timings: list[dict], output_srt: str) -> str:
    """
    为多段新闻生成 SRT 字幕文件

    参数:
        segments: 脚本 segments 列表
        segment_timings: [{"start": float, "end": float}] 每段的起止时间
        output_srt: 输出 SRT 路径
    """
    srt_lines = []
    sub_idx = 1

    for seg, timing in zip(segments, segment_timings):
        narration = seg.get("narration", "")
        if not narration:
            continue

        start_sec = timing["start"]
        end_sec = timing["end"]
        duration = end_sec - start_sec

        # 智能断句
        parts = _split_text(narration, max_chars_per_line=20)
        if not parts:
            parts = [narration]

        total_chars = sum(len(p) for p in parts)
        if total_chars == 0:
            continue

        current = start_sec
        for j, part in enumerate(parts):
            char_ratio = len(part) / total_chars
            part_duration = duration * char_ratio
            part_duration = max(0.8, min(4.0, part_duration))

            part_end = min(current + part_duration, end_sec)
            # 确保最后一段字幕不超出段落边界，且至少有 0.3 秒
            if j == len(parts) - 1:
                part_end = end_sec
            if part_end - current < 0.3:
                part_end = min(current + 0.3, end_sec)
            if part_end <= current:
                current = part_end
                continue
            srt_lines.append(f"{sub_idx}")
            srt_lines.append(f"{_format_time(current)} --> {_format_time(part_end)}")
            srt_lines.append(part.strip())
            srt_lines.append("")
            sub_idx += 1
            current = part_end

    os.makedirs(os.path.dirname(os.path.abspath(output_srt)), exist_ok=True)
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"[字幕] 多段字幕生成完成: {sub_idx - 1} 条 -> {output_srt}")
    return output_srt


def generate_subtitles(narration: str, duration_sec: float, output_srt: str) -> str:
    """
    将旁白文本拆分为 SRT 字幕文件（兼容旧接口）
    每行约 16 字，自动按时长分配时间戳
    """
    segments = _split_text(narration, max_chars_per_line=16)
    if not segments:
        segments = [narration]

    total_chars = sum(len(s) for s in segments)
    if total_chars == 0:
        return output_srt

    srt_lines = []
    current_time = 0.0

    for i, seg in enumerate(segments):
        char_ratio = len(seg) / total_chars
        seg_duration = duration_sec * char_ratio
        seg_duration = max(1.0, min(5.0, seg_duration))

        start = current_time
        end = current_time + seg_duration
        if i == len(segments) - 1:
            end = duration_sec

        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{_format_time(start)} --> {_format_time(end)}")
        srt_lines.append(seg.strip())
        srt_lines.append("")
        current_time = end

    os.makedirs(os.path.dirname(os.path.abspath(output_srt)), exist_ok=True)
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"[字幕] 生成完成: {len(segments)} 条字幕 -> {output_srt}")
    return output_srt


# ============================================================
# 横屏多段新闻视频（新）
# ============================================================

def compose_news_video(
    audio_path: str,
    srt_path: str,
    image_paths: list[str],
    segments: list[dict],
    output_path: str,
    video_paths: list[str] = None,
) -> str:
    """
    合成橘鸦Juya AI 早报风格的横屏多段新闻视频

    参数:
        audio_path: 完整旁白音频路径
        srt_path: SRT 字幕路径
        image_paths: 每个 segment 对应的图片路径列表
        segments: 脚本 segments 列表
        output_path: 输出视频路径
        video_paths: 每个 segment 对应的 Seedance 视频路径列表（可选，优先于图片）

    返回: 输出视频路径
    """
    import random
    random.seed(42)

    duration = _get_duration(audio_path)
    n_segments = len(segments)

    if not image_paths or all(not p for p in image_paths):
        print("[视频] 无图片，降级到纯色背景")
        return compose_video(audio_path, srt_path, output_path, title=segments[0].get("headline", ""), duration=duration)

    # 计算每段时长（按 narration 字数比例）
    narrations = [seg.get("narration", "") for seg in segments]
    total_chars = sum(len(n) for n in narrations)
    if total_chars == 0:
        total_chars = 1

    segment_durations = []
    for n in narrations:
        d = duration * len(n) / total_chars
        d = max(3.0, d)  # 每段至少 3 秒
        segment_durations.append(d)

    # 归一化使总时长匹配
    raw_total = sum(segment_durations)
    if raw_total > 0:
        segment_durations = [d * duration / raw_total for d in segment_durations]

    print(f"[视频] 新闻模式: {n_segments} 段, 总时长 {duration:.1f}s")
    for i, (seg, d) in enumerate(zip(segments, segment_durations)):
        print(f"  [{i+1}] {seg.get('headline', '')[:30]} -> {d:.1f}s")

    # Ken Burns 模式
    kb_patterns = [
        (1.0, 1.12, 0, 0, -60, -30),
        (1.12, 1.0, -60, -30, 0, 0),
        (1.0, 1.10, -30, 0, 30, -20),
        (1.10, 1.0, 30, -20, -30, 0),
        (1.0, 1.08, 0, -20, 0, 20),
        (1.08, 1.0, 0, 20, 0, -20),
    ]

    # 构建 FFmpeg 滤镜
    # 策略：每个 segment 用单帧图片输入 + zoompan 生成 d 帧，再 concat
    inputs = []
    filter_parts = []
    valid_segments = []

    for i, (img_path, seg_dur) in enumerate(zip(image_paths, segment_durations)):
        if not img_path or not os.path.exists(img_path):
            continue

        idx = len(valid_segments)
        valid_segments.append(i)

        n_frames = int(seg_dur * VIDEO_FPS)

        has_video = (video_paths and i < len(video_paths) and
                     video_paths[i] and os.path.exists(video_paths[i]))

        if has_video:
            # Seedance 视频片段：循环播放填充段落时长
            inputs.extend(["-stream_loop", "-1", "-t", f"{seg_dur:.2f}", "-i", video_paths[i]])
            filter_parts.append(
                f"[{idx}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={VIDEO_BG_COLOR},"
                f"format=yuv420p,"
                f"fade=t=in:st=0:d=0.5,"
                f"fade=t=out:st={seg_dur - 0.5:.2f}:d=0.5,"
                f"setsar=1[v{idx}]"
            )
        else:
            # 静态图片 + Ken Burns 效果
            inputs.extend(["-i", img_path])

            pattern = kb_patterns[idx % len(kb_patterns)]
            s_start, s_end, x1, y1, x2, y2 = pattern

            filter_parts.append(
                f"[{idx}:v]scale={VIDEO_WIDTH + 200}:{VIDEO_HEIGHT + 200},"
                f"zoompan=z='if(eq(on,1),{s_start},{s_end})':"
                f"x='iw/2-(iw/zoom/2)+({x2}-{x1})*on/{n_frames}':"
                f"y='ih/2-(ih/zoom/2)+({y2}-{y1})*on/{n_frames}':"
                f"d={n_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:"
                f"fps={VIDEO_FPS},"
                f"fade=t=in:st=0:d=0.5,"
                f"fade=t=out:st={seg_dur - 0.5:.2f}:d=0.5,"
                f"setsar=1[v{idx}]"
            )

        # 叠加新闻标题
        headline = segments[i].get("headline", "")
        if headline:
            safe_headline = _escape_ffmpeg_text(headline[:30])
            filter_parts.append(
                f"[v{idx}]drawtext="
                f"fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:"
                f"text='{safe_headline}':"
                f"fontcolor=white:fontsize=52:"
                f"x=(w-text_w)/2:y=60:"
                f"borderw=3:bordercolor=black@0.8[vh{idx}]"
            )
            last_v = f"vh{idx}"
        else:
            last_v = f"v{idx}"

    if not valid_segments:
        print("[视频] 无有效图片，降级到纯色背景")
        return compose_video(audio_path, srt_path, output_path, duration=duration)

    # 拼接所有段落
    n_valid = len(valid_segments)
    concat_labels = []
    for i in range(n_valid):
        if any(f"vh{i}]" in line for line in filter_parts):
            concat_labels.append(f"[vh{i}]")
        else:
            concat_labels.append(f"[v{i}]")
    concat_str = "".join(concat_labels)
    filter_parts.append(f"{concat_str}concat=n={n_valid}:v=1:a=0[vconcat]")
    last_label = "vconcat"

    # 叠加字幕
    if srt_path and os.path.exists(srt_path):
        ass_path = srt_path.replace(".srt", ".ass")
        _srt_to_ass(srt_path, ass_path)
        if os.path.exists(ass_path):
            filter_parts.append(f"[{last_label}]ass='{ass_path}'[v]")
            last_label = "v"

    filter_complex = ";\n".join(filter_parts)

    # 音频输入
    audio_idx = n_valid
    inputs.extend(["-i", audio_path])

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"[视频] 开始合成新闻视频...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        print(f"[视频] 新闻视频合成失败:\n{result.stderr[-500:]}")
        # 降级: 用简单 concat
        return _compose_news_simple(audio_path, srt_path, image_paths, segments, output_path, duration)

    print(f"[视频] 新闻视频合成完成: {output_path}")
    return output_path


def _compose_news_simple(
    audio_path: str,
    srt_path: str,
    image_paths: list[str],
    segments: list[dict],
    output_path: str,
    duration: float,
) -> str:
    """简化版新闻视频（降级方案）"""
    n_images = len(image_paths)
    segment_duration = duration / max(n_images, 1)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for img in image_paths:
            if img and os.path.exists(img):
                f.write(f"file '{os.path.abspath(img)}'\n")
                f.write(f"duration {segment_duration:.2f}\n")
        if image_paths:
            last = [p for p in image_paths if p and os.path.exists(p)]
            if last:
                f.write(f"file '{os.path.abspath(last[-1])}'\n")

    vf_parts = [
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={VIDEO_BG_COLOR}"
    ]

    if srt_path and os.path.exists(srt_path):
        ass_path = srt_path.replace(".srt", ".ass")
        _srt_to_ass(srt_path, ass_path)
        if os.path.exists(ass_path):
            vf_parts.append(f"ass='{ass_path}'")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_path,
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    try:
        os.remove(concat_file)
    except Exception:
        pass

    if result.returncode != 0:
        print(f"[视频] 简化新闻视频也失败: {result.stderr[-300:]}")
        return compose_video(audio_path, srt_path, output_path, duration=duration)

    print(f"[视频] 简化新闻视频合成完成: {output_path}")
    return output_path


# ============================================================
# 原有兼容接口
# ============================================================

def compose_video(
    audio_path: str,
    srt_path: str,
    output_path: str,
    title: str = "",
    bg_image: str = None,
    duration: float = None,
) -> str:
    """
    合成最终视频（兼容旧接口）
    - 音频作为主时长参考
    - 深色背景 + 标题 + 字幕
    - 输出横屏 1920x1080 MP4
    """
    if duration is None:
        duration = _get_duration(audio_path)

    filters = []

    # 背景层
    if bg_image and os.path.exists(bg_image):
        filters.append(
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={VIDEO_BG_COLOR},"
            f"setsar=1[bg]"
        )
    else:
        filters.append(
            f"color=c={VIDEO_BG_COLOR}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}:r={VIDEO_FPS},"
            f"format=yuv420p[bg]"
        )

    # 标题层
    if title:
        safe_title = _escape_ffmpeg_text(title[:20])
        filters.append(
            f"[bg]drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:"
            f"text='{safe_title}':"
            f"fontcolor=white:fontsize=72:"
            f"x=(w-text_w)/2:y=400:"
            f"borderw=3:bordercolor=black[bg_title]"
        )
        last_label = "bg_title"
    else:
        last_label = "bg"

    # 字幕层
    if srt_path and os.path.exists(srt_path):
        ass_path = srt_path.replace(".srt", ".ass")
        _srt_to_ass(srt_path, ass_path)

        if os.path.exists(ass_path):
            filters.append(f"[{last_label}]ass='{ass_path}'[v]")
        else:
            filters.append(
                f"[{last_label}]subtitles='{srt_path}':"
                f"force_style='FontName=Noto Sans CJK SC,"
                f"FontSize={SUBTITLE_FONTSIZE},"
                f"PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,"
                f"Outline={SUBTITLE_OUTLINE_WIDTH},"
                f"Alignment=2,"
                f"MarginV={VIDEO_HEIGHT - SUBTITLE_POSITION_Y}'[v]"
            )
        last_label = "v"

    filter_complex = ";\n".join(filters)

    cmd = ["ffmpeg", "-y"]
    if bg_image and os.path.exists(bg_image):
        cmd.extend(["-loop", "1", "-i", bg_image])
    else:
        cmd.extend(["-f", "lavfi", "-i", f"color=c={VIDEO_BG_COLOR}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}:r={VIDEO_FPS}"])

    cmd.extend(["-i", audio_path])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        output_path,
    ])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"[视频] 开始合成: {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"[视频] FFmpeg 错误:\n{result.stderr[-500:]}")
        return _compose_simple(audio_path, srt_path, output_path, duration)

    print(f"[视频] 合成完成: {output_path}")
    return output_path


def _compose_simple(audio_path: str, srt_path: str, output_path: str, duration: float) -> str:
    """简化版合成（降级方案）"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c={VIDEO_BG_COLOR}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}:r={VIDEO_FPS}",
        "-i", audio_path,
    ]

    if srt_path and os.path.exists(srt_path):
        cmd.extend([
            "-vf", f"subtitles='{srt_path}':force_style='FontName=Noto Sans CJK SC,FontSize={SUBTITLE_FONTSIZE},PrimaryColour=&H00FFFFFF,Outline=2,Alignment=2'",
        ])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        output_path,
    ])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"[视频] 简化合成也失败: {result.stderr[-300:]}")
        raise RuntimeError("视频合成失败")

    print(f"[视频] 简化合成完成: {output_path}")
    return output_path


def compose_slideshow_video(
    audio_path: str,
    srt_path: str,
    image_paths: list[str],
    output_path: str,
    title: str = "",
    duration: float = None,
) -> str:
    """
    用图片幻灯片 + Ken Burns 效果合成视频（兼容旧接口）
    """
    if duration is None:
        duration = _get_duration(audio_path)

    if not image_paths:
        print("[视频] 无图片，降级到纯色背景")
        return compose_video(audio_path, srt_path, output_path, title, duration=duration)

    n_images = len(image_paths)
    segment_duration = duration / n_images

    print(f"[视频] 幻灯片模式: {n_images} 张图片, 每张 {segment_duration:.1f}s")

    import random
    random.seed(42)

    kb_patterns = [
        (1.0, 1.15, "0", "0", "-100", "-50"),
        (1.15, 1.0, "-100", "-50", "0", "0"),
        (1.0, 1.12, "-50", "0", "50", "-30"),
        (1.12, 1.0, "50", "-30", "-50", "0"),
        (1.0, 1.1, "0", "-30", "0", "30"),
    ]

    inputs = []
    filter_parts = []

    for i, img_path in enumerate(image_paths):
        inputs.extend(["-loop", "1", "-t", f"{segment_duration:.2f}", "-i", img_path])

        pattern = kb_patterns[i % len(kb_patterns)]
        s_start, s_end, x1, y1, x2, y2 = pattern

        filter_parts.append(
            f"[{i}:v]scale={VIDEO_WIDTH + 200}:{VIDEO_HEIGHT + 200},"
            f"zoompan=z='if(eq(on,1),{s_start},{s_end})':"
            f"x='iw/2-(iw/zoom/2)+({x2}-{x1})*on/{segment_duration}/{VIDEO_FPS}':"
            f"y='ih/2-(ih/zoom/2)+({y2}-{y1})*on/{segment_duration}/{VIDEO_FPS}':"
            f"d={int(segment_duration * VIDEO_FPS)}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:"
            f"fps={VIDEO_FPS},"
            f"setsar=1[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(n_images))
    filter_parts.append(f"{concat_inputs}concat=n={n_images}:v=1:a=0[vconcat]")

    if title:
        safe_title = _escape_ffmpeg_text(title[:20])
        filter_parts.append(
            f"[vconcat]drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:"
            f"text='{safe_title}':"
            f"fontcolor=white:fontsize=60:"
            f"x=(w-text_w)/2:y=120:"
            f"borderw=3:bordercolor=black@0.7[vtitle]"
        )
        last_label = "vtitle"
    else:
        last_label = "vconcat"

    if srt_path and os.path.exists(srt_path):
        ass_path = srt_path.replace(".srt", ".ass")
        _srt_to_ass(srt_path, ass_path)
        if os.path.exists(ass_path):
            filter_parts.append(f"[{last_label}]ass='{ass_path}'[v]")
            last_label = "v"

    filter_complex = ";\n".join(filter_parts)

    inputs.extend(["-i", audio_path])
    audio_idx = n_images

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        output_path,
    ]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"[视频] 开始合成幻灯片视频...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"[视频] 幻灯片合成失败:\n{result.stderr[-500:]}")
        return _compose_slideshow_simple(audio_path, srt_path, image_paths, output_path, duration)

    print(f"[视频] 幻灯片视频合成完成: {output_path}")
    return output_path


def _compose_slideshow_simple(
    audio_path: str,
    srt_path: str,
    image_paths: list[str],
    output_path: str,
    duration: float,
) -> str:
    """简化版幻灯片（降级方案）"""
    n_images = len(image_paths)
    segment_duration = duration / n_images

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for img in image_paths:
            f.write(f"file '{os.path.abspath(img)}'\n")
            f.write(f"duration {segment_duration:.2f}\n")
        f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_path,
    ]

    vf_parts = [f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2"]

    if srt_path and os.path.exists(srt_path):
        ass_path = srt_path.replace(".srt", ".ass")
        _srt_to_ass(srt_path, ass_path)
        if os.path.exists(ass_path):
            vf_parts.append(f"ass='{ass_path}'")

    cmd.extend([
        "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    try:
        os.remove(concat_file)
    except Exception:
        pass

    if result.returncode != 0:
        print(f"[视频] 简化幻灯片也失败: {result.stderr[-300:]}")
        return compose_video(audio_path, srt_path, output_path, duration=duration)

    print(f"[视频] 简化幻灯片合成完成: {output_path}")
    return output_path


# ============================================================
# 工具函数
# ============================================================

def _split_text(text: str, max_chars_per_line: int = 16) -> list[str]:
    """智能断句"""
    raw_splits = re.split(r'([。！？；，、.!,;])', text)

    segments = []
    current = ""

    for part in raw_splits:
        if not part.strip():
            continue

        if re.match(r'^[。！？；，、.!,;]$', part):
            current += part
            if len(current) >= max_chars_per_line:
                segments.append(current)
                current = ""
            continue

        while len(part) > max_chars_per_line:
            if current:
                segments.append(current)
                current = ""
            segments.append(part[:max_chars_per_line])
            part = part[max_chars_per_line:]

        if len(current) + len(part) > max_chars_per_line and current:
            segments.append(current)
            current = part
        else:
            current += part

    if current.strip():
        segments.append(current)

    return [s for s in segments if s.strip()]


def _format_time(seconds: float) -> str:
    """秒 -> SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _srt_to_ass(srt_path: str, ass_path: str):
    """SRT 转 ASS（带样式）"""
    ass_header = f"""[Script Info]
Title: AI News
ScriptType: v4.00+
PlayResX: {VIDEO_WIDTH}
PlayResY: {VIDEO_HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,{SUBTITLE_FONTSIZE},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{SUBTITLE_OUTLINE_WIDTH},1,2,30,30,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    events = []
    blocks = re.split(r'\n\n+', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            text = ' '.join(lines[2:])
            match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_line)
            if match:
                g = match.groups()
                start = f"{g[0]}:{g[1]}:{g[2]}.{g[3][:2]}"
                end = f"{g[4]}:{g[5]}:{g[6]}.{g[7][:2]}"
                events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write('\n'.join(events))
        f.write('\n')


def _get_duration(path: str) -> float:
    """获取媒体文件时长"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 30.0


def _escape_ffmpeg_text(text: str) -> str:
    """转义 FFmpeg drawtext 特殊字符"""
    for ch in ["\\", "'", ":", "%", "[", "]"]:
        text = text.replace(ch, f"\\{ch}")
    return text


if __name__ == "__main__":
    test_narration = "据报道，OpenAI 计划在今年夏季发布 GPT-5。与此同时，苹果 Vision Pro 2 也曝光了。"
    generate_subtitles(test_narration, 30.0, "output/test.srt")
