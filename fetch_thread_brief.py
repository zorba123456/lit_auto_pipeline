"""从公开豆包 thread 分享页抠 reading_note_zh（无需登录）。"""

from __future__ import annotations

import argparse
import asyncio
import re

from playwright.async_api import async_playwright

from doubao_rpa_extract import extract_brief_from_main_text

THREAD_URL_RE = re.compile(
    r"^https://www\.doubao\.com/thread/[a-zA-Z0-9]+/?(\?.*)?$"
)


async def _page_text(page) -> str:
    return await page.evaluate(
        """() => {
            const main = document.querySelector('main[data-container-name="main"]');
            if (main && main.innerText) return main.innerText;
            const root = document.querySelector('#root main') || document.querySelector('main');
            if (root && root.innerText) return root.innerText;
            return document.body.innerText || '';
        }"""
    )


async def fetch_thread_brief(
    share_url: str,
    *,
    timeout_sec: int = 90,
    headless: bool = True,
) -> str:
    """打开公开 thread，等待渲染后提取导读正文。"""
    share_url = share_url.strip().rstrip("/")
    if not THREAD_URL_RE.match(share_url):
        raise ValueError(f"非豆包 thread URL: {share_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        try:
            await page.goto(share_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)

            best = ""
            stable = 0
            for _ in range(timeout_sec * 2):
                await page.wait_for_timeout(500)
                text = await _page_text(page)
                extracted = extract_brief_from_main_text(text)
                if extracted and len(extracted) > len(best):
                    best = extracted
                if extracted and len(extracted) >= 200:
                    stable += 1
                    if stable >= 6:
                        break
                else:
                    stable = 0

            if not best:
                text = await _page_text(page)
                best = extract_brief_from_main_text(text)

            return best
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="从豆包 thread 分享链抠导读")
    parser.add_argument("url", help="https://www.doubao.com/thread/...")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("-o", "--output", help="写入文件路径")
    args = parser.parse_args()

    brief = asyncio.run(
        fetch_thread_brief(
            args.url,
            timeout_sec=args.timeout,
            headless=not args.no_headless,
        )
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"✅ 已写入 {args.output} ({len(brief)} 字)")
    else:
        print(brief or "(未提取到导读结构)")
    if not brief:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
