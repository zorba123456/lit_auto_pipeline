#!/bin/bash
# ima_relogin.sh — IMA 掉线一键重登
# 用法: bash ~/.hermes/scripts/ima_relogin.sh
# 作用:
#   1) 启动带窗口的 Android 模拟器 (pixel_ima_cn)，否则登录界面无窗口可看
#   2) 拉起腾讯 IMA app
#   3) 提示用户到模拟器窗口里做微信/扫码登录
# 搭配: ima_patrol.py 掉线防护（navigate 失败 exit=2 + 阻塞式弹窗提醒）
#       掉线弹窗会提示本脚本。登录完成后，跑 run_ima_scan.sh 立即恢复，
#       或等下一次 cron (11:05/18:05) 自动恢复。
#
# 说明: 登录态持久化在 AVD 用户数据里，本脚本/关闭模拟器都不清除。
#       唯有账号 token 失效（长时间未活跃/换设备）才需人工重登。

EMULATOR="$HOME/Library/Android/sdk/emulator/emulator/emulator"
AVD="pixel_ima_cn"
ADB="/opt/homebrew/bin/adb"
IMA_PKG="com.tencent.ima"
IMA_ACT=".MainActivity"

set -u

echo "==> 1/3 准备模拟器..."

# 清理陈旧锁文件（上次异常退出的残留，可能阻塞启动）
rm -f "$HOME/.android/avd/$AVD.avd/"*.lock 2>/dev/null
"$ADB" start-server >/dev/null 2>&1

# 若模拟器已在跑则直接复用；否则带窗口冷启动
if "$ADB" devices | grep -q "emulator-5554.*device"; then
    echo "    模拟器已在运行，复用现有实例。"
else
    echo "    => 启动模拟器（窗口即将弹出）..."
    "$EMULATOR" -avd "$AVD" -netdelay none -netspeed full \
        -gpu swiftshader_indirect -no-audio -no-boot-anim -no-snapshot \
        >/tmp/ima_relogin_emulator.log 2>&1 &
    # 等待 boot 完成（最多 120s）
    for i in $(seq 1 60); do
        if "$ADB" devices | grep -q "emulator-5554.*device"; then
            b=$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
            if [ "$b" = "1" ]; then
                echo "    模拟器启动完成。"
                break
            fi
        fi
        sleep 2
    done
fi

echo "==> 2/3 拉起腾讯 IMA app..."
"$ADB" shell am start -n "$IMA_PKG/$IMA_ACT" 2>/dev/null || \
    "$ADB" shell am start -n "$IMA_PKG/.MainActivity" 2>/dev/null
sleep 3

echo "==> 3/3 完成。"
echo ""
echo "┌──────────────────────────────────────────────────────┐"
echo "│  IMA 已打开。请到【模拟器窗口】里完成登录：             │"
echo "│                                                      │"
echo "│  提示「登录信息已失效」→ 点【立即登录】                 │"
echo "│  → 选【微信登录】或【扫码登录】，手机扫码/授权即可        │"
echo "│                                                      │"
echo "│  登录完成后：                                         │"
echo "│    立即恢复 → bash ~/coding/lit_auto_pipeline/run_ima_scan.sh │"
echo "│    等待下次 cron（11:05 / 18:05）自动恢复也可以          │"
echo "└──────────────────────────────────────────────────────┘"
