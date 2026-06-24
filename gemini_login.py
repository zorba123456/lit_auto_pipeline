#!/usr/bin/env python3
"""一次性在 gemini_playwright_profile 里登录 Google；之后 RPA 复用该 profile。"""

from __future__ import annotations

import argparse
import asyncio

from playwright.async_api import async_playwright

GEMINI_PROFILE = "./gemini_playwright_profile"
GEMINI_URL = "https://gemini.google.com/app"


async def run(wait_sec: int) -> None:
    print("===== Gemini RPA 登录 =====")
    print(f"Profile: {GEMINI_PROFILE}")
    print("说明：这是独立于日常 Chrome 的自动化专用配置，不会读取你主浏览器的登录态。")
    print("请在本窗口完成 Google 登录，并确认能打开 Gemini 对话页。")
    print()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            GEMINI_PROFILE,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()
        await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=90000)
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 900);")

        if wait_sec > 0:
            print(f"等待 {wait_sec}s（期间请完成登录）…")
            await asyncio.sleep(wait_sec)
        else:
            print("浏览器已打开。登录完成后回到终端按 Enter 关闭并保存登录态…")
            await asyncio.get_event_loop().run_in_executor(None, input)

        await ctx.close()

    print("✅ 已关闭。登录态保存在 gemini_playwright_profile，下次 gemini_rpa 应免登录。")
    print("若仍被要求登录：检查是否删了 profile 目录，或 Google 要求二次验证。")


def main():
    parser = argparse.ArgumentParser(description="Gemini RPA 专用 Chrome 登录")
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
