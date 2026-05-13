"""
AI 短视频流水线 - 板书风格合成模块
参考黑鸦Heya风格：深色网格背景 + 左侧照片 + 右侧标题/详情/红色高亮数字
"""
import os
import subprocess
import re
from config import VIDEO_WIDTH, VIDEO_HEIGHT, FONTS_DIR

# Board color scheme
BOARD_BG_COLOR = "0x0a1628"       # 深蓝背景
BOARD_GRID_COLOR = "0x1a3050@0.3"  # 网格线
BOARD_DIVIDER_COLOR = "0x3a6090@0.6"  # 分割线
TEXT_WHITE = "white"
TEXT_GRAY = "0xcccccc"
TEXT_RED = "0xff4444"              # 关键数字高亮
TEXT_ORANGE = "0xff8844"           # 次要高亮
TEXT_LOGO = "0x5a8ab8"            # Logo 颜色
TEXT_SUBTITLE = "0xaaaaaa"        # 底部字幕

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def _escape_ffmpeg_text(text: str) -> str:
    """转义 FFmpeg drawtext 特殊字符"""
    for ch in ["\\", "'", ":", "%", "[", "]"]:
        text = text.replace(ch, f"\\{ch}")
    return text


def _find_highlights(narration: str) -> list[str]:
    """从旁白中提取关键数字/金额作为高亮"""
    highlights = []
    # 匹配金额: X亿美元, X亿元, X万亿美元, $X billion 等
    patterns = [
        r'\d+[\d,.]*\s*(?:万亿|亿|万)\s*(?:美元|元|人民币)?',
        r'\$\s*\d+[\d,.]*\s*(?:billion|million|trillion)?',
        r'\d+[\d,.]*\s*(?:billion|million|trillion)\s*(?:dollars|USD)?',
        r'\d+[\d,.]*%',
    ]
    for pat in patterns:
        matches = re.findall(pat, narration)
        highlights.extend(matches)
    return highlights[:3]  # 最多3个高亮


def _split_headline_details(headline: str, narration: str) -> tuple[str, list[str]]:
    """
    拆分：主标题（短）+ 详情要点（列表）
    主标题取 headline，详情从 narration 中提取要点
    """
    main_title = headline[:25] if len(headline) > 25 else headline

    # 从 narration 中按句号/逗号拆分要点
    sentences = re.split(r'[。！？；\n]', narration)
    details = []
    for s in sentences:
        s = s.strip()
        if len(s) >= 6 and len(s) <= 40:
            details.append(s)
        elif len(s) > 40:
            # 截断到合适长度
            cut = s[:38].rstrip('，、,')
            details.append(cut + '……')
    return main_title, details[:4]  # 最多4条详情


