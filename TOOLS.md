# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## GitHub
- 仓库: https://github.com/x278218443/ClawFolder.git
- Token 存在 `.env` 的 `GITHUB_TOKEN` 变量中
- 推送方式: `git push -f origin main`（workspace 根目录）
- 注意: .gitignore 已配置（output/、node_modules/、*.mp4 等），勿提交大文件
- 如果 remote 报错，先 `git pull origin main --allow-unrelated-histories`

## MiMo TTS 配置
- API Base: https://token-plan-cn.xiaomimimo.com/v1
- API Key: 同 xiaomicoding chat key (tp- 开头)
- 音色: default_zh（中文女声）/ mimo_default
- 模型: mimo-v2-tts
- 风格标签: <style>撒娇</style>、<style>开心</style>、<style>东北话</style> 等

## 飞书语音消息
- 必须转 opus 格式才能识别为语音（WAV/MP3 会被当文件）
- ffmpeg -i input.wav -c:a libopus -b:a 32k -ar 16000 output.opus
- 发送时用 asVoice=true + filePath=xxx.opus

## MiniMax TTS 默认配置
- 音色：lovely_girl（萌萌女童）
- 模型：speech-2.8-hd
- 地区端点：api.minimaxi.com
- 用途：默认语音说话
