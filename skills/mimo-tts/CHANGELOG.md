# 更新日志 (Changelog)

## [1.2.0] - 2026-04-05

### ✨ 新增功能
- stdin 管道输入：`echo "文本" | mimo-tts -o out.wav`
- 短参数：`-t` `-o` `-v` `-f` `-i` `-h`

### 🔧 改进修复
- extractAudio 不再静默吞错，异常时输出响应结构便于调试
- Style 正则改为 `<style\b[^>]*>.*?</style>`，支持属性和空格
- API 地址可通过 `MIMO_API_BASE` 环境变量覆盖
- tts.js 移除重复的 CLI 入口，只保留模块导出

---

## [1.1.0] - 2026-04-05

### 🐛 安全修复
- 移除 `execSync` 子进程调用，改为 `require` 直接加载，消除 Shell 注入风险

### ✨ 新增功能
- `--input` 参数：支持从文件读取长文本（UTF-8）
- 自动文本分段：超过 2000 字按句号自动切分，分段合成后合并
- 网络重试：HTTP 429/5xx/网络错误自动重试，最多 3 次指数退避
- 段间静音：分段合成时自动插入 300ms 静音间隔，避免吞字

### 🔧 改进修复
- WAV 合并：不再硬编码 16kHz，从实际 WAV header 读取采样率（API 返回 24kHz）
- Style 标签：分段时自动将 `<style>` 标签附加到每个分段，保持风格一致
- 请求超时：从 30s 延长至 120s，长文本不再超时
- parseArgs：修复 `--text` 作为末尾参数时的越界自增问题
- 输出信息：新增音频时长、采样率、声道数显示
- 移除未使用的 `attempt` 参数

### 🏗️ 架构
- `index.js` 改为直接 `require('./scripts/tts')`，消除子进程开销
- WAV header 解析/构建抽为独立函数，支持任意采样率和声道数

---

## [1.0.0] - 2026-04-05

### ✨ 新增功能
- 初始版本发布
- 支持小米 MiMo V2-TTS 语音合成 API
- 支持 3 种预置音色：
  - `mimo_default` - MiMo 默认音色
  - `default_zh` - 中文女声
  - `default_en` - 英文女声
- 支持风格控制标签 `<style>风格</style>`
- 支持多种输出格式（wav, pcm16）
- 支持非流式和流式调用模式

### 📦 命令行功能
- `--text` - 输入文本
- `--output` - 输出文件路径
- `--voice` - 音色选择
- `--format` - 输出格式
- `--stream` - 流式模式
- `--help` - 帮助信息

### 📚 文档
- SKILL.md - Skill 描述和触发条件
- README.md - 完整使用说明
- INSTALL.md - 快速安装指南
- VERSION - 版本信息
- CHANGELOG.md - 更新日志
- package.json - 依赖配置

### 🔧 技术实现
- 使用 OpenAI SDK 兼容格式调用 API
- 原生 Node.js 实现，无额外依赖
- 自动处理风格标签
- 完善的错误处理和提示

---

## 版本命名规范

遵循语义化版本 (Semantic Versioning)：
- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

格式：MAJOR.MINOR.PATCH (例如：1.0.0)
