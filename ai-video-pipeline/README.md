# AI 短视频自动流水线

自动采集热点 → 生成脚本 → 语音合成 → 视频合成 → 一键发布

## 架构

```
Cron定时触发 → collector(采集) → scriptwriter(LLM脚本) → tts_engine(语音) → video_maker(合成) → publisher(发布)
```

## 目录结构

```
ai-video-pipeline/
├── config.py          # 全局配置
├── collector.py       # 内容采集（微博热搜 + 关键词搜索）
├── scriptwriter.py    # LLM 脚本生成
├── tts_engine.py      # MiniMax TTS 语音合成
├── video_maker.py     # FFmpeg 视频合成 + 字幕
├── pipeline.py        # 主控流程
├── cron_runner.py     # 定时任务入口
├── output/            # 输出目录（按日期）
│   └── 2026-05-05_1530/
│       ├── news_raw.json    # 原始素材
│       ├── script.json      # 生成的脚本
│       ├── narration.mp3    # 语音
│       ├── subtitles.srt    # 字幕
│       ├── final_video.mp4  # 最终视频
│       └── metadata.json    # 元数据
└── assets/            # 素材目录（背景图等）
```

## 快速开始

### 1. 环境要求
- Python 3.11+
- FFmpeg（含 libass）
- MiniMax API Key

### 2. 设置 API Key
```bash
export MINIMAX_API_KEY="your-api-key-here"
```

### 3. 运行
```bash
# 完整流水线
python3 pipeline.py --topics "AI人工智能" "科技新闻" --count 5

# 只测试脚本生成
python3 pipeline.py --dry-run

# 自定义音色和语速
python3 pipeline.py --voice "Sweet_Girl_2" --speed 1.0
```

### 4. 定时运行
```bash
# 每天早上 8 点自动运行
python3 cron_runner.py
```

## 配置说明

编辑 `config.py` 修改：
- **话题关键词**: `DEFAULT_TOPICS`
- **视频尺寸**: 竖屏 1080x1920（可改）
- **字幕样式**: 字体、颜色、位置
- **TTS 音色**: 默认 Sweet_Girl_2

## 可用音色

| 音色 ID | 描述 | 适合场景 |
|---------|------|---------|
| Sweet_Girl_2 | 甜美女声 | 资讯、生活 |
| Preset_Open_Amazon | 沉稳男声 | 科技、商业 |
| British_Elegant_Lady | 英式女声 | 英文内容 |

查看全部音色：
```bash
python3 ~/.openclaw/workspace/skills/minimax-speech/scripts/minimax_tts.py voices --voice-type system
```

## TODO

- [ ] 接入更多新闻源（今日头条、知乎等）
- [ ] AI 自动生成配图
- [ ] 自动发布到抖音/B站
- [ ] 多模板支持（不同风格）
- [ ] 数据统计面板
