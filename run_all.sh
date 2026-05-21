#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 手动全量执行脚本
# VERSION: v1.0.4 (方案 B 极简物理锁与首尾硬核自愈清场版)
# ------------------------------------------------------------------------------
VERSION="v1.0.4"
LOCK_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/lock"
RUN_FLAG="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/run"
SCRIPT_PATH="/Users/meiyiwangluokeji/coding/lit_auto_pipeline/run_task.sh"

echo "🚀 开始串行执行全量文献管线 ($VERSION)..."

# 【前置清场】：开工前强拆任何可能残留的僵尸锁和标识
rm -rf "$LOCK_DIR" "$RUN_FLAG" 2>/dev/null

# 捕捉前台人工中断（Ctrl+C），确保优雅删锁，绝不把黄灯卡在屏幕上
trap 'rm -rf "$LOCK_DIR" "$RUN_FLAG" 2>/dev/null; echo "任务已人工中断"' INT TERM

# 按顺序排队串行执行单项任务
"$SCRIPT_PATH" lww
"$SCRIPT_PATH" cma
"$SCRIPT_PATH" ktn
"$SCRIPT_PATH" cnki

# 【后置扫尾】：全量任务结束时，强力粉碎痕迹，确保 100% 刷新为绿灯
rm -rf "$LOCK_DIR" "$RUN_FLAG" 2>/dev/null

echo "✅ 全量文献管线 ($VERSION) 执行完毕！"