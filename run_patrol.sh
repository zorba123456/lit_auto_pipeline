#!/bin/bash
# AES-INTEL 管线巡查：写日志 + 日记，观察期用于复盘 KTN/各源健康状况
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/patrol.log"

mkdir -p "$LOG_DIR" "$LOG_DIR/patrol_diary"
cd "$PROJECT_DIR" || exit 1

echo "=== [patrol] Start: $(date) ===" >> "$LOG_FILE"
source venv/bin/activate
python3 pipeline_patrol.py 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "=== [patrol] End (exit=$EXIT_CODE): $(date) ===" >> "$LOG_FILE"
exit "$EXIT_CODE"
