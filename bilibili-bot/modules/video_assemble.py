"""
视频合成模块 - 使用 FFmpeg 将片段、音频、字幕合成为成品视频
"""
import os
import json
import subprocess
from datetime import datetime


def get_video_duration(filepath: str) -> float:
    """获取视频时长(秒)"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def resize_clip(input_path: str, output_path: str, width=1080, height=1920) -> str:
    """调整片段尺寸 (统一为竖屏)"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
        return output_path
    except Exception as e:
        print(f"[合成] 调整尺寸失败: {e}")
        return input_path


def concat_clips(clip_paths: list[str], output_path: str) -> str:
    """拼接多个视频片段"""
    if not clip_paths:
        print("[合成] 无片段可拼接")
        return None

    if len(clip_paths) == 1:
        # 单片段直接复制
        subprocess.run(["cp", clip_paths[0], output_path], capture_output=True)
        return output_path

    # 创建 concat 列表文件
    list_file = "/tmp/concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[合成] 拼接完成: {output_path}")
            return output_path
        else:
            print(f"[合成] 拼接失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"[合成] 拼接异常: {e}")
        return None


def add_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """替换/添加音频轨"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[合成] 添加音频完成: {output_path}")
            return output_path
        else:
            print(f"[合成] 添加音频失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"[合成] 添加音频异常: {e}")
        return None


def add_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """烧录字幕到视频"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}:force_style='FontSize=22,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2,MarginV=60'",
        "-c:a", "copy",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[合成] 添加字幕完成: {output_path}")
            return output_path
        else:
            print(f"[合成] 添加字幕失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"[合成] 添加字幕异常: {e}")
        return None


def generate_srt(audio_files: list[dict], output_path: str) -> str:
    """根据音频信息生成 SRT 字幕文件"""
    srt_content = []
    current_time = 0.0

    for i, audio in enumerate(audio_files, 1):
        duration = audio.get("duration", 5.0)
        narration = audio.get("narration", "")

        start = format_srt_time(current_time)
        end = format_srt_time(current_time + duration)

        srt_content.append(f"{i}")
        srt_content.append(f"{start} --> {end}")
        srt_content.append(narration)
        srt_content.append("")

        current_time += duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))

    print(f"[字幕] 生成完成: {output_path}")
    return output_path


def format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def add_bgm(video_path: str, bgm_path: str, output_path: str, volume=0.15) -> str:
    """添加背景音乐 (低音量)"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[合成] 添加BGM完成: {output_path}")
            return output_path
        else:
            print(f"[合成] 添加BGM失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"[合成] 添加BGM异常: {e}")
        return None


def assemble_video(
    clip_paths: list[str],
    audio_files: list[dict],
    output_path: str,
    bgm_path: str = None,
    add_srt: bool = True,
) -> str:
    """完整视频合成流程
    1. 拼接视频片段
    2. 添加旁白音频
    3. 生成并烧录字幕
    4. (可选) 添加BGM
    """
    output_dir = os.path.dirname(output_path)
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Step 1: 拼接片段
    print("\n[合成] Step 1: 拼接视频片段...")
    concat_path = os.path.join(temp_dir, "concat.mp4")
    result = concat_clips(clip_paths, concat_path)
    if not result:
        print("[合成] 拼接失败，中止")
        return None

    # Step 2: 添加旁白音频
    print("[合成] Step 2: 添加旁白音频...")
    audio_path = os.path.join(temp_dir, "full_audio.mp3")

    # 合并所有音频
    if len(audio_files) > 1:
        audio_list = os.path.join(temp_dir, "audio_list.txt")
        with open(audio_list, "w") as f:
            for af in audio_files:
                f.write(f"file '{af['audio_path']}'\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", audio_list, "-c", "copy", audio_path
        ], capture_output=True, timeout=60)
    elif len(audio_files) == 1:
        subprocess.run(["cp", audio_files[0]["audio_path"], audio_path], capture_output=True)
    else:
        print("[合成] 无音频，跳过")
        return concat_path

    with_audio_path = os.path.join(temp_dir, "with_audio.mp4")
    result = add_audio(concat_path, audio_path, with_audio_path)
    if not result:
        return concat_path

    # Step 3: 字幕
    current_video = with_audio_path
    if add_srt:
        print("[合成] Step 3: 添加字幕...")
        srt_path = os.path.join(temp_dir, "subtitles.srt")
        generate_srt(audio_files, srt_path)

        with_srt_path = os.path.join(temp_dir, "with_srt.mp4")
        result = add_subtitles(current_video, srt_path, with_srt_path)
        if result:
            current_video = result

    # Step 4: BGM (可选)
    if bgm_path and os.path.exists(bgm_path):
        print("[合成] Step 4: 添加BGM...")
        with_bgm_path = os.path.join(temp_dir, "with_bgm.mp4")
        result = add_bgm(current_video, bgm_path, with_bgm_path)
        if result:
            current_video = result

    # Step 5: 复制到最终输出
    subprocess.run(["cp", current_video, output_path], capture_output=True)

    # 清理临时文件
    # import shutil
    # shutil.rmtree(temp_dir, ignore_errors=True)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    duration = get_video_duration(output_path)
    print(f"\n[合成] ✅ 最终视频: {output_path}")
    print(f"[合成] 时长: {duration:.1f}秒, 大小: {file_size:.1f}MB")

    return output_path


if __name__ == "__main__":
    # 测试 SRT 生成
    test_audio = [
        {"scene_id": 1, "audio_path": "/tmp/test1.mp3", "duration": 5.0, "narration": "这是第一段"},
        {"scene_id": 2, "audio_path": "/tmp/test2.mp3", "duration": 4.0, "narration": "这是第二段"},
    ]
    generate_srt(test_audio, "/tmp/test.srt")
    with open("/tmp/test.srt") as f:
        print(f.read())
