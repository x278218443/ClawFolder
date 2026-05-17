#!/usr/bin/env python3
"""
动画板书 AI 早报 - 实时新闻版
基于 2026-05-09 抓取的实时 AI 新闻 (AIBase)
"""
import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from tts_engine import synthesize_speech
from board_maker_anim import make_animated_board, make_animated_board_with_audio, make_title_card
from image_fetcher import _generate_from_seedream, _enhance_prompt, _load_ark_key
from config import OUTPUT_DIR

W, H = 1920, 1080
FPS = 30

BG_COLORS = [
    ((20, 18, 42), (12, 10, 28)),   # 深蓝紫（默认）
    ((25, 18, 45), (15, 12, 30)),   # 偏紫
    ((18, 22, 48), (10, 14, 32)),   # 偏蓝
    ((28, 18, 40), (18, 12, 28)),   # 暖紫
    ((18, 25, 45), (10, 16, 30)),   # 冷蓝
    ((22, 18, 50), (14, 12, 35)),   # 深紫
    ((18, 28, 42), (10, 18, 28)),   # 青蓝
    ((25, 20, 48), (16, 14, 32)),   # 蓝紫
]

# === 用户精选版 AI 新闻 (2026-05-09) ===
NEWS_SEGMENTS = [
    {
        "id": 1,
        "type": "title",
        "headline": "AI 早报",
        "subline": "2026 年 5 月 9 日 星期六",
        "narration": "欢迎收看今天的 AI 早报。",
    },
    {
        "id": 2,
        "type": "news",
        "headline": "DeepSeek V4 Flash 推理引擎发布",
        "details": [
            "专为 Metal 平台打造的本地推理引擎",
            "支持百万 Token 上下文窗口",
            "MacBook 128GB 可跑 2-bit 量化，思维模式仅 1/5 耗时",
        ],
        "highlight_nums": ["100 万", "1/5"],
        "narration": "DeepSeek 发布 V4 Flash 本地推理引擎，专为 Metal 平台优化，支持百万 Token 上下文窗口。思维模式下处理复杂问题的耗时仅为其他模型的五分之一，MacBook 128GB 即可跑 2-bit 量化推理，本地大模型时代加速到来。",
    },
    {
        "id": 3,
        "type": "news",
        "headline": "OpenAI 发布三款实时语音模型",
        "details": [
            "GPT-Realtime-2 具备 GPT-5 级推理能力",
            "支持 70 种输入语言、13 种输出语言实时翻译",
            "语音输入 $32/百万 Token，输出 $64/百万 Token",
        ],
        "highlight_nums": ["GPT-5", "70 种"],
        "narration": "OpenAI 一口气发布三款实时语音模型。旗舰款 GPT-Realtime-2 是首个具备 GPT-5 级推理能力的语音模型，可边对话边进行复杂逻辑推理。GPT-Realtime-Translate 支持七十种语言实时同传，GPT-Realtime-Whisper 实现超低延迟流式转写。",
    },
    {
        "id": 4,
        "type": "news",
        "headline": "OpenAI Codex Chrome 扩展上线",
        "details": [
            "深度集成浏览器，可跨标签页获取上下文",
            "直接调用 DevTools 完成复杂开发任务",
            "周活跃用户突破 400 万，年初至今增长 8 倍",
        ],
        "highlight_nums": ["400 万", "8 倍"],
        "narration": "OpenAI 推出 Codex Chrome 浏览器扩展，深度集成浏览器环境，可跨标签页获取上下文并直接调用 DevTools。数据显示 Codex 周活跃用户已突破四百万，较年初增长八倍。",
    },
    {
        "id": 5,
        "type": "news",
        "headline": "OpenAI 发布 GPT-5.5-Cyber 安全预览版",
        "details": [
            "面向认证安全团队限量开放",
            "放宽安全限制以支持漏洞识别和恶意软件分析",
            "继 Anthropic Claude Mythos 之后的又一垂直领域模型",
        ],
        "highlight_nums": ["5.5", "限量"],
        "narration": "OpenAI 发布 GPT-5.5-Cyber 安全预览版，面向认证安全团队限量开放。该版本针对网络安全场景放宽内置限制，让授权团队更高效地执行漏洞识别、补丁验证和恶意软件分析，继 Anthropic Claude Mythos 之后，大厂纷纷布局安全垂直赛道。",
    },
    {
        "id": 6,
        "type": "news",
        "headline": "Anthropic Claude 深度集成 Microsoft 365",
        "details": [
            "覆盖 Excel、PowerPoint、Word 全家桶",
            "Outlook 邮件智能分类 + 自动回复草稿",
            "跨应用无缝切换，无需重复说明上下文",
        ],
        "highlight_nums": ["365"],
        "narration": "Anthropic 推出 Claude for Microsoft 365，深度集成 Excel、PowerPoint 和 Word。在 Outlook 中可自动分类邮件、识别哪些需要亲自回复，并生成回复草稿。跨应用协作无需重复说明工作背景，办公效率大幅提升。",
    },
    {
        "id": 7,
        "type": "news",
        "headline": "阿里通义 AI 眼镜 S1 重磅升级",
        "details": [
            "全球首个空间 3D 显示功能，双目立体成像",
            "新增主动服务能力，根据天气日程智能提醒",
            "本月上线打车、闪购等生活服务",
        ],
        "highlight_nums": ["3D", "首个"],
        "narration": "阿里通义 AI 眼镜 S1 重大升级，实现全球首个空间 3D 显示功能，采用双目立体成像技术让信息呈现更真实。新增主动服务能力，可根据天气和日程主动提醒，本月还将上线打车、闪购等生活服务。",
    },
    {
        "id": 8,
        "type": "news",
        "headline": "美团 AI 社交「米游」开启公测",
        "details": [
            "AI 原生社区，数字生命拥有独立身份和社交关系",
            "用户可体验「养虾」模式，AI 助手帮你赚钱交友",
            "互联网巨头 AI 策略从工具走向社区生态",
        ],
        "highlight_nums": ["公测"],
        "narration": "美团首个 AI 原生社区「米游」正式开启公测。在这个社区中，AI 数字生命拥有独立身份和社交关系，用户可以通过「养虾」模式体验 AI 助手帮你赚钱交友。这标志着互联网巨头的 AI 策略从单一工具向社区生态进化。",
    },
    {
        "id": 9,
        "type": "news",
        "headline": "商汤日日新 6.7 Flash-Lite 发布",
        "details": [
            "轻量多模态智能体模型，消除中间视觉层",
            "Token 消耗降低 60%，毫秒级反馈",
            "金融、制造、医疗、教育多行业落地",
        ],
        "highlight_nums": ["60%", "毫秒"],
        "narration": "商汤发布日日新六点七 Flash-Lite 轻量多模态智能体模型，直接理解复杂文档和图表，实现看、想、做一体化。Token 消耗较传统方案降低百分之六十，支持毫秒级反馈，已在金融、制造、医疗等多行业落地。",
    },
    {
        "id": 10,
        "type": "ending",
        "headline": "感谢收看",
        "subline": "关注频道，每天获取 AI 最新资讯",
        "narration": "以上就是今天的 AI 早报，感谢收看，我们明天见。",
    },
]


