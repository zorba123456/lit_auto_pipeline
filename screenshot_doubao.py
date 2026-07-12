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
        print("Navigating to doubao.com/chat/")
        await page.goto("https://www.doubao.com/chat/", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        
        await page.screenshot(path="doubao_chat_ui.png")
        print("Screenshot saved to doubao_chat_ui.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
