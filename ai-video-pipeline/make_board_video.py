#!/usr/bin/env python3
"""
动画板书风格 AI 早报视频生成器
完整流程：新闻内容 → TTS 语音 → 动画板书 → 合成最终视频
"""
import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from tts_engine import synthesize_speech
from board_maker_anim import make_animated_board, make_animated_board_with_audio, make_title_card
from config import OUTPUT_DIR

W, H = 1920, 1080
FPS = 30

# === 颜色方案 ===
BG_COLORS = [
    ((25, 25, 45), (15, 15, 35)),     # 深蓝黑
    ((30, 20, 40), (20, 15, 30)),     # 深紫黑
    ((20, 35, 25), (15, 25, 20)),     # 深绿黑
    ((35, 25, 20), (25, 18, 15)),     # 深棕黑
    ((25, 30, 40), (18, 22, 30)),     # 深灰蓝
    ((35, 20, 25), (25, 15, 18)),     # 深红黑
    ((20, 30, 35), (15, 22, 28)),     # 深青黑
    ((30, 25, 35), (22, 18, 28)),     # 深紫蓝
]

# === 新闻内容 ===
NEWS_SEGMENTS = [
    {
        "id": 1,
        "type": "title",
        "headline": "AI 早报",
        "subline": "2026 年 5 月 8 日 星期四",
        "narration": "欢迎收看今天的 AI 早报。",
    },
    {
        "id": 2,
        "type": "news",
        "headline": "OpenAI 发布 GPT-5.5 Instant",
        "details": [
            "响应速度提升 60%，成本降低 40%",
            "支持 100 万 token 超长上下文",
            "已在 ChatGPT 和 API 全量上线",
        ],
        "highlight_nums": ["60%", "40%", "100 万"],
        "narration": "OpenAI 昨天正式发布了 GPT-5.5 Instant 模型，响应速度提升了百分之六十，成本降低了百分之四十，同时支持百万 token 超长上下文，目前已在 ChatGPT 和 API 端全量上线。",
    },
    {
        "id": 3,
        "type": "news",
        "headline": "Google DeepMind 推出 Gemini 3.0",
        "details": [
            "原生多模态：文本、图像、视频、音频一体化",
            "在 MMLU 和 HumanEval 基准中刷新纪录",
            "首次支持实时视频流理解",
        ],
        "highlight_nums": ["Gemini 3.0"],
        "narration": "谷歌 DeepMind 发布了 Gemini 3.0，这是一款原生多模态模型，首次实现了文本、图像、视频和音频的统一处理，在多个基准测试中刷新了纪录。",
    },
    {
        "id": 4,
        "type": "news",
        "headline": "Anthropic Claude 获批企业安全认证",
        "details": [
            "通过 SOC 2 Type II 和 ISO 27001 认证",
            "新增企业级数据加密和审计日志",
            "已有 300 多家企业客户签约",
        ],
        "highlight_nums": ["300+ 家", "SOC 2"],
        "narration": "Anthropic 的 Claude 通过了 SOC 2 Type II 和 ISO 27001 企业安全认证，并新增了企业级数据加密和审计日志功能，已有超过三百家企业客户签约使用。",
    },
    {
        "id": 5,
        "type": "news",
        "headline": "Meta 开源 Llama 4 Scout 模型",
        "details": [
            "170 亿参数，性能对标 GPT-4",
            "完全开源可商用，无限制使用",
            "支持 128K 上下文窗口",
        ],
        "highlight_nums": ["170 亿", "128K"],
        "narration": "Meta 开源了 Llama 4 Scout 模型，拥有 170 亿参数，性能对标 GPT-4，完全开源可商用，支持 128K 的上下文窗口。",
    },
    {
        "id": 6,
        "type": "news",
        "headline": "英伟达发布 Blackwell Ultra GPU",
        "details": [
            "AI 训练性能提升 4 倍",
            "单卡显存达到 192GB HBM4",
            "预计今年第三季度量产",
        ],
        "highlight_nums": ["4 倍", "192GB"],
        "narration": "英伟达正式发布了 Blackwell Ultra GPU，AI 训练性能提升了 4 倍，单卡显存达到 192GB HBM4，预计今年第三季度开始量产。",
    },
    {
        "id": 7,
        "type": "news",
        "headline": "小米 MiMo 模型通过图灵测试",
        "details": [
            "中文对话能力首次达到人类水平",
            "在 5 项权威评测中排名第一",
            "已集成到小米全系智能设备",
        ],
        "highlight_nums": ["图灵测试", "第一"],
        "narration": "小米自研的 MiMo 大模型在中文对话能力上首次通过图灵测试，达到人类水平，在五项权威评测中排名第一，并已集成到小米全系智能设备中。",
    },
    {
        "id": 8,
        "type": "news",
        "headline": "欧盟 AI 法案正式生效",
        "details": [
            "高风险 AI 系统需通过合规审查",
            "禁止使用实时生物识别监控",
            "违规企业最高罚款 3500 万欧元",
        ],
        "highlight_nums": ["3500 万€"],
        "narration": "欧盟人工智能法案正式生效，要求高风险 AI 系统必须通过合规审查，禁止使用实时生物识别监控，违规企业最高将被罚款 3500 万欧元。",
    },
    {
        "id": 9,
        "type": "ending",
        "headline": "感谢收看",
        "subline": "关注频道，每天获取 AI 最新资讯",
        "narration": "以上就是今天的 AI 早报，感谢收看，我们明天见。",
    },
]


