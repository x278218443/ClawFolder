# API Key 配置指南

## 必需

### 火山方舟 ARK API (Seedream 图片 + Seedance 视频)

1. 注册：https://www.volcengine.com/
2. 开通方舟大模型服务
3. 获取 API Key（格式：`ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）
4. 写入 `~/.openclaw/workspace/ai-video-pipeline/.env`：
   ```
   ARK_API_KEY=ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

**模型 ID：**
- 图片：`doubao-seedream-5-0-260128`
- 视频：`doubao-seedance-1-5-pro-251215`

**图片 API 注意事项：**
- 端点：`POST https://ark.cn-beijing.volces.com/api/v3/images/generations`
- 最小分辨率：3686400 像素（推荐 2560x1440）
- 认证：`Authorization: Bearer {ARK_API_KEY}`

**视频 API 注意事项：**
- 创建任务：`POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
- 查询结果：`GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}`
- 异步轮询，约 100-120 秒生成

## 可选

### MiMo TTS (小米语音合成)

- 自动从 `~/.openclaw/openclaw.json` 的 xiaomicoding provider 读取 API Key
- 音色：冰糖（默认）、茉莉、苏打、白桦
- 模型：mimo-v2-tts

### DashScope (阿里备用图片生成)

- 注册：https://dashscope.aliyun.com/
- 获取 API Key（格式：`sk-xxxxxxxx`）
- 写入 `.env`：`DASHSCOPE_API_KEY=sk-xxxxxxxx`
- 模型：`wanx-v1`
