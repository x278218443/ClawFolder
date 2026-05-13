"""
脚本生成模块 - 用 AI 根据热点生成视频脚本
输出: 旁白文案 + 分镜描述 + 即梦提示词
"""
import json
import os
from datetime import datetime
from openai import OpenAI

# 初始化 MiMo 客户端
def get_client():
    from config.settings import MIMO_API_KEY, MIMO_BASE_URL
    return OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)


SYSTEM_PROMPT = """你是一个专业的短视频脚本编剧，专门为B站制作信息量大、节奏快、有吸引力的短视频。

## 要求
- 视频时长控制在 60 秒左右
- 开头3秒必须有钩子（震撼/疑问/反转），留住观众
- 信息密度高，每句话都有价值
- 语言风格：口语化、有网感、不啰嗦
- 结尾引导互动（点赞/关注/评论）

## 输出格式 (严格 JSON)
```json
{
    "title": "B站标题（要有吸引力，可以用emoji）",
    "cover_text": "封面文字（6-10个字）",
    "tags": ["标签1", "标签2", "标签3"],
    "narration": "完整的旁白文案（纯文本，约200-300字）",
    "scenes": [
        {
            "scene_id": 1,
            "duration": 5,
            "narration": "这一段的旁白",
            "visual_desc": "画面描述（中文，给即梦AI用）",
            "jimeng_prompt": "即梦生成提示词（中文，详细的画面描述，包含风格、色调、构图）",
            "text_overlay": "画面上叠加的文字（可选）"
        }
    ]
}
```

## 画面描述技巧 (给即梦用)
- 指定风格：如"电影质感"、"二次元"、"3D渲染"、"写实摄影"
- 指定色调：如"暖色调"、"科技蓝"、"黑白"
- 指定构图：如"特写"、"全景"、"俯瞰"、"侧面"
- 指定情绪：如"紧张"、"温馨"、"震撼"
- 不要出现文字、字母、数字（AI生图不擅长这些）
- 每个场景描述控制在 50-80 字

## 注意
- 只输出 JSON，不要有其他内容
- scenes 数量 8-12 个
- 总时长 = 所有 scene 的 duration 之和 ≈ 60 秒
"""


def generate_script(topic: str, extra_context: str = "") -> dict:
    """根据热点话题生成视频脚本"""
    client = get_client()
    from config.settings import MIMO_MODEL

    user_prompt = f"""请根据以下热点话题生成一个短视频脚本：

话题：{topic}
{f'背景信息：{extra_context}' if extra_context else ''}

要求：
1. 适合B站短视频的风格
2. 信息量大，节奏快
3. 画面要有冲击力
4. 每个场景的即梦提示词要详细可用

请严格按 JSON 格式输出。"""

    try:
        response = client.chat.completions.create(
            model=MIMO_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=4000,
        )

        content = response.choices[0].message.content.strip()

        # 提取 JSON (处理可能的 markdown 包裹)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        script = json.loads(content)

        # 验证必要字段
        required_fields = ["title", "narration", "scenes"]
        for field in required_fields:
            if field not in script:
                raise ValueError(f"脚本缺少字段: {field}")

        # 计算总时长
        total_duration = sum(s.get("duration", 5) for s in script["scenes"])
        script["total_duration"] = total_duration
        script["generated_at"] = datetime.now().isoformat()
        script["source_topic"] = topic

        print(f"[脚本] 生成完成: {script['title']}")
        print(f"[脚本] 场景数: {len(script['scenes'])}, 总时长: {total_duration}秒")

        return script

    except json.JSONDecodeError as e:
        print(f"[脚本] JSON 解析失败: {e}")
        print(f"[脚本] 原始内容: {content[:500]}")
        return None
    except Exception as e:
        print(f"[脚本] 生成失败: {e}")
        return None


def generate_scripts_batch(topics: list[dict], max_count: int = 3) -> list[dict]:
    """批量生成脚本"""
    scripts = []
    for i, topic in enumerate(topics[:max_count]):
        print(f"\n[脚本] 正在生成第 {i+1}/{min(len(topics), max_count)} 个...")
        title = topic.get("title", "")
        script = generate_script(title)
        if script:
            scripts.append(script)

    return scripts


def save_script(script: dict, output_dir: str = ".") -> str:
    """保存脚本到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = script.get("title", "untitled")[:20].replace("/", "_").replace(" ", "_")
    filepath = os.path.join(output_dir, f"script_{timestamp}_{safe_title}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"[脚本] 保存到 {filepath}")
    return filepath


if __name__ == "__main__":
    # 测试
    test_topic = "胖东来正式起诉博主惊梦人"
    script = generate_script(test_topic)
    if script:
        print(json.dumps(script, ensure_ascii=False, indent=2))