def get_audio_duration(path):
    """获取音频时长"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(r.stdout)
        return float(info["format"]["duration"])
    except:
        return 5.0


def main():
    now = datetime.now()
    output_dir = os.path.join(OUTPUT_DIR, f"board_{now.strftime('%Y%m%d_%H%M')}")
    os.makedirs(output_dir, exist_ok=True)
    seg_dir = os.path.join(output_dir, "segments")
    tts_dir = os.path.join(output_dir, "tts")
    os.makedirs(seg_dir, exist_ok=True)
    os.makedirs(tts_dir, exist_ok=True)

    print("=" * 50)
    print(f"  动画板书 AI 早报视频生成器")
    print(f"  {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # === 第1步：生成所有 TTS ===
    print("\n[1/3] 生成 TTS 语音...")
    for seg in NEWS_SEGMENTS:
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

    # === 第2步：生成每个片段的视频 ===
    print("\n[2/3] 生成动画板书视频片段...")
    video_segments = []

    for i, seg in enumerate(NEWS_SEGMENTS):
        sid = seg["id"]
        seg_type = seg.get("type", "news")
        bg = BG_COLORS[(sid - 1) % len(BG_COLORS)]
        seg_path = os.path.join(seg_dir, f"seg_{sid:02d}.mp4")
        tts_path = seg.get("tts_path")

        # 计算视频时长
        if seg_type in ("title", "ending"):
            target_dur = seg.get("tts_duration", 4.0)
        else:
            target_dur = seg.get("tts_duration", 8.0) + 1.5  # 额外留白

        print(f"  seg_{sid:02d}: {seg_type} / {target_dur:.1f}s ...")

        try:
            if tts_path and os.path.exists(tts_path):
                # 有音频：用 make_animated_board_with_audio
                make_animated_board_with_audio(
                    seg, tts_path, seg_path,
                    logo_text="AI 早报 2026-05-08",
                    index=i,
                    bg_color1=bg[0], bg_color2=bg[1],
                )
            else:
                # 无音频：只生成视频
                make_animated_board(
                    seg, seg_path,
                    logo_text="AI 早报 2026-05-08",
                    index=i,
                    audio_duration=target_dur,
                    bg_color1=bg[0], bg_color2=bg[1],
                )

            if os.path.exists(seg_path):
                size_kb = os.path.getsize(seg_path) / 1024
                dur = get_audio_duration(seg_path)
                video_segments.append(seg_path)
                print(f"  seg_{sid:02d}: ✅ {size_kb:.0f}KB / {dur:.1f}s")
            else:
                print(f"  seg_{sid:02d}: ❌ 文件不存在")
        except Exception as e:
            print(f"  seg_{sid:02d}: ❌ {e}")

    if not video_segments:
        print("\n❌ 没有生成任何视频片段")
        return

    # === 第3步：合并 ===
    print(f"\n[3/3] 合并 {len(video_segments)} 个片段...")

    # 写 concat 列表
    concat_file = os.path.join(output_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in video_segments:
            f.write(f"file '{os.path.abspath(p)}'\n")

    final_path = os.path.join(output_dir, "ai_news_board.mp4")
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
        print(f"  片段: {len(video_segments)}")
    else:
        print(f"\n❌ 合并失败: {r.stderr[-500:]}")


if __name__ == "__main__":
    main()