def compose_board_image(
    segment: dict,
    photo_path: str,
    output_path: str,
    logo_text: str = "HEYA AI 早报",
    index: int = 0,
) -> str:
    """
    合成一张板书风格的新闻配图

    参数:
        segment: 脚本 segment，含 headline, narration, image_query
        photo_path: Seedream 生成的照片路径（左侧展示）
        output_path: 输出图片路径
        logo_text: 右上角 logo 文字
        index: 新闻序号

    返回: 输出图片路径
    """
    headline = segment.get("headline", "")
    narration = segment.get("narration", "")

    main_title, details = _split_headline_details(headline, narration)
    highlights = _find_highlights(narration)

    W, H = VIDEO_WIDTH, VIDEO_HEIGHT

    # === 构建 FFmpeg 滤镜 ===
    filters = []

    # 1. 背景：深蓝底色 + 网格
    filters.append(
        f"color=c={BOARD_BG_COLOR}:s={W}x{H}:d=1:r=1,"
        f"drawgrid=w=60:h=60:t=1:c={BOARD_GRID_COLOR}"
    )

    # 2. 左侧照片区域（如果有照片）
    if photo_path and os.path.exists(photo_path):
        # 读取照片并缩放到左侧区域
        filters[0] += (
            f"[bg];"
            f"[1:v]scale=680:1000:force_original_aspect_ratio=decrease,"
            f"pad=680:1000:(ow-iw)/2:(oh-ih)/2:color={BOARD_BG_COLOR},"
            f"format=yuva420p,colorchannelmixer=aa=0.85[photo];"
            f"[bg][photo]overlay=10:40[bg_photo]"
        )
        last_label = "bg_photo"
    else:
        # 无照片：左侧画一个深色区域
        filters[0] += (
            f",drawbox=x=0:y=0:w=700:h=1080:c=0x000000@0.4:t=fill"
        )
        last_label = None

    # 3. 分割线
    divider_filter = f"drawbox=x=700:y=50:w=3:h=980:c={BOARD_DIVIDER_COLOR}:t=fill"

    # 4. 右上角 Logo
    safe_logo = _escape_ffmpeg_text(logo_text)
    logo_filter = f"drawtext=text='{safe_logo}':fontfile={FONT_BOLD}:fontsize=36:fontcolor={TEXT_LOGO}:x=1700:y=30"

    # 5. 主标题（白色大字）
    safe_title = _escape_ffmpeg_text(main_title)
    title_filter = f"drawtext=text='{safe_title}':fontfile={FONT_BOLD}:fontsize=56:fontcolor={TEXT_WHITE}:x=750:y=100"

    # 6. 关键数字高亮（红色）
    highlight_filters = []
    y_offset = 190
    for i, hl in enumerate(highlights[:3]):
        safe_hl = _escape_ffmpeg_text(hl)
        color = TEXT_RED if i == 0 else TEXT_ORANGE
        highlight_filters.append(
            f"drawtext=text='{safe_hl}':fontfile={FONT_BOLD}:fontsize=52:fontcolor={color}:x=750:y={y_offset}"
        )
        # 下划线
        highlight_filters.append(
            f"drawbox=x=750:y={y_offset + 50}:w={len(hl) * 36}:h=3:c={color}@0.8:t=fill"
        )
        y_offset += 80

    # 7. 详情要点（灰色）
    if not highlight_filters:
        y_offset = 190
    detail_filters = []
    for i, detail in enumerate(details[:4]):
        safe_detail = _escape_ffmpeg_text(detail)
        dy = y_offset + i * 60
        detail_filters.append(
            f"drawtext=text='{safe_detail}':fontfile={FONT_REGULAR}:fontsize=32:fontcolor={TEXT_GRAY}:x=750:y={dy}"
        )

    # 8. 底部字幕
    subtitle = segment.get("headline", "")
    safe_sub = _escape_ffmpeg_text(subtitle[:50])
    sub_filter = f"drawtext=text='{safe_sub}':fontfile={FONT_REGULAR}:fontsize=32:fontcolor={TEXT_SUBTITLE}:x=(w-text_w)/2:y=1000"

    # 9. 序号标记
    num_filter = f"drawtext=text='{index + 1:02d}':fontfile={FONT_BOLD}:fontsize=120:fontcolor=0x1a3050@0.3:x=1700:y=900"

    # === 组合所有滤镜 ===
    # 基础层
    if last_label:
        base = f"[{last_label}]"
    else:
        base = ""

    all_draws = [divider_filter, logo_filter, title_filter]
    all_draws.extend(highlight_filters)
    all_draws.extend(detail_filters)
    all_draws.extend([sub_filter, num_filter])

    full_filter = filters[0] + ";" + base + ",".join(all_draws) + "[v]"

    # === 执行 FFmpeg ===
    cmd = ["ffmpeg", "-y"]

    if photo_path and os.path.exists(photo_path):
        cmd.extend(["-f", "lavfi", "-i", f"color=c={BOARD_BG_COLOR}:s={W}x{H}:d=1:r=1"])
        cmd.extend(["-i", photo_path])
    else:
        cmd.extend(["-f", "lavfi", "-i", f"color=c={BOARD_BG_COLOR}:s={W}x{H}:d=1:r=1"])

    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[v]",
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        print(f"[板书] 合成失败: {result.stderr[-200:]}")
        # 降级：用简化版
        return _compose_board_simple(segment, photo_path, output_path, index)

    print(f"[板书] 合成完成: {output_path}")
    return output_path


def _compose_board_simple(
    segment: dict,
    photo_path: str,
    output_path: str,
    index: int = 0,
) -> str:
    """简化版板书（降级方案）"""
    headline = segment.get("headline", "")
    narration = segment.get("narration", "")
    main_title, details = _split_headline_details(headline, narration)
    highlights = _find_highlights(narration)

    W, H = VIDEO_WIDTH, VIDEO_HEIGHT

    # 简化：纯色背景 + 文字
    safe_title = _escape_ffmpeg_text(main_title)
    vf = (
        f"color=c={BOARD_BG_COLOR}:s={W}x{H}:d=1:r=1,"
        f"drawgrid=w=60:h=60:t=1:c={BOARD_GRID_COLOR},"
        f"drawbox=x=700:y=50:w=3:h=980:c={BOARD_DIVIDER_COLOR}:t=fill,"
        f"drawtext=text='{safe_title}':fontfile={FONT_BOLD}:fontsize=56:fontcolor={TEXT_WHITE}:x=750:y=100"
    )

    # 高亮数字
    y = 200
    for hl in highlights[:2]:
        safe_hl = _escape_ffmpeg_text(hl)
        vf += f",drawtext=text='{safe_hl}':fontfile={FONT_BOLD}:fontsize=52:fontcolor={TEXT_RED}:x=750:y={y}"
        y += 80

    # 详情
    for detail in details[:3]:
        safe_d = _escape_ffmpeg_text(detail)
        vf += f",drawtext=text='{safe_d}':fontfile={FONT_REGULAR}:fontsize=32:fontcolor={TEXT_GRAY}:x=750:y={y}"
        y += 60

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BOARD_BG_COLOR}:s={W}x{H}:d=1:r=1",
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        print(f"[板书] 简化版也失败: {result.stderr[-200:]}")
        return ""

    print(f"[板书] 简化版合成完成: {output_path}")
    return output_path
