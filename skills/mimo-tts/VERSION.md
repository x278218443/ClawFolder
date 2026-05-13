# MiMo TTS Skill 版本信息

## 当前版本
**v1.2.0** (2026-04-05)

## 版本历史

### v1.2.0 (2026-04-05) - 开发者体验增强
- ✅ 新增 stdin 管道输入支持
- ✅ 新增短参数 `-t` `-o` `-v` `-f` `-i` `-h`
- ✅ extractAudio 不再静默吞错，输出响应结构便于调试
- ✅ Style 正则支持属性和空格
- ✅ API 地址可通过 MIMO_API_BASE 环境变量覆盖
- ✅ tts.js 精简，移除重复 CLI 入口

### v1.1.0 (2026-04-05) - 稳定性与功能增强
- ✅ 修复 Shell 注入风险（移除 execSync，改为 require 调用）
- ✅ 自动文本分段（超 2000 字按句切分，段间 300ms 静音）
- ✅ 网络失败自动重试（最多 3 次，指数退避）
- ✅ 新增 `--input` 参数，支持从文件读取长文本
- ✅ 修复 WAV 合并采样率硬编码（实际读取 header）
- ✅ Style 标签跨段保持一致
- ✅ 请求超时从 30s 延长至 120s
- ✅ parseArgs 边界安全修复
- ✅ 输出显示音频时长、采样率、声道数

### v1.0.0 (2026-04-05) - 初始发布
- ✅ 支持 MiMo V2-TTS API 调用
- ✅ 支持 3 种预置音色（mimo_default, default_zh, default_en）
- ✅ 支持风格标签（<style>风格</style>）
- ✅ 支持多种输出格式（wav, pcm16）
- ✅ 命令行界面
- ✅ 完整的文档和安装指南
- ✅ OpenAI SDK 兼容格式

## 系统要求
- Node.js >= 14.0.0
- 环境变量 MIMO_API_KEY
- OpenClaw >= 1.0.0

## 兼容性
- Linux ✅
- macOS ✅
- Windows (WSL) ✅
