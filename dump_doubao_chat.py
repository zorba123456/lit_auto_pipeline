import asyncio
from playwright.async_api import async_playwright

async def main():
    profile_dir = "./doubao_profile"
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=True,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        await page.goto("https://www.doubao.com/chat/")
        await page.wait_for_selector("textarea", timeout=15000)
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        with open("doubao_chat_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Dumped DOM to doubao_chat_dump.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
