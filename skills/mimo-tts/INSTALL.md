# MiMo TTS Skill - 快速安装指南（轻量版）

## 📦 安装包说明

本版本为**轻量版**，不包含 `node_modules`，需要自行安装依赖。

**优势**：
- 包体积小（~18KB vs 14MB）
- 依赖版本最新
- 适合分发和部署

---

## 1. 解压技能包

```bash
# 解压到 OpenClaw skills 目录
unzip mimo-tts-v1.0.0-lite.zip -d ~/.openclaw/skills/
```

## 2. 安装依赖

```bash
# 进入技能目录
cd ~/.openclaw/skills/mimo-tts

# 安装 npm 依赖（只需一次）
npm install
```

安装完成后会生成 `node_modules/` 目录。

## 3. 获取 API Key

访问 [MiMo 开放平台](https://platform.xiaomimimo.com) 注册并获取 API Key。

## 4. 设置环境变量

### Linux/macOS
```bash
export MIMO_API_KEY=your_api_key_here
```

### 永久设置（推荐）
将以下内容添加到 `~/.bashrc` 或 `~/.zshrc`：
```bash
export MIMO_API_KEY=your_api_key_here
```

然后执行：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 5. 验证安装

```bash
mimo-tts --help
```

预期输出：
```
MiMo V2-TTS 语音合成技能

用法：mimo-tts [选项]

选项:
  --text <文本>       要转换为语音的文本内容 (必填)
  --output <文件>     输出音频文件路径 (必填)
  --voice <音色>      音色选择 (可选，默认：mimo_default)
  ...
```

## 6. 快速测试

```bash
# 中文测试
mimo-tts --text "你好，欢迎使用 MiMo 语音合成" --output test.wav --voice default_zh

# 英文测试
mimo-tts --text "Hello world" --voice default_en --output hello.wav

# 带风格测试
mimo-tts --text "<style>欢快</style>今天天气真好！" --output happy.wav
```

---

## 故障排除

### 问题：`mimo-tts` 命令不存在

**解决**：确保技能目录在 PATH 中，或者使用完整路径：
```bash
~/.openclaw/skills/mimo-tts/index.js --help
```

### 问题：`openai` 模块未找到

**解决**：重新安装依赖
```bash
cd ~/.openclaw/skills/mimo-tts
npm install
```

### 问题：未设置 MIMO_API_KEY

**解决**：设置环境变量
```bash
export MIMO_API_KEY=your_api_key_here
```

---

## 完整文件列表

```
mimo-tts/
├── index.js          # CLI 入口
├── scripts/
│   └── tts.js        # TTS 核心脚本
├── package.json      # 依赖配置
├── package-lock.json # 依赖锁定
├── SKILL.md          # Skill 描述
├── README.md         # 使用说明
├── INSTALL.md        # 本文件
├── VERSION           # 版本信息
└── CHANGELOG.md      # 更新日志
```

安装依赖后：
```
└── node_modules/     # npm 依赖（自动生成）
```
