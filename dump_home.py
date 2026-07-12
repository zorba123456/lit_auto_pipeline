import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        user_data_dir = "./yuanbao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir, headless=True, channel="chrome"
        )
        page = await browser.new_page()
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("home_dump.html", "w") as f:
            f.write(html)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
