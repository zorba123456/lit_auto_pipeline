#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 手动全量执行脚本
# VERSION: v1.0.6 (真双轨锁 - 彻底不触碰人类资产版)
# ------------------------------------------------------------------------------
VERSION="v1.0.6"
ROBOT_LOCK="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/pipeline.lock"
RUN_FLAG="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/run"
SCRIPT_PATH="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/run_task.sh"

echo "🚀 开始串行执行全量文献管线 ($VERSION)..."

# 【前置清场】：只清理机器人自己的临时锁和红灯
rm -rf "$ROBOT_LOCK" "$RUN_FLAG" 2>/dev/null
trap 'rm -rf "$ROBOT_LOCK" "$RUN_FLAG" 2>/dev/null; echo "任务已人工中断"' INT TERM

# 执行任务
"$SCRIPT_PATH" lww
"$SCRIPT_PATH" cma
"$SCRIPT_PATH" ktn
"$SCRIPT_PATH" cnki

# 【后置扫尾】：只清理机器人的资产
rm -rf "$ROBOT_LOCK" "$RUN_FLAG" 2>/dev/null
echo "✅ 全量文献管线 ($VERSION) 执行完毕！"