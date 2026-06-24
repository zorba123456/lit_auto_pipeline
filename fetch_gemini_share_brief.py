"""从 Gemini 公开分享页抠 reading_note_zh（自定义 prompt 仅在 Gemini 侧，不公开到豆包 thread）。"""

from __future__ import annotations

import argparse
import asyncio
import re

from playwright.async_api import async_playwright

from gemini_rpa_extract import extract_gemini_brief

GEMINI_SHARE_RE = re.compile(
    r"^https://gemini\.google\.com/share/[a-zA-Z0-9]+/?(\?.*)?$"
)


async def _page_text(page) -> str:
    return await page.evaluate(
        """() => {
            const main = document.querySelector('main') || document.querySelector('[role="main"]');
            if (main && main.innerText) return main.innerText;
            return document.body.innerText || '';
        }"""
    )


async def fetch_gemini_share_brief(
    share_url: str,
    *,
    timeout_sec: int = 120,
    headless: bool = True,
) -> str:
    share_url = share_url.strip().rstrip("/")
    if not GEMINI_SHARE_RE.match(share_url):
        raise ValueError(f"非 Gemini share URL: {share_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        try:
            await page.goto(share_url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(3000)

            best = ""
            stable = 0
            for _ in range(timeout_sec * 2):
                await page.wait_for_timeout(500)
                text = await _page_text(page)
                extracted = extract_gemini_brief(text)
                if extracted and len(extracted) > len(best):
                    best = extracted
                if extracted and len(extracted) >= 200:
                    stable += 1
                    if stable >= 6:
                        break
                else:
                    stable = 0

            if not best:
                best = extract_gemini_brief(await _page_text(page))
            return best
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="从 Gemini share 抠导读")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    brief = asyncio.run(
        fetch_gemini_share_brief(
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
        print(brief or "(未提取到导读)")
    if not brief:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
