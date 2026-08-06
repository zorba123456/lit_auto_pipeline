#!/bin/bash
# AES 微信DOI 自动扫描调度包装（§D50 落地）
# 用法: ./run_wechat_scan.sh incremental | full
#   incremental = 每日增量（白名单+水位，只扫新入库）
#   full        = 每周全量（不限白名单+增补命中池）
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/wechat_scan.log"

MODE=$1
[ -z "$MODE" ] && MODE="incremental"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1
source venv/bin/activate

echo "=== [wechat_scan:$MODE] Start: $(date) ===" >> "$LOG_FILE"
python3 -m aes_workflow.wechat_scan_cron --mode "$MODE" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "=== [wechat_scan:$MODE] End (exit=$EXIT_CODE): $(date) ===" >> "$LOG_FILE"
exit "$EXIT_CODE"
