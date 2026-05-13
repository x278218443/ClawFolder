---
name: mimo-tts
version: 1.2.0
description: 小米 MiMo V2-TTS 语音合成技能。使用兼容 OpenAI SDK 的格式将文本转换为自然流畅的语音。支持多种音色选择、风格控制和输出格式。当用户需要将文本转换为语音、生成音频文件、或使用 MiMo TTS 服务时使用此技能。
author: OpenClaw Community
license: MIT
repository: https://github.com/openclaw/skills/tree/main/mimo-tts
---

# MiMo V2-TTS 语音合成技能

**版本**: v1.2.0  
**发布日期**: 2026-04-05

## 快速开始

使用命令行调用：

```bash
mimo-tts --text "你好，欢迎使用 MiMo 语音合成" --output audio.wav
```

## 核心功能

### 1. 文本转语音

支持将任意文本转换为自然流畅的语音，兼容 OpenAI SDK 格式。

### 2. 音色选择

支持 3 种预置音色：

- `mimo_default` - MiMo-默认音色
- `default_zh` - MiMo-中文女声
- `default_en` - MiMo-英文女声

使用方式：

```bash
mimo-tts --text "Hello World" --voice default_en --output hello.wav
```

### 3. 风格控制

支持在文本中使用 `<style>风格</style>` 标签控制语音风格：

```bash
# 情绪变化
mimo-tts --text "<style>开心</style>今天真是太棒了！" --output happy.wav

# 方言
mimo-tts --text "<style>东北话</style>哎呀妈呀！" --output dongbei.wav

# 唱歌
mimo-tts --text "<style>唱歌</style>原谅我这一生不羁放纵爱自由" --output sing.wav
```

### 4. 输出格式

- `wav` - 标准 WAV 格式（默认）
- `pcm16` - 16 位 PCM（流式模式专用）

## 命令行参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--text` | ✅ | - | 要合成的文本内容 |
| `--output` | ✅ | - | 输出音频文件路径 |
| `--voice` | ❌ | `mimo_default` | 音色选择 |
| `--format` | ❌ | `wav` | 输出格式 |
| `--stream` | ❌ | `false` | 流式模式 |
| `--help` | ❌ | - | 显示帮助信息 |

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `MIMO_API_KEY` | MiMo API 密钥（必填） |

## 文件结构

```
mimo-tts/
├── SKILL.md          # Skill 描述（本文件）
├── index.js          # CLI 入口
├── scripts/
│   └── tts.js        # TTS 核心脚本
├── package.json      # 依赖配置
├── README.md         # 使用说明
├── INSTALL.md        # 安装指南
├── VERSION           # 版本信息
└── CHANGELOG.md      # 更新日志
```

## 使用示例

### 基础用法

```bash
# 中文语音
mimo-tts --text "你好，我是你的 AI 助手" --output greeting.wav

# 英文语音
mimo-tts --text "Hello, I am your AI assistant" --voice default_en --output hello.wav
```

### 风格控制

```bash
# 欢快语气
mimo-tts --text "<style>欢快</style>今天天气真好！" --output happy.wav

# 东北方言
mimo-tts --text "<style>东北话</style>哎呀妈呀，这天儿真冷！" --output dongbei.wav

# 唱歌模式
mimo-tts --text "<style>唱歌</style>原谅我这一生不羁放纵爱自由" --output sing.wav
```

### 细粒度控制

```bash
mimo-tts --text "（紧张，深呼吸）呼……冷静，冷静。（语速加快）自我介绍已经背了五十遍了" --output nervous.wav
```

## 注意事项

1. **文本位置**：语音合成文本自动放在 `assistant` 角色消息中
2. **风格标签**：`<style>` 标签必须放在文本开头
3. **唱歌模式**：必须仅使用 `<style>唱歌</style>` 标签
4. **流式模式**：流式调用时必须使用 `pcm16` 格式
5. **文本长度**：推荐单次 2000 字以内，长文本建议分段

## 故障排除

### 错误：未设置 MIMO_API_KEY
```bash
export MIMO_API_KEY=your_api_key_here
```

### 错误：HTTP 401
API Key 无效，请检查是否正确

### 错误：HTTP 404
检查 API 端点是否正确

### 错误：请求超时
文本过长或网络问题，尝试缩短文本

## 相关链接

- [MiMo 开放平台](https://platform.xiaomimimo.com)
- [API 文档](https://platform.xiaomimimo.com/#/docs/usage-guide/speech-synthesis)
- [控制台](https://platform.xiaomimimo.com/#/console/balance)

## 许可证

MIT License

## 更新日志

参见 [CHANGELOG.md](./CHANGELOG.md)
