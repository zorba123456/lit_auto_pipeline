#!/usr/bin/env python3
"""一次性在 yuanbao_profile 里登录腾讯账号；之后 RPA 复用该 profile。"""

from __future__ import annotations

import argparse
import asyncio

from playwright.async_api import async_playwright

YUANBAO_PROFILE = "./yuanbao_profile"
YUANBAO_URL = "https://yuanbao.tencent.com/"


async def run(wait_sec: int) -> None:
    print("===== 元宝 RPA 登录 =====")
    print(f"Profile: {YUANBAO_PROFILE}")
    print("说明：独立于日常 Chrome；请在本窗口完成腾讯/微信登录，并确认能进入对话。")
    print()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            YUANBAO_PROFILE,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await ctx.new_page()
        await page.goto(YUANBAO_URL, wait_until="domcontentloaded", timeout=90000)
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 900);")

        if wait_sec > 0:
            print(f"等待 {wait_sec}s（期间请完成登录）…")
            await asyncio.sleep(wait_sec)
        else:
            print("浏览器已打开。登录完成并能对话后，回到终端按 Enter 关闭并保存登录态…")
            await asyncio.get_event_loop().run_in_executor(None, input)

        await ctx.close()

    print("✅ 已关闭。登录态保存在 yuanbao_profile，下次 yuanbao_rpa 应免登录。")


def main():
    parser = argparse.ArgumentParser(description="元宝 RPA 专用 Chrome 登录")
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="自动等待秒数；默认 0 = 手动按 Enter 结束",
    )
    args = parser.parse_args()
    asyncio.run(run(args.wait))


if __name__ == "__main__":
    main()
