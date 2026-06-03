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
    echo "用户已确认，开始执行 Web 模式深度抓取..."
    # 切换到项目根目录
    DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$DIR"
    
    # 获取任务排他锁 (如果刚好整点后台有任务在跑，则等待其完成)
    while ! mkdir "$DIR/pipeline.lock" 2>/dev/null; do
        sleep 2
    done
    
    # 安全兜底：退出时自动清理锁和红灯状态
    trap 'rm -rf "$DIR/pipeline.lock" "$DIR/run" 2>/dev/null' EXIT INT TERM
    
    # 🛑 开启物理红灯 (通知 SwiftBar 状态为繁忙)
    touch "$DIR/run"
    
    # 激活环境并运行
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    python3 aes-feeds/cnki_downloader.py --mode web
else
    echo "用户取消或选择暂不执行。"
fi
