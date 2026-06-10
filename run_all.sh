#!/bin/bash
# ------------------------------------------------------------------------------
# AES-INTEL 自动化管线全量心跳调度脚本
# VERSION: v1.0.8-patrol-sched (KTN 错峰独立调度 + 巡查)
# ------------------------------------------------------------------------------
VERSION="v1.0.8-patrol-sched"
PROJECT_DIR="/Users/meiyiwangluokeji/coding/lit_auto_pipeline"

cd "$PROJECT_DIR" || exit 1

echo "🚀 开始串行分发全量文献管线心跳 ($VERSION)..."

# 依次串行分发任务
# 每个任务进入 run_task.sh 后都会先独立判断状态和 pipeline.lock，安全且不抢占资源
./run_task.sh cma
./run_task.sh cnki

echo "✅ 全量文献管线心跳 ($VERSION) 分发完毕！"