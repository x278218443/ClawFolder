# 🎬 B站全自动短视频流水线

自动抓热点 → AI写脚本 → 即梦生成画面 → TTS配音 → FFmpeg合成 → 发布B站

## 📁 项目结构

```
bilibili-bot/
├── config/
│   ├── settings.py          # 配置文件（路径、参数）
│   └── api_keys.json        # API密钥（需手动配置）
├── modules/
│   ├── hot_topics.py        # 热点抓取（微博/知乎/B站/抖音/头条）
│   ├── script_writer.py     # AI脚本生成（MiMo模型）
│   ├── video_gen.py         # 即梦API视频生成
│   ├── tts_gen.py           # MiMo TTS配音
│   ├── video_assemble.py    # FFmpeg视频合成
│   └── bilibili_publish.py  # B站自动发布
├── output/
│   ├── scripts/             # 生成的脚本
│   ├── audio/               # 配音音频
│   ├── clips/               # 视频片段
│   └── final/               # 最终成品
├── logs/                    # 运行日志
├── pipeline.py              # 主流水线控制器
├── scheduler.py             # 定时调度器
├── setup.py                 # 配置向导
└── README.md                # 本文件
```

## 🚀 快速开始

### 1. 配置 API 密钥

```bash
cd ~/.openclaw/workspace/bilibili-bot
python3 setup.py
```

需要配置：
- **MiMo API Key**（必填）- 用于 AI 生成脚本和配音
- **火山引擎 Key**（可选）- 即梦 API，用于生成视频画面
- **B站 Cookie**（可选）- 用于自动发布

### 2. 试运行（不发布）

```bash
python3 scheduler.py run --dry-run
```

### 3. 正式运行

```bash
# 自动生成一个视频
python3 scheduler.py run

# 指定话题
python3 scheduler.py run --topic "今天的热点话题"

# 生成多个
python3 scheduler.py run --count 3
```

### 4. 安装定时任务

```bash
# 默认每天 11:00 和 19:00 自动运行
python3 scheduler.py install

# 自定义时间（每天 9 点和 20 点）
python3 scheduler.py install --schedule "0 9,20 * * *"

# 卸载定时任务
python3 scheduler.py uninstall
```

## 🔧 各模块独立测试

```bash
# 测试热点抓取
python3 modules/hot_topics.py

# 测试脚本生成
python3 modules/script_writer.py

# 测试 TTS
python3 modules/tts_gen.py

# 测试即梦（需要配置 API Key）
python3 modules/video_gen.py
```

## 📝 流水线流程

```
┌──────────────┐
│  1. 热点抓取  │  ← tophub.today (微博/知乎/B站/抖音/头条)
└──────┬───────┘
       ↓
┌──────────────┐
│  2. AI 脚本  │  ← MiMo V2.5 Pro 生成脚本+分镜+提示词
└──────┬───────┘
       ↓
┌──────────────┐
│  3. 视频生成  │  ← 即梦 API (文生图→图生视频)
└──────┬───────┘
       ↓
┌──────────────┐
│  4. TTS 配音  │  ← MiMo TTS 生成旁白音频
└──────┬───────┘
       ↓
┌──────────────┐
│  5. 合成视频  │  ← FFmpeg 拼接+字幕+BGM
└──────┬───────┘
       ↓
┌──────────────┐
│  6. 发布 B站  │  ← B站 API 自动投稿
└──────────────┘
```

## 💰 成本估算

| 项目 | 费用 |
|------|------|
| MiMo 模型（脚本生成） | 套餐内 |
| MiMo TTS（配音） | 套餐内/免费 |
| 即梦 API（视频画面） | ~¥0.5-2/片段 |
| B站发布 | 免费 |
| **单条视频总成本** | **约 ¥5-20** |

## ⚠️ 注意事项

1. **B站审核**: AI生成内容可能触发审核，建议人工审核后再发布
2. **即梦额度**: 注意控制调用频率和额度
3. **Cookie 过期**: B站 Cookie 有效期有限，需要定期更新
4. **内容质量**: 全自动模式建议先半自动跑通，再逐步放开

## 🔄 进阶用法

### 作为 OpenClaw 子任务运行

可以在 OpenClaw 中直接调用：
```
帮我运行 B站视频流水线，话题是"今天的科技热点"
```

### 自定义内容领域

编辑 `modules/hot_topics.py` 中的 `filter_for_video()` 函数，
添加关键词过滤、领域筛选等逻辑。

### 更换 TTS 音色

在 `config/settings.py` 中修改 `TTS_VOICE` 参数。
MiMo TTS 支持多种音色，详见：
https://platform.xiaomimimo.com/docs/zh-CN
