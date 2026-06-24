"""
Gemini Web RPA：自定义 brief prompt → share → reading_note_zh
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess

from playwright.async_api import async_playwright

from prompts.prompt_loader import load_structured_prompt
from fetch_gemini_share_brief import fetch_gemini_share_brief
from gemini_rpa_extract import (
    DEFAULT_MODEL_LABEL,
    GEMINI_CHAT_URL,
    _brief_is_ready,
    _brief_section_count,
    get_conversation_text,
    get_share_link,
    select_model,
    send_prompt,
    start_new_chat,
    upload_pdf,
    wait_for_brief_reply,
)

GEMINI_PROFILE = "./gemini_playwright_profile"


def _park_chrome_window() -> None:
    """挪到屏幕外；主要靠 --window-position + JS。osascript 需辅助功能权限，失败则静默跳过。"""
    if os.environ.get("GEMINI_RPA_FOREGROUND") == "1":
        return
    x = int(os.environ.get("GEMINI_RPA_WINDOW_X", "2400"))
    y = int(os.environ.get("GEMINI_RPA_WINDOW_Y", "80"))
    script = f'''
tell application "System Events"
    if exists process "Google Chrome" then
        tell process "Google Chrome"
            if (count of windows) > 0 then
                set position of front window to {{{x}, {y}}}
            end if
        end tell
    end if
end tell
'''
    subprocess.run(
        ["osascript", "-e", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _setup_gemini_window(page) -> None:
    foreground = os.environ.get("GEMINI_RPA_FOREGROUND") == "1"
    w = int(os.environ.get("GEMINI_RPA_WINDOW_W", "1280"))
    h = int(os.environ.get("GEMINI_RPA_WINDOW_H", "900"))
    if foreground:
        x, y = 0, 0
    else:
        x = int(os.environ.get("GEMINI_RPA_WINDOW_X", "2400"))
        y = int(os.environ.get("GEMINI_RPA_WINDOW_Y", "80"))
    await page.evaluate(f"window.moveTo({x}, {y}); window.resizeTo({w}, {h});")
    await page.wait_for_timeout(250)
    _park_chrome_window()


def _chrome_launch_args() -> list[str]:
    args = ["--disable-blink-features=AutomationControlled"]
    if os.environ.get("GEMINI_RPA_FOREGROUND") != "1":
        x = os.environ.get("GEMINI_RPA_WINDOW_X", "2400")
        y = os.environ.get("GEMINI_RPA_WINDOW_Y", "80")
        args.append(f"--window-position={x},{y}")
    return args


async def process_pdf_with_gemini(
    pdf_path: str,
    *,
    prompt: str | None = None,
    model_label: str = DEFAULT_MODEL_LABEL,
    verify_share_extract: bool = True,
) -> tuple[str, str | None]:
    """返回 (reading_note_zh, gemini_share_url)。"""
    if prompt is None:
        prompt = load_structured_prompt("brief")

    abs_pdf = os.path.abspath(pdf_path)
    session_brief = ""
    share_url: str | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            GEMINI_PROFILE,
            headless=False,
            channel="chrome",
            args=_chrome_launch_args(),
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await browser.new_page()
        await _setup_gemini_window(page)

        await page.goto(GEMINI_CHAT_URL, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(1500)
        _park_chrome_window()

        await start_new_chat(page)
        await select_model(page, model_label)
        await upload_pdf(page, abs_pdf)
        await send_prompt(page, prompt)
        session_brief = await wait_for_brief_reply(page)

        if session_brief and _brief_is_ready(session_brief):
            print(f"📎 导读 {len(session_brief)} 字，准备分享…")
            share_url = await get_share_link(page)
        elif session_brief:
            print(
                f"⚠️ 导读不完整（{len(session_brief)} 字，"
                f"{_brief_section_count(session_brief)} 节），跳过分享"
            )
        else:
            print("⚠️ 未提取到导读，跳过分享")

        if not session_brief:
            debug_path = abs_pdf + "_gemini_debug.txt"
            conv = await get_conversation_text(page)
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(conv)
            print(f"📋 导读为空，已 dump: {debug_path} ({len(conv)} 字)")

        await browser.close()

    thread_brief = ""
    if verify_share_extract and share_url:
        print("🔍 从 share 页二次抠导读…")
        thread_brief = await fetch_gemini_share_brief(share_url, headless=True)

    # 优先 share 抠字（与生产路径一致）；会话内作 fallback
    reading_note = thread_brief if len(thread_brief or "") >= len(session_brief or "") else session_brief
    if thread_brief and session_brief and thread_brief != session_brief:
        print(f"ℹ️ session={len(session_brief)} 字 share={len(thread_brief)} 字")

    return reading_note, share_url


def main():
    parser = argparse.ArgumentParser(description="Gemini 导读 RPA")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL_LABEL)
    parser.add_argument(
        "--fetch-only",
        metavar="SHARE_URL",
        help="仅从已有 Gemini share URL 抠导读",
    )
    parser.add_argument("--no-verify-share", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    if args.fetch_only:
        brief = asyncio.run(fetch_gemini_share_brief(args.fetch_only))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(brief)
            print(f"✅ {args.output} ({len(brief)} 字)")
        else:
            print(brief)
        return

    abs_pdf = os.path.abspath(args.pdf)
    if not os.path.exists(abs_pdf):
        print(f"❌ 不存在: {abs_pdf}")
        raise SystemExit(1)

    brief, share = asyncio.run(
        process_pdf_with_gemini(
            abs_pdf,
            model_label=args.model,
            verify_share_extract=not args.no_verify_share,
        )
    )

    out = abs_pdf + "_gemini_result.txt"
    with open(out, "w", encoding="utf-8") as f:
        if share:
            f.write(f"Share: {share}\n\n")
        f.write("Brief:\n")
        f.write(brief or "")
    print(f"✅ 已保存 {out}")
    if share:
        print(f"🔗 {share}")
    print(f"导读 {len(brief or '')} 字（不含 prompt）")


if __name__ == "__main__":
    main()