def get_audio_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(r.stdout)
        return float(info["format"]["duration"])
    except:
        return 5.0


def load_news_segments():
    """支持从外部 JSON 文件加载 NEWS_SEGMENTS"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--news-json", help="从 fetch_news.py 输出的 JSON 文件加载新闻")
    args, _ = parser.parse_known_args()

    if args.news_json and os.path.exists(args.news_json):
        print(f"[新闻] 从外部文件加载: {args.news_json}")
        with open(args.news_json, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("[新闻] 使用内置 NEWS_SEGMENTS")
        return NEWS_SEGMENTS


def main():
    now = datetime.now()
    segments = load_news_segments()
    output_dir = os.path.join(OUTPUT_DIR, f"board_live_{now.strftime('%Y%m%d_%H%M')}")
    seg_dir = os.path.join(output_dir, "segments")
    tts_dir = os.path.join(output_dir, "tts")
    os.makedirs(seg_dir, exist_ok=True)
    os.makedirs(tts_dir, exist_ok=True)

    print("=" * 50)
    print(f"  动画板书 AI 早报 - 实时新闻版")
    print(f"  {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 0. 配图：优先用新闻原图，抓不到再 AI 生成
    ark_key = _load_ark_key()
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    print("\n[配图] 获取新闻配图...")
    for seg in segments:
        sid = seg["id"]
        seg_type = seg.get("type", "news")
        if seg_type == "title":
            continue  # 标题卡不需要配图
        headline = seg.get("headline", "")
        if not headline:
            continue
        img_path = os.path.join(images_dir, f"seg_{sid:02d}.jpg")
        # 已有本地缓存
        if os.path.exists(img_path):
            seg["image_path"] = img_path
            print(f"  seg_{sid:02d}: 已有配图")
            continue
        # 优先用新闻原图
        news_img_url = seg.get("image_url", "")
        if news_img_url:
            try:
                import requests as _req
                _resp = _req.get(news_img_url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                if _resp.status_code == 200 and len(_resp.content) > 5000:
                    with open(img_path, "wb") as f:
                        f.write(_resp.content)
                    seg["image_path"] = img_path
                    print(f"  seg_{sid:02d}: ✅ 新闻原图 ({len(_resp.content)//1024}KB)")
                    continue
            except Exception as e:
                print(f"  seg_{sid:02d}: ⚠️ 新闻原图下载失败: {e}")
        # 新闻原图没有，AI 生成
        if ark_key:
            prompt = _enhance_prompt(headline)
            try:
                ok = _generate_from_seedream(prompt, img_path, ark_key)
                if ok:
                    seg["image_path"] = img_path
                    print(f"  seg_{sid:02d}: ✅ AI配图 {headline[:30]}")
                else:
                    print(f"  seg_{sid:02d}: ⚠️ AI 生成失败")
            except Exception as e:
                print(f"  seg_{sid:02d}: ❌ {e}")
        else:
            print(f"  seg_{sid:02d}: ⚠️ 无新闻图且无 ARK_API_KEY")
    n_ok = sum(1 for s in segments if s.get("image_path"))
    print(f"[配图] 完成: {n_ok}/{len(segments)} 张")

    # 1. TTS
    print("\n[1/3] 生成 TTS 语音...")
    for seg in segments:
        sid = seg["id"]
        narration = seg.get("narration", "")
        tts_path = os.path.join(tts_dir, f"seg_{sid:02d}.mp3")
        if os.path.exists(tts_path):
            seg["tts_path"] = tts_path
            seg["tts_duration"] = get_audio_duration(tts_path)
            print(f"  seg_{sid:02d}: 已有 ({seg['tts_duration']:.1f}s)")
            continue
        try:
            result = synthesize_speech(narration, tts_path, voice_id="冰糖", speed=1.1)
            seg["tts_path"] = tts_path
            seg["tts_duration"] = result["duration_sec"]
            print(f"  seg_{sid:02d}: {result['duration_sec']:.1f}s ✅")
        except Exception as e:
            print(f"  seg_{sid:02d}: ❌ {e}")
            seg["tts_path"] = None
            seg["tts_duration"] = 5.0

    # 2. 视频片段
    print("\n[2/3] 生成动画板书视频片段...")
    video_segments = []
    for i, seg in enumerate(segments):
        sid = seg["id"]
        seg_type = seg.get("type", "news")
        bg = BG_COLORS[(sid - 1) % len(BG_COLORS)]
        seg_path = os.path.join(seg_dir, f"seg_{sid:02d}.mp4")
        tts_path = seg.get("tts_path")
        target_dur = seg.get("tts_duration", 8.0) + (1.5 if seg_type == "news" else 0)

        print(f"  seg_{sid:02d}: {seg_type} / {target_dur:.1f}s ...")
        try:
            img_path = seg.get("image_path") or seg.get("image_url")
            if tts_path and os.path.exists(tts_path):
                make_animated_board_with_audio(
                    seg, tts_path, seg_path,
                    logo_text=f"AI 早报 {now.strftime('%Y-%m-%d')}", index=i,
                    bg_color1=bg[0], bg_color2=bg[1],
                    image_path=img_path,
                )
            else:
                make_animated_board(
                    seg, seg_path,
                    logo_text=f"AI 早报 {now.strftime('%Y-%m-%d')}", index=i,
                    audio_duration=target_dur,
                    bg_color1=bg[0], bg_color2=bg[1],
                    image_path=img_path,
                )
            if os.path.exists(seg_path):
                size_kb = os.path.getsize(seg_path) / 1024
                dur = get_audio_duration(seg_path)
                video_segments.append(seg_path)
                print(f"  seg_{sid:02d}: ✅ {size_kb:.0f}KB / {dur:.1f}s")
        except Exception as e:
            print(f"  seg_{sid:02d}: ❌ {e}")

    if not video_segments:
        print("\n❌ 没有生成任何视频片段")
        return

    # 3. 合并
    print(f"\n[3/3] 合并 {len(video_segments)} 个片段...")
    concat_file = os.path.join(output_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in video_segments:
            f.write(f"file '{os.path.abspath(p)}'\n")

    final_path = os.path.join(output_dir, "ai_news_board_live.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        final_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode == 0 and os.path.exists(final_path):
        size_mb = os.path.getsize(final_path) / (1024 * 1024)
        dur = get_audio_duration(final_path)
        print(f"\n🎉 完成！")
        print(f"  文件: {final_path}")
        print(f"  大小: {size_mb:.1f}MB")
        print(f"  时长: {dur:.1f}s")
        return final_path
    else:
        print(f"\n❌ 合并失败: {r.stderr[-500:]}")
        return None


if __name__ == "__main__":
    main()
