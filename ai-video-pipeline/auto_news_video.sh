#!/bin/bash
# 自动 AI 早报视频生成脚本
# 用法: ./auto_news_video.sh [--now] [--news-file /path/to/news.json]
#   --now: 立即执行，不等待
#   --news-file: 使用已有的新闻 JSON 文件

set -e
cd "$(dirname "$0")"

WAIT=true
NEWS_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --now) WAIT=false; shift ;;
        --news-file) NEWS_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# 等待到 00:05
if [ "$WAIT" = true ]; then
    TARGET_HOUR=0 TARGET_MIN=5
    NOW_EPOCH=$(date +%s)
    TODAY=$(date +%Y-%m-%d)
    TARGET_EPOCH=$(date -d "${TODAY} ${TARGET_HOUR}:${TARGET_MIN}:00" +%s 2>/dev/null || echo 0)

    # 如果目标时间已过，设为明天
    if [ "$TARGET_EPOCH" -le "$NOW_EPOCH" ]; then
        TOMORROW=$(date -d "+1 day" +%Y-%m-%d)
        TARGET_EPOCH=$(date -d "${TOMORROW} ${TARGET_HOUR}:${TARGET_MIN}:00" +%s)
    fi

    SLEEP_SEC=$(( TARGET_EPOCH - NOW_EPOCH ))
    echo "[定时] 等待 ${SLEEP_SEC} 秒到目标时间..."
    sleep "$SLEEP_SEC"
fi

echo "=========================================="
echo "  AI 早报自动视频生成"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

SKILL_DIR="$(dirname "$0")/../skills/ai-news-video"
PIPELINE_DIR="$(dirname "$0")"
OUTPUT_DIR="${PIPELINE_DIR}/output"
TODAY=$(date +%Y%m%d)

# Step 1: 抓取新闻
if [ -z "$NEWS_FILE" ]; then
    NEWS_FILE="${OUTPUT_DIR}/news_${TODAY}.json"
    mkdir -p "$OUTPUT_DIR"
    echo -e "\n[1/2] 抓取今日 AI 新闻..."
    python3 "${SKILL_DIR}/scripts/fetch_news.py" 7 "$NEWS_FILE" 2>&1
    if [ ! -f "$NEWS_FILE" ]; then
        echo "❌ 新闻抓取失败，退出"
        exit 1
    fi
    echo "✅ 新闻已保存: $NEWS_FILE"
else
    echo -e "\n[1/2] 使用已有新闻文件: $NEWS_FILE"
fi

# Step 2: 生成视频
echo -e "\n[2/2] 生成动画板书视频..."
RESULT=$(python3 "${PIPELINE_DIR}/make_board_live.py" --news-json "$NEWS_FILE" 2>&1)
echo "$RESULT"

# 提取输出文件路径
FINAL_PATH=$(echo "$RESULT" | grep -oP '文件: \K.*' | tail -1)

if [ -n "$FINAL_PATH" ] && [ -f "$FINAL_PATH" ]; then
    SIZE=$(du -h "$FINAL_PATH" | cut -f1)
    echo -e "\n🎉 视频生成完成！"
    echo "  路径: $FINAL_PATH"
    echo "  大小: $SIZE"
    echo "$FINAL_PATH" > "${OUTPUT_DIR}/latest_video.txt"

    # Step 3: 发布到 B站
    echo -e "\n[3/4] 发布到 B站..."
    python3 "${PIPELINE_DIR}/bilibili_publish.py" --video "$FINAL_PATH" 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ 已发布到 B站"
    else
        echo "⚠️ B站发布失败，视频保存在: $FINAL_PATH"
    fi

    # Step 4: 推送视频到飞书
    echo -e "\n[4/4] 推送视频到飞书..."
    FEISHU_TARGET="user:ou_74504c7998ca288e6531039420584403"
    openclaw message send --channel feishu \
        --target "$FEISHU_TARGET" \
        --media "$FINAL_PATH" \
        --message "📺 今日 AI 早报已送达" 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ 视频已推送到飞书"
    else
        echo "⚠️ 飞书推送失败，视频保存在: $FINAL_PATH"
    fi
else
    echo -e "\n❌ 视频生成失败"
    exit 1
fi
