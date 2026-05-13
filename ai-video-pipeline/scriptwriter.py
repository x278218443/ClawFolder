"""
AI 短视频流水线 - 多话题脚本生成模块
橘鸦Juya AI 早报风格：6-12 条新闻，标题故事 + 快速资讯
"""
import requests
import json
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, SCRIPT_MAX_CHARS


SYSTEM_PROMPT = """你是一位专业的 AI 大模型科技新闻脚本编辑，风格参考"黑鸦Heya"。

你的内容聚焦（严格限定）：
- 大模型发布/升级/更新（GPT、Claude、Gemini、豆包、DeepSeek、Kimi 等）
- AI 产品商业化（订阅、付费、API）
- AI 安全/伦理/监管事件
- AI 融资/创业（必须与 AI 模型直接相关）
- 模型能力突破（推理、多模态、幻觉、对齐等）

❌ 不收录：芯片算力、机器人、自动驾驶、硬件产品、一般科技公司财报/股价

要求：
1. 新闻播报体，客观专业，像新闻联播主播
2. 用"据报道"、"据悉"等新闻用语
3. 不说"大家好"、"我是"等开场白，直接进入新闻
4. 中英文混用：产品名/公司名用英文，描述用中文
5. 每期 6-10 条新闻（根据实际 AI 模型新闻数量决定）
6. 第一条是标题故事，旁白要详细（背景+影响），约 15-25 秒
7. 后续新闻简短概括，约 8-12 秒
8. 简短过渡："与此同时"、"另外"、"值得一提的是"
9. 结尾无总结，最后一条新闻说完即结束
10. 总字数控制在 600-900 字
11. image_query 用英文描述该新闻相关的场景或人物，适合 AI 生图

新闻筛选规则（严格遵守）：
- ✅ 必须收录：实际发生的事件（发布/更新/融资/安全事件），与大模型/AI产品直接相关
- ✅ 必须收录：今天或昨天发生
- ❌ 直接跳过：鸡汤/感悟/观点/预测/旧闻/广告/无具体事件
- ❌ 直接跳过：芯片/硬件/机器人/自动驾驶等非大模型新闻
- ❌ 直接跳过：一般科技公司动态（除非与大模型直接相关）

新闻筛选原则：
- 涉及知名 AI 产品/公司（OpenAI/Anthropic/Google/字节/百度/阿里/智谱等）
- 有具体事件（发布、升级、事故、融资）
- 对 AI 行业有实际影响
- 非广告、非鸡汤、非旧闻

输出格式（JSON）：
{{
  "title": "视频标题（头条新闻的简短标题）",
  "date": "YYYY-MM-DD",
  "segments": [
    {{
      "index": 1,
      "headline": "新闻标题（不超过20字）",
      "narration": "详细旁白（背景+影响，15-25秒）",
      "image_query": "English description for AI image generation"
    }},
    {{
      "index": 2,
      "headline": "新闻标题2",
      "narration": "简短旁白（8-12秒）",
      "image_query": "English description"
    }}
  ],
  "tags": ["标签1", "标签2"]
}}"""


def generate_script(news_items: list[dict], max_chars: int = None) -> dict:
    """
    将新闻素材发给 LLM，生成多话题 AI 早报脚本

    返回: {
        "title": str,
        "date": str,
        "segments": [{"index": int, "headline": str, "narration": str, "image_query": str}],
        "tags": list
    }
    """
    if max_chars is None:
        max_chars = SCRIPT_MAX_CHARS

    if not LLM_API_KEY:
        print("[脚本] LLM API Key 未配置，无法生成脚本")
        return None

    # 构造素材摘要
    material = ""
    for i, item in enumerate(news_items[:15], 1):  # 最多用 15 条
        material += f"\n{i}. 【{item.get('source', '未知')}】{item['title']}\n"
        if item.get("summary"):
            material += f"   摘要：{item['summary'][:200]}\n"

    if not material.strip():
        print("[脚本] 没有可用的新闻素材")
        return None

    prompt = f"""以下是今天的热点新闻素材，请整合成一期 AI 早报脚本。
选取最有价值的 6-12 条新闻，第一条作为标题故事要详细展开。

总字数控制在 {max_chars} 字以内。

新闻素材：{material}"""

    try:
        resp = requests.post(
            f"{LLM_API_BASE}/chat/completions",
            headers={
                "api-key": LLM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 3000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 尝试解析 JSON（兼容 markdown code block）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # 验证字段
        assert "segments" in result, "缺少 segments 字段"
        assert "title" in result, "缺少 title 字段"
        assert len(result["segments"]) >= 1, "segments 不能为空"

        # 确保每个 segment 有必需字段
        for i, seg in enumerate(result["segments"]):
            seg.setdefault("index", i + 1)
            seg.setdefault("headline", "")
            seg.setdefault("narration", "")
            seg.setdefault("image_query", "technology")

        # 检查总字数
        total_chars = sum(len(seg.get("narration", "")) for seg in result["segments"])
        if total_chars > max_chars + 100:
            print(f"[脚本] ⚠️ 总字数 {total_chars} 超出限制 {max_chars}，将尝试裁剪")
            _trim_narration(result["segments"], max_chars)

        print(f"[脚本] 生成成功: {result['title']}")
        print(f"[脚本] 新闻条数: {len(result['segments'])}")
        print(f"[脚本] 总字数: {total_chars}")
        return result

    except json.JSONDecodeError as e:
        print(f"[脚本] JSON 解析失败: {e}")
        print(f"[脚本] 原始响应: {content[:500]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[脚本] LLM API 调用失败: {e}")
        return None
    except Exception as e:
        print(f"[脚本] 生成失败: {e}")
        return None


def _trim_narration(segments: list[dict], max_chars: int):
    """裁剪旁白总字数到限制内"""
    total = sum(len(s.get("narration", "")) for s in segments)
    if total <= max_chars:
        return

    # 保留第一条（标题故事）的长度，压缩后面的
    head = segments[0]
    head_len = len(head.get("narration", ""))
    remaining_chars = max_chars - head_len

    other_segments = segments[1:]
    if not other_segments:
        return

    other_total = sum(len(s.get("narration", "")) for s in other_segments)
    if other_total <= 0:
        return

    ratio = remaining_chars / other_total
    for seg in other_segments:
        narration = seg.get("narration", "")
        if len(narration) > 0:
            target_len = max(30, int(len(narration) * ratio))
            if len(narration) > target_len:
                seg["narration"] = narration[:target_len].rstrip("，。、") + "。"


if __name__ == "__main__":
    # 测试用
    test_news = [
        {"title": "GPT-5 即将发布，OpenAI CEO 透露重大突破", "summary": "据外媒报道，OpenAI 计划在今年夏季发布 GPT-5，CEO Sam Altman 表示这将是 AI 领域的重大里程碑。", "source": "科技日报"},
        {"title": "苹果 Vision Pro 2 曝光：更轻更便宜", "summary": "供应链消息显示，苹果正在开发第二代 Vision Pro，重量减轻 30%，价格下调至 2500 美元。", "source": "36氪"},
        {"title": "豆包推出订阅制，月费最高五百元", "summary": "字节跳动旗下 AI 助手豆包拟推三档订阅服务。", "source": "澎湃新闻"},
    ]
    result = generate_script(test_news)
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
