"""
AI 短视频流水线 - 动画板书生成器（MoviePy 版）
参考黑鸦Heya风格：深蓝紫渐变 + 极简排版 + 数字黄色高亮 + 大量留白
"""
import os
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoClip, ImageClip, ColorClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip, VideoFileClip
)
from config import VIDEO_WIDTH, VIDEO_HEIGHT

W, H = VIDEO_WIDTH, VIDEO_HEIGHT  # 1920x1080
FPS = 30

# ──────────────────────────────────────────────
# 颜色方案（黑鸦Heya风格）
# ──────────────────────────────────────────────
BG_TOP = (18, 18, 42)       # 深蓝紫渐变 - 顶部
BG_BOTTOM = (10, 10, 25)    # 深蓝紫渐变 - 底部
GRID_COLOR = (30, 30, 60, 25)  # 极淡网格线（几乎看不见但有质感）

TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (180, 180, 190)     # 辅助文字
TEXT_DIM = (100, 100, 120)      # 水印/装饰
TEXT_YELLOW = (255, 215, 0)     # 数字高亮 - 明黄色
TEXT_RED = (255, 80, 80)        # 品牌强调色 - 红
TEXT_ORANGE = (255, 160, 60)    # 品牌强调色 - 橙
TEXT_LOGO = (80, 80, 110)       # 水印色

# 品牌颜色映射
BRAND_COLORS = {
    "谷歌": (66, 133, 244), "Google": (66, 133, 244), "Gemini": (66, 133, 244),
    "OpenAI": (255, 255, 255), "ChatGPT": (255, 255, 255), "GPT": (255, 255, 255),
    "DeepSeek": (100, 200, 255),
    "Anthropic": (200, 160, 255), "Claude": (200, 160, 255),
    "百度": (255, 80, 80), "文心": (255, 80, 80),
    "阿里": (255, 150, 50), "通义": (255, 150, 50),
    "字节": (80, 200, 255), "豆包": (80, 200, 255),
    "Step": (255, 140, 50), "StepFun": (255, 140, 50),
    "商汤": (100, 180, 255),
    "Meta": (66, 133, 244), "Llama": (66, 133, 244),
}

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def _make_bg_frame():
    """生成深蓝紫渐变背景 + 极淡网格线"""
    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img, "RGBA")
    # 渐变：从上到下 BG_TOP → BG_BOTTOM
    for y in range(H):
        ratio = y / H
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    # 极淡网格线（间距80px，几乎透明）
    grid_w = 80
    for x in range(0, W, grid_w):
        draw.line([(x, 0), (x, H)], fill=GRID_COLOR, width=1)
    for y in range(0, H, grid_w):
        draw.line([(0, y), (W, y)], fill=GRID_COLOR, width=1)
    return np.array(img)


def _make_bg_frame_custom(bg_color1, bg_color2):
    """使用自定义颜色生成渐变背景"""
    img = Image.new("RGB", (W, H), bg_color1)
    draw = ImageDraw.Draw(img, "RGBA")
    for y in range(H):
        ratio = y / H
        r = int(bg_color1[0] * (1 - ratio) + bg_color2[0] * ratio)
        g = int(bg_color1[1] * (1 - ratio) + bg_color2[1] * ratio)
        b = int(bg_color1[2] * (1 - ratio) + bg_color2[2] * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    # 极淡网格
    grid_w = 80
    grid_c = (max(0, bg_color2[0] + 15), max(0, bg_color2[1] + 15), max(0, bg_color2[2] + 20), 20)
    for x in range(0, W, grid_w):
        draw.line([(x, 0), (x, H)], fill=grid_c, width=1)
    for y in range(0, H, grid_w):
        draw.line([(0, y), (W, y)], fill=grid_c, width=1)
    return np.array(img)


def _get_brand_color(text):
    """根据文本中的品牌名返回对应颜色"""
    for brand, color in BRAND_COLORS.items():
        if brand in text:
            return color
    return None


def _make_text_image(text, font_path, font_size, color, max_width=None, line_spacing=1.3):
    """渲染文字为 RGBA numpy 数组"""
    font = ImageFont.truetype(font_path, font_size)

    if max_width:
        lines = _wrap_text(text, font, max_width)
        text = "\n".join(lines)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=int(font_size * (line_spacing - 1)))
    tw = bbox[2] - bbox[0] + 30
    th = bbox[3] - bbox[1] + 30

    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.multiline_text((15, 15), text, font=font, fill=(*color, 255), spacing=int(font_size * (line_spacing - 1)))
    return np.array(img)


