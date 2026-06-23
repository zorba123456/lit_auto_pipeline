#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 自动化管线单任务调度脚本
# VERSION: v1.0.9-domestic-daytime (国内源白天：CNKI RSS 静默；CMA 前台浏览器深度)
# ------------------------------------------------------------------------------
VERSION="v1.0.9-domestic-daytime"

TASK_NAME=$1
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/${TASK_NAME}.log"

# 读取全局状态 (真理之源)
STATUS=$(cat "$PROJECT_DIR/.status" 2>/dev/null)

# ==============================================================================
# 第一层门禁：状态授权拦截 (全局电闸)
# ==============================================================================
# 1. 如果是从终端手动执行 ([ -t 0 ])，直接放行，无视 AUTO/MANUAL
# 2. MANUAL 下仍允许 cron 触发，分两类（「放行」≠「静默」）：
#    - 真·静默（无浏览器前台）：ktn, lww
#    - cnki RSS cron 已暂停（2026-06-23）；手动 ./run_task.sh cnki 仍可跑 --mode rss 兜底
#    - 前台浏览器（会弹 Edge，headless=False）：cma（工作日 10:30/18:30）
if [ ! -t 0 ] && [ "$STATUS" != "AUTO" ]; then
    case "$TASK_NAME" in
        ktn|lww|cnki|cma) ;;
        *) exit 0 ;;
    esac
fi

# 机器人自己排队防并发用的临时锁
ROBOT_LOCK="$PROJECT_DIR/pipeline.lock"
RUN_FLAG="$PROJECT_DIR/run"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

# ==============================================================================
# 第二层门禁：机器人排队防并发机制
# ==============================================================================
# 确保 LWW、CMA、KTN、CNKI 在被触发时不会互相抢占 Edge 资源
if ! mkdir "$ROBOT_LOCK" 2>/dev/null; then
    echo "=== [$TASK_NAME] Skipped ($VERSION): $(date) (后台有相同任务在跑，跳过) ===" >> "$LOG_FILE"
    exit 0
fi

# 机器人的安全兜底：退出时粉碎它自己的临时锁和红灯标识
trap 'rm -rf "$ROBOT_LOCK" "$RUN_FLAG" 2>/dev/null' EXIT INT TERM

# ==============================================================================
# 正常执行流程
# ==============================================================================
echo "=== [$TASK_NAME] Start ($VERSION): $(date) ===" >> "$LOG_FILE"
if [ "$TASK_NAME" = "cma" ]; then
    echo "[$TASK_NAME] 执行模式: 前台 Edge 浏览器（非后台静默）" >> "$LOG_FILE"
fi

# 只有涉及浏览器自动化（会抢占焦点）的任务，才需要清理残留的 Edge 进程
if [ "$TASK_NAME" = "cma" ] || [ "$TASK_NAME" = "lww" ]; then
    killall -9 "Microsoft Edge" 2>/dev/null
    sleep 2
fi

source venv/bin/activate

# 🛑 开启物理红灯
touch "$RUN_FLAG"

if [ "$TASK_NAME" = "cnki" ]; then
    # RSS 模式保留作兜底；cron 已暂停，日常由 prompt_cnki_web.sh --mode web 更新
    python3 "aes-feeds/${TASK_NAME}_downloader.py" --mode rss 2>&1 | tee -a "$LOG_FILE"
else
    python3 "aes-feeds/${TASK_NAME}_downloader.py" 2>&1 | tee -a "$LOG_FILE"
fi

# 🟢 湮灭物理红灯
rm -f "$RUN_FLAG" 2>/dev/null

echo "=== [$TASK_NAME] End ($VERSION): $(date) ===" >> "$LOG_FILE"