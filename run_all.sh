#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 历史全量心跳脚本（已废弃定时，仅保留作手动串行测试入口）
# VERSION: v1.1.0-no-cron (各通道已独立 cron；CMA 见工作日 10:30/18:30)
# ------------------------------------------------------------------------------
VERSION="v1.1.0-no-cron"
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"

cd "$PROJECT_DIR" || exit 1

echo "ℹ️ run_all 已不再挂 cron。各通道请用独立 run_task.sh 或见 crontab.backup。"
echo "   手动全量示例: ./run_task.sh ktn && ./run_task.sh cnki && ./run_task.sh cma"
exit 0
