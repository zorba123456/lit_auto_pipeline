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
        await page.wait_for_timeout(5000)
        
        # Try to find input type file
        inputs = await page.locator("input[type='file']").all()
        print(f"Found {len(inputs)} file inputs.")
        
        # Take a screenshot
        await page.screenshot(path="doubao_chat_ui_test.png")
        print("Screenshot saved.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
