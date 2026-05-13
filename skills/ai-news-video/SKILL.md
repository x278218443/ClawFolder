---
name: ai-news-video
description: |
  AI 早报短视频自动生成。抓取实时 AI 新闻 → 生成 TTS 语音旁白 → 用 MoviePy 生成动画板书风格视频（深色背景 + 文字逐行出现 + 淡入淡出转场）→ 合成最终带旁白的 1080p 视频。
  触发条件：用户要求生成 AI 早报视频、AI 新闻短视频、动画板书视频、news video。
  可选：用 Seedream 5.0 生成视频封面图。
---

# AI 早报动画板书视频

## 流水线概览

```
新闻抓取 → LLM 脚本生成 → TTS 语音 → 动画板书片段 → 合并最终视频 → 推送飞书
```

## 快速开始

```bash
# 1. 抓取实时新闻（v3 — 多源 + 大模型优先）
cd ~/.openclaw/workspace/skills/ai-news-video
python3 scripts/fetch_news.py 7                      # 抓取 7 条，输出 JSON 到 stdout
python3 scripts/fetch_news.py 7 /tmp/news.json       # 抓取 7 条，写入文件

# 2. 生成视频
cd ~/.openclaw/workspace/ai-video-pipeline
python3 make_board_live.py --news-json /tmp/news.json

# 3. 自动化（生成 + 推送飞书）
cd ~/.openclaw/workspace/ai-video-pipeline
bash auto_news_video.sh --now
```

## 新闻过滤规则（v3 — 大模型优先）

### 核心原则
1. **大模型/产品发布优先** — GPT、Claude、Gemini、DeepSeek、千问等核心动态得分最高
2. **公司动态次之** — AI 公司融资/投资/战略调整（不排除！）
3. **工具/基建再次** — Agent、MCP、推理框架等开发者工具
4. **关键数字加分** — 降60%、300%增长、40亿美元等
5. **每条必附来源** — 标注新闻出处

### 品类与优先级（分值越高越优先）

| 品类 | 标签 | 优先级分 | 典型事件 |
|------|------|----------|----------|
| 模型/产品发布 | 🟢 | 100 | 新模型、新版本、API 更新、开源发布 |
| 事故/宕机 | 🔴 | 90 | 服务中断、安全漏洞、法律诉讼 |
| 公司动态 | 🏢 | 80 | 融资、投资、收购、战略调整 |
| 开源项目 | 🔵 | 70 | GitHub 仓库、模型权重发布 |
| 工具/基建更新 | 🟡 | 60 | 开发者工具、框架、插件 |
| 成本/数据 | 📊 | 50 | Token 价格、调用量统计 |
| 硬件/AI设备 | 📱 | 40 | 芯片、GPU、机器人 |

### 排除规则
- **排除**：纯裁员、财报、IPO、股价等非 AI 相关商业新闻
- **不排除**：AI 公司融资/投资（如 DeepSeek 融资、OpenAI 投资），只要标题含 AI 关键词就不排除

### 综合评分公式
```
总分 = 品类基础分 + 数字加分(15) + 核心AI关键词加分(8)
```
核心 AI 关键词：大模型、GPT、DeepSeek、OpenAI、Claude、Gemini、千问、豆包、通义、文心、Llama、Grok、Codex、Agent、智能体

## 数据源（v3 — 3 个源）

| 源 | URL | 状态 | 说明 |
|---|---|---|---|
| AIBase 中文 | aibase.com/zh/news | ✅ | 综合 AI 新闻，中文内容，更新快 |
| IT之家 AI | ithome.com/tag/AI | ✅ | 覆盖 OpenAI/Google/国内大模型，新闻量大 |
| 36kr AI | 36kr.com/information/AI | ✅ | 科技商业视角，有投资/融资分析 |

### 已移除的源（v2 → v3）
- ❌ 机器之心（jiqizhixin.com）— SPA 单页应用，HTML 无内容，无法用 requests 抓取
- ❌ 量子位（qbitai.com）— 返回 403，被封
- ❌ 虎嗅（huxiu.com）— SPA，同机器之心

