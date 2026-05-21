#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 自动化管线单任务调度脚本
# VERSION: v1.0.4 (方案 B 物理红绿灯咬合器，精准对齐 aes-feeds 子目录)
# ------------------------------------------------------------------------------
VERSION="v1.0.4"

TASK_NAME=$1
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/${TASK_NAME}.log"
LOCK_DIR="$PROJECT_DIR/lock"
RUN_FLAG="$PROJECT_DIR/run"

# 创建日志文件夹并进入项目根目录
mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

# ==============================================================================
# 极简互斥锁机制
# ==============================================================================
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "=== [$TASK_NAME] Skipped ($VERSION): $(date) (互斥锁生效，跳过) ===" >> "$LOG_FILE"
    exit 0
fi

# 安全防线：确保无论脚本发生何种崩溃，退出时必须物理粉碎所有状态锁
trap 'rm -rf "$LOCK_DIR" "$RUN_FLAG" 2>/dev/null' EXIT INT TERM

# ==============================================================================
# 正常执行流程
# ==============================================================================
echo "=== [$TASK_NAME] Start ($VERSION): $(date) ===" >> "$LOG_FILE"

# 强杀残留 Edge 进程
killall -9 "Microsoft Edge" 2>/dev/null
sleep 2

# 激活统一的 Python 虚拟环境
source venv/bin/activate

# 🛑 亮红灯：创建物理运行标识
touch "$RUN_FLAG"

# 物理对齐执行
python3 "aes-feeds/${TASK_NAME}_downloader.py" >> "$LOG_FILE" 2>&1

# 🟢 灭红灯：释放运行标识
rm -f "$RUN_FLAG" 2>/dev/null

echo "=== [$TASK_NAME] End ($VERSION): $(date) ===" >> "$LOG_FILE"