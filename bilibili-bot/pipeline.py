"""
全自动 B站短视频流水线 - 主控制器
串联所有模块: 热点发现 → 脚本生成 → 视频生成 → 配音 → 合成 → 发布
"""
import os
import sys
import json
import time
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hot_topics import fetch_all_hot_topics, filter_for_video, save_hot_topics
from modules.script_writer import generate_script, save_script
from modules.video_gen import JimengClient, generate_clips_for_script
from modules.tts_gen import generate_scene_audio, generate_full_audio
from modules.video_assemble import assemble_video
from modules.bilibili_publish import publish_video

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.openclaw/workspace/bilibili-bot/logs/pipeline.log")),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class VideoPipeline:
    """全自动视频生产流水线"""

    def __init__(self):
        from config.settings import (
            OUTPUT_DIR, SCRIPTS_DIR, AUDIO_DIR, CLIPS_DIR, FINAL_DIR,
            JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY,
        )
        self.output_dir = OUTPUT_DIR
        self.scripts_dir = SCRIPTS_DIR
        self.audio_dir = AUDIO_DIR
        self.clips_dir = CLIPS_DIR
        self.final_dir = FINAL_DIR

        # 确保目录存在
        for d in [self.scripts_dir, self.audio_dir, self.clips_dir, self.final_dir]:
            os.makedirs(d, exist_ok=True)

        # 初始化即梦客户端
        self.jimeng = None
        if JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY:
            self.jimeng = JimengClient(JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY)
        else:
            logger.warning("即梦 API 未配置，视频生成将跳过")

        # 时间戳
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run(self, topic: str = None, max_videos: int = 1) -> list[dict]:
        """运行完整流水线
        Args:
            topic: 指定话题（None=自动从热点中选）
            max_videos: 最多生成几个视频
        Returns:
            [{"title": "...", "video_path": "...", "publish_result": {...}}, ...]
        """
        results = []

        # ===== Step 1: 热点发现 =====
        logger.info("=" * 50)
        logger.info("Step 1: 抓取热点...")
        if not topic:
            hot_topics = fetch_all_hot_topics()
            selected = filter_for_video(hot_topics, max_count=max_videos)
            if not selected:
                logger.error("没有找到合适的热点，退出")
                return results
            save_hot_topics(hot_topics, self.scripts_dir)
        else:
            selected = [{"title": topic, "platform": "manual", "hot_value": 0}]

        for i, topic_item in enumerate(selected):
            topic_title = topic_item["title"]
            logger.info(f"\n{'='*50}")
            logger.info(f"开始处理第 {i+1}/{len(selected)} 个话题: {topic_title}")

            try:
                result = self._process_single_topic(topic_title, i)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"处理话题失败 [{topic_title}]: {e}")
                import traceback
                traceback.print_exc()

        # ===== 汇总 =====
        logger.info(f"\n{'='*50}")
        logger.info(f"流水线完成! 共处理 {len(results)}/{len(selected)} 个话题")
        for r in results:
            status = "✅" if r.get("publish_result", {}).get("success") else "❌"
            logger.info(f"  {status} {r.get('title', 'untitled')}")

        return results

    def _process_single_topic(self, topic: str, index: int) -> dict:
        """处理单个话题的完整流程"""
        run_dir = os.path.join(self.output_dir, f"run_{self.timestamp}_{index}")
        os.makedirs(run_dir, exist_ok=True)

        # ===== Step 2: 脚本生成 =====
        logger.info("Step 2: 生成脚本...")
        script = generate_script(topic)
        if not script:
            logger.error("脚本生成失败")
            return None

        script_path = save_script(script, self.scripts_dir)
        logger.info(f"脚本: {script['title']}")
        logger.info(f"场景数: {len(script['scenes'])}, 总时长: {script.get('total_duration', '?')}秒")

        # ===== Step 3: 即梦生成视频 =====
        clips = []
        if self.jimeng:
            logger.info("Step 3: 即梦生成视频片段...")
            clips_dir = os.path.join(run_dir, "clips")
            os.makedirs(clips_dir, exist_ok=True)
            clips = generate_clips_for_script(script, self.jimeng, clips_dir)
        else:
            logger.warning("Step 3: 即梦未配置，跳过视频生成")
            logger.warning("  → 使用测试模式: 生成纯色占位视频")
            clips = self._generate_placeholder_clips(script, run_dir)

        if not clips:
            logger.error("无视频片段，跳过后续步骤")
            return None

        # ===== Step 4: TTS 配音 =====
        logger.info("Step 4: 生成配音...")
        audio_dir = os.path.join(run_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        audio_files = generate_scene_audio(script, audio_dir)

        if not audio_files:
            logger.warning("配音生成失败，使用静音")
            audio_files = self._generate_silence_audio(script, audio_dir)

        # ===== Step 5: 合成视频 =====
        logger.info("Step 5: 合成最终视频...")
        safe_title = "".join(c for c in script["title"][:30] if c.isalnum() or c in "_ -")
        final_filename = f"{self.timestamp}_{safe_title}.mp4"
        final_path = os.path.join(self.final_dir, final_filename)

        video_path = assemble_video(
            clip_paths=clips,
            audio_files=audio_files,
            output_path=final_path,
            add_srt=True,
        )

        if not video_path:
            logger.error("视频合成失败")
            return None

        # ===== Step 6: 发布到 B站 =====
        logger.info("Step 6: 发布到B站...")
        publish_result = publish_video(
            video_path=video_path,
            title=script["title"],
            desc=script.get("narration", "")[:250],
            tags=script.get("tags", ["热点", "新闻", "AI"]),
        )

        return {
            "title": script["title"],
            "topic": topic,
            "video_path": video_path,
            "script_path": script_path,
            "publish_result": publish_result,
            "timestamp": self.timestamp,
        }

    def _generate_placeholder_clips(self, script: dict, run_dir: str) -> list[str]:
        """生成占位视频片段（测试用）"""
        import subprocess
        clips_dir = os.path.join(run_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        clips = []

        for i, scene in enumerate(script.get("scenes", [])):
            duration = scene.get("duration", 5)
            output = os.path.join(clips_dir, f"placeholder_{i:02d}.mp4")

            # 生成纯色占位视频
            colors = ["0x1a1a2e", "0x16213e", "0x0f3460", "0x533483", "0xe94560"]
            color = colors[i % len(colors)]

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i",
                f"color=c={color}:s=1080x1920:d={duration}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)

            if os.path.exists(output):
                clips.append(output)

        return clips

    def _generate_silence_audio(self, script: dict, audio_dir: str) -> list[dict]:
        """生成静音音频（测试用）"""
        import subprocess
        audio_files = []

        for i, scene in enumerate(script.get("scenes", [])):
            duration = scene.get("duration", 5)
            output = os.path.join(audio_dir, f"silence_{i:02d}.mp3")

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=stereo",
                "-t", str(duration),
                "-c:a", "libmp3lame",
                output
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)

            if os.path.exists(output):
                audio_files.append({
                    "scene_id": scene.get("scene_id", i + 1),
                    "audio_path": output,
                    "duration": duration,
                    "narration": scene.get("narration", ""),
                })

        return audio_files


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="B站全自动短视频流水线")
    parser.add_argument("--topic", type=str, help="指定话题（不指定则自动抓热点）")
    parser.add_argument("--count", type=int, default=1, help="生成视频数量")
    parser.add_argument("--dry-run", action="store_true", help="试运行（不发布）")
    args = parser.parse_args()

    pipeline = VideoPipeline()

    if args.dry_run:
        logger.info("=== 试运行模式 ===")
        # 只测试前几步
        hot_topics = fetch_all_hot_topics()
        selected = filter_for_video(hot_topics, max_count=args.count)
        for t in selected:
            logger.info(f"  热点: {t['title']} (热度: {t.get('hot_value', 0)})")
        return

    results = pipeline.run(topic=args.topic, max_videos=args.count)

    # 保存结果记录
    result_file = os.path.join(
        os.path.expanduser("~/.openclaw/workspace/bilibili-bot/logs"),
        f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"结果保存到: {result_file}")


if __name__ == "__main__":
    main()
