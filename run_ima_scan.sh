#!/bin/bash
# IMA 巡查更新（scan-only，不下载、不归并，仅供人眼）→ 导入工作台 ima_update
# 用法: ./run_ima_scan.sh
#   1) ima_patrol.py --scan-only : 启动模拟器→扫清单→导 _scan_*.json→关模拟器(不下载)
#   2) ima_ingest.py             : 读最新清单→【不查重直接追加导入】(discovery_type=ima_update)
# 触发: crontab 每天 11:05 / 18:05（IMA 独立模拟器）
# 说明: 仅爬取更新文件名,不做 --normalize 标题反查归一,不查重(用户定策,仅供人眼筛查).
LOG_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/ima_scan.log"
cd /Users/meiyiwangluokeji/coding/aes-workbench || exit 1

echo "=== [ima:scan-only] Start: $(date) ===" >> "$LOG"

# 1) 模拟器巡查拉清单（scan-only,不下载）
PYIMA="$HOME/.hermes/scripts/venv_ima/bin/python"
"$PYIMA" "$HOME/.hermes/scripts/ima_patrol.py" --scan-only >> "$LOG" 2>&1
SCAN_EXIT=$?
echo "[ima:scan-only] patrol exit=$SCAN_EXIT $(date)" >> "$LOG"

# 2) 导入工作台（即使 patrol 失败也尝试 ingest 已有最新清单,但失败时跳过避免误清洗）
if [ "$SCAN_EXIT" -eq 0 ]; then
    source .venv/bin/activate 2>/dev/null
    unset PYTHONPATH
    python3 ima_ingest.py >> "$LOG" 2>&1
    echo "[ima:scan-only] ingest done $(date)" >> "$LOG"
else
    echo "[ima:scan-only] ⚠️ patrol 失败(exit=$SCAN_EXIT), 跳过 ingest 避免误清洗" >> "$LOG"
fi

echo "=== [ima:scan-only] End: $(date) ===" >> "$LOG"
exit "$SCAN_EXIT"
