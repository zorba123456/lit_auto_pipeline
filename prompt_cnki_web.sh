#!/bin/bash
# =============================================================================
# Project: lit_auto_pipeline (aes-intel platform)
# File: prompt_cnki_web.sh
# Description: 每天定时弹窗提醒用户执行深度抓取。若用户点击，则调用 cnki_downloader.py
#
# 通知中心接入（方案 A，2026-07-31）：
#   - 保留原生 dialog 作为桌面端提醒 + 执行点击界面（不更换）。
#   - 启用时：在弹 dialog 前创建一条 action 待办到通知中心留档，用户点击后回填
#     outcome（executed/cancelled），抓取完成后追加 report 回填 exit 码。
#   - 开关：USE_NOTIFICATION_HUB=1 开启留档；=0 完全回退为原样（只弹 dialog）。
#     cnki_downloader.py 爬取本体逻辑不变。
# =============================================================================

# 通知中心接入开关（1=开启留档，0=回退原样）
USE_NOTIFICATION_HUB=1

# 通知中心统一写入端（绝对路径；notify_cli.py 纯标准库，用 system python3 即可）
NOTIFY_CLI="$HOME/coding/notification-hub/notify_cli.py"
NOTIFY_PY=python3

# 脚本自身绝对路径（作为 action.target，供将来网页看板解释执行）
SCRIPT_PATH="$HOME/coding/lit_auto_pipeline/prompt_cnki_web.sh"

# 建一个 action 待办（pending）并捕获其 id；失败时不阻断主流程
ACTION_ID=""
if [ "$USE_NOTIFICATION_HUB" = "1" ] && [ -f "$NOTIFY_CLI" ]; then
    ACTION_ID=$("$NOTIFY_PY" "$NOTIFY_CLI" --type action \
        --source cnki_downloader --level warn --no-banner --print-id \
        --title "深度抓取开工" \
        --msg "【知网深度抓取】时间到了，是否立即执行？" \
        --action-kind cnki_web --action-target "$SCRIPT_PATH" 2>/dev/null | tail -n 1)
fi

# 使用 AppleScript 弹出持久化系统对话框
res=$(osascript -e '
try
    set response to display dialog "【知网深度抓取】时间到了！\n\n点击“立即执行”将打开浏览器抓取当期目录与网络首发。\n（如遇滑块验证码，请手动滑动解锁，等待时间长达10分钟）" buttons {"暂不", "立即执行"} default button "立即执行" with title "Lit Auto Pipeline" with icon note
    return button returned of response
on error number -128
    return "Cancel"
end try
')

# 根据 dialog 结果回填待办结果（仅启用留档且有 id 时）
if [ -n "$ACTION_ID" ]; then
    if [ "$res" = "立即执行" ]; then
        outcome="executed"
    else
        outcome="cancelled"
    fi
    msg_prompt="用户在 dialog 中选择了「$([ "$outcome" = "executed" ] && echo 立即执行 || echo 暂不/取消)」"
    "$NOTIFY_PY" "$NOTIFY_CLI" --type action --resolve --ref "$ACTION_ID" \
        --source cnki_downloader --level info --no-banner \
        --outcome "$outcome" --title "深度抓取开工" --msg "$msg_prompt" >/dev/null 2>&1
fi

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

    # ==========================================================================
    # 获取任务排他锁（PID 存活检测 + 年龄兜底，防僵尸锁卡死）
    #   - 锁目录内写 lock.pid(持有者 PID)，用于判断锁是否还由活进程持有
    #   - 若 PID 已死(进程消失) → 判定僵尸锁，删除后重新尝试
    #   - 若锁目录无 PID 文件(历史遗留)且年龄超过 5 分钟 → 判定僵尸锁，删除重试
    #   - 正常执行中 PID 文件必有且持有者存活(见下方 PID 写入行)，不会被误删
    #   - 滑块验证码最长等 10 分钟，期间持有者进程仍存活，受 PID 检测保护，安全
    # ==========================================================================
    while ! mkdir "$DIR/pipeline.lock" 2>/dev/null; do
        ZOMBIE=0
        if [ -f "$DIR/pipeline.lock/lock.pid" ]; then
            # 有 PID 文件：若进程已不存活，即僵尸
            LOCK_PID=$(cat "$DIR/pipeline.lock/lock.pid" 2>/dev/null | tr -d '[:space:]')
            if ! kill -0 "$LOCK_PID" 2>/dev/null; then
                ZOMBIE=1
            fi
        else
            # 无 PID 文件(历史僵尸遗留)：用年龄兜底，超过 5 分钟判定僵尸
            if [ -x /usr/bin/stat ]; then
                LOCK_AGE=$(($(date +%s) - $(stat -f %m "$DIR/pipeline.lock" 2>/dev/null)))
            else
                LOCK_AGE=9999
            fi
            if [ "${LOCK_AGE:-0}" -gt 300 ]; then
                ZOMBIE=1
            fi
        fi

        if [ "$ZOMBIE" = "1" ]; then
            echo "检测到僵尸锁 pipeline.lock，自动清除后重试..." | tee -a "$LOG_FILE"
            rm -rf "$DIR/pipeline.lock"
            continue
        fi

        echo "等待 pipeline.lock 释放(存在有效持有者)..." | tee -a "$LOG_FILE"
        sleep 2
    done

    # 写入持有者 PID，供后续进程检测锁是否存活
    echo "$$" > "$DIR/pipeline.lock/lock.pid"

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

    # 抓取完成后追加 report 回填结果（仅启用留档时）
    if [ "$USE_NOTIFICATION_HUB" = "1" ] && [ -f "$NOTIFY_CLI" ]; then
        if [ "$EXIT_CODE" = "0" ]; then
            "$NOTIFY_PY" "$NOTIFY_CLI" --source cnki_downloader --level info --no-banner \
                --type report --title "深度抓取完成" \
                --msg "知网深度抓取执行完成" --result "exit=0,成功" >/dev/null 2>&1
        else
            "$NOTIFY_PY" "$NOTIFY_CLI" --source cnki_downloader --level error --no-banner \
                --type report --title "深度抓取失败" \
                --msg "知网深度抓取异常退出" --result "exit=$EXIT_CODE,失败" >/dev/null 2>&1
        fi
    fi

    exit "$EXIT_CODE"
else
    echo "用户取消或选择暂不执行。"
fi