def _wrap_text(text, font, max_width):
    """自动换行"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _split_headline_details(headline, narration):
    """拆分主标题 + 详情要点"""
    main_title = headline[:35] if len(headline) > 35 else headline
    sentences = re.split(r'[。！？；\n]', narration)
    details = []
    for s in sentences:
        s = s.strip()
        if 6 <= len(s) <= 50:
            details.append(s)
        elif len(s) > 50:
            cut = s[:48].rstrip('，、,')
            details.append(cut + '……')
    return main_title, details[:3]  # 黑鸦风格：最多3条要点


def _find_highlights(narration):
    """提取关键数字"""
    highlights = []
    patterns = [
        r'\d+[\d,.]*\s*(?:万亿|亿|万)\s*(?:美元|元|人民币)?',
        r'\$\s*\d+[\d,.]*\s*(?:billion|million|trillion)?',
        r'\d+[\d,.]*%',
        r'\d+[\d,.]*\s*(?:倍|GB|TB|MB)',
    ]
    for pat in patterns:
        matches = re.findall(pat, narration)
        highlights.extend(matches)
    return highlights[:2]  # 最多2个数字高亮


def make_title_card(
    segment: dict,
    output_path: str,
    audio_duration: float = None,
    bg_color1=None,
    bg_color2=None,
    logo_text: str = "AI 日报",
) -> str:
    """生成标题卡/结尾卡（居中大字）— 黑鸦Heya风格"""
    headline = segment.get("headline", "AI 早报")
    subline = segment.get("subline", "")

    duration = audio_duration or segment.get("duration", 4.0)
    fade_in, fade_out = 0.5, 0.5

    # 背景（渐变 + 极淡网格）
    if bg_color1 and bg_color2:
        bg_frame = _make_bg_frame_custom(bg_color1, bg_color2)
    else:
        bg_frame = _make_bg_frame()
    bg_clip = ImageClip(bg_frame).with_duration(duration)

    # 标题（居中，大字，白色）
    title_img = _make_text_image(headline, FONT_BOLD, 120, TEXT_WHITE, max_width=W - 300)
    title_clip = (
        ImageClip(title_img)
        .with_duration(duration - fade_in - fade_out)
        .with_start(fade_in)
        .with_position(("center", H // 2 - 60))
    )

    text_clips = [title_clip]

    # 副标题（居中，灰色，下方）
    if subline:
        sub_img = _make_text_image(subline, FONT_REGULAR, 36, TEXT_GRAY, max_width=W - 300)
        sub_clip = (
            ImageClip(sub_img)
            .with_duration(duration - fade_in - fade_out)
            .with_start(fade_in + 0.3)
            .with_position(("center", H // 2 + 80))
        )
        text_clips.append(sub_clip)

    # 水印（右下角）
    wm_img = _make_text_image(logo_text, FONT_REGULAR, 24, TEXT_DIM)
    wm_clip = (
        ImageClip(wm_img)
        .with_duration(duration)
        .with_position((W - wm_img.shape[1] - 40, H - wm_img.shape[0] - 30))
        .with_opacity(0.5)
    )
    text_clips.append(wm_clip)

    all_clips = [bg_clip] + text_clips
    final = CompositeVideoClip(all_clips, size=(W, H))

    try:
        from moviepy.video.fx import FadeIn, FadeOut
        final = final.with_effects([FadeIn(fade_in), FadeOut(fade_out)])
    except:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.write_videofile(
        output_path, fps=FPS, codec="libx264", preset="fast",
        ffmpeg_params=["-crf", "23"], audio=False, logger=None,
    )
    print(f"[标题卡] 生成完成: {output_path} ({duration:.1f}s)")
    return output_path


def make_animated_board(
    segment: dict,
    output_path: str,
    logo_text: str = "AI 日报",
    index: int = 0,
    audio_duration: float = None,
    bg_color1=None,
    bg_color2=None,
) -> str:
    """
    生成一条带动画效果的板书视频 — 黑鸦Heya风格

    设计要点：
    - 深蓝紫渐变背景 + 极淡网格
    - 数字黄色高亮，品牌色匹配
    - 大量留白，极简排版
    - 右下角水印
    - 文字逐行淡入
    """
    headline = segment.get("headline", "")
    narration = segment.get("narration", "")
    seg_type = segment.get("type", "news")
    category = segment.get("category", "")

    # 标题卡/结尾卡走专用函数
    if seg_type in ("title", "ending"):
        return make_title_card(segment, output_path, audio_duration, bg_color1, bg_color2, logo_text)

    # 优先使用 segment 中显式提供的 details
    if "details" in segment and segment["details"]:
        main_title = headline
        details = segment["details"][:3]  # 最多3条
    else:
        main_title, details = _split_headline_details(headline, narration)

    # 优先使用 segment 中显式提供的 highlight_nums
    if "highlight_nums" in segment and segment["highlight_nums"]:
        highlights = segment["highlight_nums"][:2]  # 最多2个
    else:
        highlights = _find_highlights(narration)

    # --- 时间轴 ---
    fade_in = 0.4
    fade_out = 0.4
    title_delay = 0.3
    line_interval = 0.6     # 每行间隔（稍慢，呼吸感）
    hold_time = 1.5

    num_items = 1 + len(highlights) + len(details)
    content_end = title_delay + (num_items - 1) * line_interval + hold_time
    total_duration = content_end + fade_in + fade_out

    if audio_duration and audio_duration > total_duration:
        total_duration = audio_duration
        hold_time = total_duration - fade_in - fade_out - title_delay - (num_items - 1) * line_interval

    # --- 背景 ---
    if bg_color1 and bg_color2:
        bg_frame = _make_bg_frame_custom(bg_color1, bg_color2)
    else:
        bg_frame = _make_bg_frame()
    bg_clip = ImageClip(bg_frame).with_duration(total_duration)

    # 右下角水印（"AI 日报"，低调）
    wm_img = _make_text_image(logo_text, FONT_REGULAR, 24, TEXT_DIM)
    wm_clip = (
        ImageClip(wm_img)
        .with_duration(total_duration)
        .with_position((W - wm_img.shape[1] - 40, H - wm_img.shape[0] - 30))
        .with_opacity(0.5)
    )

    # --- 文字动画层 ---
    text_clips = []
    y_cursor = 160        # 顶部留白更多
    x_left = 180          # 左侧留白更多

    # 检测品牌色（用于标题中的品牌词）
    brand_color = _get_brand_color(main_title)

    # 1. 主标题（大字，白色/品牌色）
    title_color = brand_color if brand_color else TEXT_WHITE
    title_img = _make_text_image(main_title, FONT_BOLD, 68, title_color, max_width=W - 360)
    title_h = title_img.shape[0]
    title_start = fade_in + title_delay
    title_dur = total_duration - title_start - fade_out

    title_clip = (
        ImageClip(title_img)
        .with_duration(title_dur)
        .with_start(title_start)
        .with_position((x_left, y_cursor))
    )
    text_clips.append(title_clip)
    y_cursor += title_h + 50  # 更多留白

    # 2. 关键数字（明黄色大字，独立成行）
    for i, hl in enumerate(highlights):
        hl_img = _make_text_image(hl, FONT_BOLD, 56, TEXT_YELLOW, max_width=W - 360)
        hl_h = hl_img.shape[0]
        hl_start = fade_in + title_delay + (i + 1) * line_interval
        hl_dur = total_duration - hl_start - fade_out

        hl_clip = (
            ImageClip(hl_img)
            .with_duration(hl_dur)
            .with_start(hl_start)
            .with_position((x_left, y_cursor))
        )
        text_clips.append(hl_clip)
        y_cursor += hl_h + 30

    # 3. 详情要点（灰色，小字，最多3条）
    for i, detail in enumerate(details):
        detail_img = _make_text_image(detail, FONT_REGULAR, 32, TEXT_GRAY, max_width=W - 360)
        detail_h = detail_img.shape[0]
        detail_start = fade_in + title_delay + (1 + len(highlights) + i) * line_interval
        detail_dur = total_duration - detail_start - fade_out

        detail_clip = (
            ImageClip(detail_img)
            .with_duration(detail_dur)
            .with_start(detail_start)
            .with_position((x_left, y_cursor))
        )
        text_clips.append(detail_clip)
        y_cursor += detail_h + 20

    # --- 合成 ---
    all_clips = [bg_clip, wm_clip] + text_clips
    final = CompositeVideoClip(all_clips, size=(W, H))

    # 整体淡入淡出
    try:
        from moviepy.video.fx import FadeIn, FadeOut
        final = final.with_effects([FadeIn(fade_in), FadeOut(fade_out)])
    except Exception:
        print("[动画板书] 警告：淡入淡出效果不可用，使用默认输出")
        pass

    # --- 输出 ---
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        audio=False,
        logger=None,
    )

    print(f"[动画板书] 生成完成: {output_path} ({total_duration:.1f}s)")
    return output_path


def make_animated_board_with_audio(
    segment: dict,
    audio_path: str,
    output_path: str,
    logo_text: str = "AI 日报",
    index: int = 0,
    bg_color1=None,
    bg_color2=None,
) -> str:
    """生成带动画+音频的板书视频"""
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    temp_video = output_path.replace(".mp4", "_noaudio.mp4")
    make_animated_board(segment, temp_video, logo_text, index, audio_duration=duration,
                        bg_color1=bg_color1, bg_color2=bg_color2)

    video = VideoFileClip(temp_video).with_duration(duration)
    video = video.with_audio(audio)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        audio_codec="aac",
        logger=None,
    )

    if os.path.exists(temp_video):
        os.remove(temp_video)

    print(f"[动画板书+音频] 生成完成: {output_path}")
    return output_path


# === 测试 ===
if __name__ == "__main__":
    test_segment = {
        "headline": "OpenAI 推出 GPT-5.5 Instant 模型",
        "narration": "OpenAI 发布了全新的 GPT-5.5 Instant 模型，速度提升 40%，价格降低 25%。ChatGPT 同步增强记忆功能，支持跨对话上下文保留。这是 OpenAI 今年最重要的更新之一。"
    }
    out = make_animated_board(
        test_segment,
        "/tmp/test_anim_board.mp4",
        logo_text="AI 日报",
        index=0,
    )
    print(f"测试视频: {out}")
