#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 自动化管线单任务调度脚本
# VERSION: v1.0.6 (真双轨锁机制 - 机器人绝不自动创建 lock)
# ------------------------------------------------------------------------------
VERSION="v1.0.6"

TASK_NAME=$1
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/${TASK_NAME}.log"

# 你的专属手动免打扰电闸（脚本只读，绝不创建）
MY_LOCK="$PROJECT_DIR/lock"
# 机器人自己排队防并发用的临时锁
ROBOT_LOCK="$PROJECT_DIR/pipeline.lock"
RUN_FLAG="$PROJECT_DIR/run"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

# ==============================================================================
# 双轨锁拦截机制
# ==============================================================================
# 1. 拦截点 A：如果你手动把 lockr 改名成了 lock，机器人老老实实原地秒退
if [ -d "$MY_LOCK" ]; then
    echo "=== [$TASK_NAME] Intercepted ($VERSION): $(date) (主人已挂锁，退出) ===" >> "$LOG_FILE"
    exit 0
fi

# 2. 拦截点 B：机器人尝试建立自己专属的防并发锁
if ! mkdir "$ROBOT_LOCK" 2>/dev/null; then
    echo "=== [$TASK_NAME] Skipped ($VERSION): $(date) (后台有相同任务在跑，跳过) ===" >> "$LOG_FILE"
    exit 0
fi

# 机器人的安全兜底：退出时只粉碎它自己的临时锁和红灯标识，绝对不碰你的 lock
trap 'rm -rf "$ROBOT_LOCK" "$RUN_FLAG" 2>/dev/null' EXIT INT TERM

# ==============================================================================
# 正常执行流程
# ==============================================================================
echo "=== [$TASK_NAME] Start ($VERSION): $(date) ===" >> "$LOG_FILE"

killall -9 "Microsoft Edge" 2>/dev/null
sleep 2

source venv/bin/activate

# 🛑 开启物理红灯
touch "$RUN_FLAG"

python3 "aes-feeds/${TASK_NAME}_downloader.py" >> "$LOG_FILE" 2>&1

# 🟢 湮灭物理红灯
rm -f "$RUN_FLAG" 2>/dev/null

echo "=== [$TASK_NAME] End ($VERSION): $(date) ===" >> "$LOG_FILE"