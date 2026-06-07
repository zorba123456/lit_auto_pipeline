#!/bin/bash
# =============================================================================
# Project: lit_auto_pipeline (aes-intel platform)
# File: prompt_cnki_web.sh
# Description: 每天定时弹窗提醒用户执行深度抓取。若用户点击，则调用 cnki_downloader.py
# =============================================================================

# 使用 AppleScript 弹出持久化系统对话框
res=$(osascript -e '
try
    set response to display dialog "【知网深度抓取】时间到了！\n\n点击“立即执行”将打开浏览器抓取当期目录与网络首发。\n（如遇滑块验证码，请手动滑动解锁，等待时间长达10分钟）" buttons {"暂不", "立即执行"} default button "立即执行" with title "Lit Auto Pipeline" with icon note
    return button returned of response
on error number -128
    return "Cancel"
end try
')

# 如果用户点击了“立即执行”
if [ "$res" = "立即执行" ]; then
    DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$DIR"

    LOG_DIR="$DIR/logs"
    LOG_FILE="$LOG_DIR/cnki_web.log"
    mkdir -p "$LOG_DIR"

    cleanup() {
        rm -rf "$DIR/pipeline.lock" "$DIR/run" 2>/dev/null
        # Playwright 持久化上下文可能残留 Edge 进程，按 profile 路径精准清理
        pkill -f "cnki_playwright_profile" 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM USR1

    echo "=== [cnki-web] Start: $(date) ===" | tee -a "$LOG_FILE"
    echo "用户已确认，开始执行 Web 模式深度抓取..." | tee -a "$LOG_FILE"

    # 获取任务排他锁 (如果刚好整点后台有任务在跑，则等待其完成)
    while ! mkdir "$DIR/pipeline.lock" 2>/dev/null; do
        echo "等待 pipeline.lock 释放..." | tee -a "$LOG_FILE"
        sleep 2
    done

    # 🛑 开启物理红灯 (通知 SwiftBar 状态为繁忙)
    touch "$DIR/run"

    # 激活环境并运行（无缓冲输出，写入专用日志）
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    export PYTHONUNBUFFERED=1
    python3 aes-feeds/cnki_downloader.py --mode web 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}

    echo "=== [cnki-web] End (exit=$EXIT_CODE): $(date) ===" | tee -a "$LOG_FILE"
    exit "$EXIT_CODE"
else
    echo "用户取消或选择暂不执行。"
fi