### 过滤流程
```
3 个源抓取（~60 条）→ 排除无关新闻 → 品类关键词匹配
→ 综合评分排序 → 标题去重（相似度>60%）→ 取前 N 条
```

输出目录：`output/board_live_YYYYMMDD_HHMM/`

## 核心模块

| 文件 | 功能 |
|------|------|
| `scripts/fetch_news.py` | 新闻抓取 + 过滤（v3，3 源，大模型优先评分） |
| `make_board_live.py` | 主入口：抓新闻 + 生成 TTS + 生成视频 |
| `board_maker_anim.py` | MoviePy 动画板书生成器 |
| `tts_engine.py` | TTS 语音合成（MiMo / edge-tts） |
| `image_fetcher.py` | 图片生成（Seedream 5.0 / DashScope） |
| `video_generator.py` | 视频生成（Seedance 1.5 Pro） |
| `config.py` | 配置（尺寸、字体、API Key） |
| `auto_news_video.sh` | 自动化脚本（生成 + 推送飞书） |

## 定时任务

OpenClaw cron job `AI早报视频`（ID: bce38a17...）：
- 每天 00:05（Asia/Shanghai）自动运行
- isolated session → 生成视频 → 用 `openclaw message send --channel feishu` 推送到飞书
- 推送目标：`user:ou_74504c7998ca288e6531039420584403`

## 自定义新闻内容

编辑 `make_board_live.py` 中的 `NEWS_SEGMENTS` 列表：

```python
{
    "id": 1,
    "type": "title",          # title / news / ending
    "headline": "AI 早报",
    "subline": "2026 年 5 月 8 日",
    "narration": "欢迎收看今天的 AI 早报。",
},
{
    "id": 2,
    "type": "news",
    "headline": "OpenAI 发布 GPT-5.5",     # 大标题
    "details": ["要点一", "要点二", "要点三"],  # 逐行显示
    "highlight_nums": ["60%", "40%"],        # 高亮数字
    "narration": "OpenAI 发布了...",         # TTS 旁白文本
}
```

## 动画效果

每条新闻生成一个视频片段：
1. 深色渐变背景 + 网格线（每条新闻不同配色）
2. 大号装饰序号（右下角半透明）
3. Logo（右上角 "AI 早报"）
4. 标题淡入 → 高亮数字淡入 → 详情要点逐行淡入
5. 整体 FadeIn / FadeOut

## 封面图生成

```python
# 使用 Seedream 5.0（火山方舟 ARK API）
# 端点: https://ark.cn-beijing.volces.com/api/v3/images/generations
# 模型: doubao-seedream-5-0-260128
# 尺寸: 2560x1440（最低 3686400 像素）
# 认证: Authorization: Bearer {ARK_API_KEY}
```

## API Key 配置

在 `ai-video-pipeline/.env` 中配置：

```
ARK_API_KEY=ark-xxx          # 火山方舟（Seedream 图片 + Seedance 视频）
MIMO_API_KEY=tp-xxx          # 小米 MiMo TTS（可选，自动从 openclaw.json 读取）
DASHSCOPE_API_KEY=sk-xxx     # 阿里 DashScope（备用图片生成）
```

## 飞书发送限制

- 飞书文件上传硬限制 30MB
- <30MB 视频可直接通过 `openclaw message send --channel feishu --media` 发送
- 大文件需用 ffmpeg 压缩（CRF 28-32）

## 依赖

- Python 3.12+
- moviepy (`pip install moviepy --break-system-packages`)
- Pillow (`pip install pillow==10.4.0 --break-system-packages`)
- numpy, requests
- ffmpeg（系统已安装）

## 已知限制

- MoviePy 渲染 1920x1080 较慢（每段约 30-60 秒）
- TTS 引擎优先使用 MiMo，失败时降级到 edge-tts
- 凌晨 00:05 跑只能抓到前一天的新闻（IT之家/AIBase 更新快，通常没问题）
- 参考对象（橘鸦Juya）通常下午发布，能覆盖当天全天热点
