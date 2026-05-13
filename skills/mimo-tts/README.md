# MiMo TTS Skill

小米 MiMo V2-TTS 语音合成 OpenClaw Skill，将文本转换为自然流畅的语音。

## 功能特性

- ✅ **多种音色**：支持中文、英文等多种预置音色
- ✅ **风格控制**：支持语速、情绪、角色扮演、方言等多种风格
- ✅ **细粒度控制**：支持呼吸、停顿、咳嗽等语气标签
- ✅ **多种格式**：支持 wav、pcm16 等输出格式
- ✅ **OpenAI 兼容**：使用标准 Chat Completions API 格式

## 快速开始

### 基本用法

```bash
mimo-tts --text "你好，欢迎使用 MiMo 语音合成" --output greeting.wav
```

### 选择音色

```bash
# 中文女声
mimo-tts --text "你好世界" --voice default_zh --output hello-zh.wav

# 英文女声
mimo-tts --text "Hello World" --voice default_en --output hello-en.wav

# 默认音色
mimo-tts --text "你好" --voice mimo_default --output default.wav
```

### 风格控制

#### 整体风格

在文本前添加 `<style>风格</style>` 标签：

```bash
# 情绪变化
mimo-tts --text "<style>开心</style>今天真是太棒了！" --output happy.wav
mimo-tts --text "<style>悲伤</style>为什么会这样..." --output sad.wav
mimo-tts --text "<style>生气</style>你怎么能这样！" --output angry.wav

# 语速控制
mimo-tts --text "<style>变快</style>快点快点来不及了！" --output fast.wav
mimo-tts --text "<style>变慢</style>请...慢...一...点..." --output slow.wav

# 方言
mimo-tts --text "<style>东北话</style>哎呀妈呀，这天儿真冷啊！" --output dongbei.wav
mimo-tts --text "<style>四川话</style>巴适得板！" --output sichuan.wav
mimo-tts --text "<style>粤语</style>呢个真係好正啊！" --output cantonese.wav
mimo-tts --text "<style>台湾腔</style>真的假的啦～" --output taiwan.wav

# 角色扮演
mimo-tts --text "<style>孙悟空</style>俺老孙来也！" --output wukong.wav
mimo-tts --text "<style>林黛玉</style>花谢花飞花满天..." --output daiyu.wav

# 特殊风格
mimo-tts --text "<style>悄悄话</style>告诉你一个秘密..." --output whisper.wav
mimo-tts --text "<style>夹子音</style>你好呀～" --output jiazi.wav

# 唱歌
mimo-tts --text "<style>唱歌</style>原谅我这一生不羁放纵爱自由" --output sing.wav
```

#### 细粒度控制

使用括号和描述实现更精细的语气控制：

```bash
mimo-tts --text "（紧张，深呼吸）呼……冷静，冷静。（语速加快）自我介绍已经背了五十遍了" --output nervous.wav

mimo-tts --text "（极其疲惫）师傅……到地方了叫我一声……（长叹一口气）我先眯一会儿" --output tired.wav

mimo-tts --text "如果我当时……（沉默片刻）哪怕再坚持一秒钟，结果是不是就不一样了？（苦笑）" --output regret.wav

mimo-tts --text "（提高音量喊话）大姐！这鱼新鲜着呢！早上刚捞上来的！" --output shouting.wav
```

## 命令行参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--text` | ✅ | - | 要合成的文本内容 |
| `--output` | ✅ | - | 输出音频文件路径 |
| `--voice` | ❌ | `mimo_default` | 音色选择 |
| `--format` | ❌ | `wav` | 输出格式（wav/pcm16） |
| `--stream` | ❌ | `false` | 流式模式（暂不支持） |

## 可用音色

| 音色代码 | 描述 | 适用场景 |
|---------|------|---------|
| `mimo_default` | MiMo-默认 | 通用场景 |
| `default_zh` | MiMo-中文女声 | 中文内容 |
| `default_en` | MiMo-英文女声 | 英文内容 |

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `MIMO_API_KEY` | MiMo API Key（必填） |

## 输出说明

- 输出文件自动保存到指定路径
- 相对路径会保存到 workspace 目录
- 建议使用绝对路径避免混淆

## 注意事项

1. **文本位置**：语音合成的文本必须放在 `assistant` 角色的消息中（脚本已自动处理）
2. **风格标签**：`<style>` 标签必须放在文本开头
3. **唱歌模式**：必须仅使用 `<style>唱歌</style>` 标签，后接歌词
4. **流式模式**：流式调用时必须使用 `pcm16` 格式
5. **API 限速**：请参考 MiMo 官方文档了解当前限速策略

## 计费说明

- 当前状态：限时免费
- 用量查询：访问 [MiMo 控制台](https://platform.xiaomimimo.com/#/console/usage)

## 示例场景

### 1. 问候语生成
```bash
mimo-tts --text "你好，欢迎使用我们的服务！" --voice default_zh --output welcome.wav
```

### 2. 通知播报
```bash
mimo-tts --text "<style>开心</style>您的订单已发货，请注意查收！" --output notification.wav
```

### 3. 故事讲述
```bash
mimo-tts --text "（神秘地）很久很久以前，在一个遥远的王国……" --output story.wav
```

### 4. 多语言支持
```bash
mimo-tts --text "Hello! Bonjour! こんにちは！" --voice default_en --output multilingual.wav
```

## 故障排除

### 常见错误

**错误：未设置 MIMO_API_KEY**
```
错误：未设置 MIMO_API_KEY 环境变量
请设置：export MIMO_API_KEY=your_api_key_here
```
**解决**：设置环境变量 `export MIMO_API_KEY=your_key`

**错误：HTTP 401**
```
API 请求失败：HTTP 401
```
**解决**：API Key 无效，请检查是否正确

**错误：HTTP 404**
```
API 请求失败：HTTP 404
```
**解决**：检查 API 端点，当前使用 `https://api.xiaomimimo.com/v1/chat/completions`

**错误：请求超时**
```
请求超时（30 秒）
```
**解决**：文本过长或网络问题，尝试缩短文本

## 相关链接

- [MiMo 开放平台](https://platform.xiaomimimo.com)
- [API 文档](https://platform.xiaomimimo.com/#/docs/usage-guide/speech-synthesis)
- [控制台](https://platform.xiaomimimo.com/#/console/balance)

## 技术支持

如有问题，请访问 MiMo 开放平台文档或联系技术支持。
