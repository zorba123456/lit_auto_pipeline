import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            "./yuanbao_profile", headless=True, channel="chrome"
        )
        page = await browser.new_page()
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_timeout(5000)
        
        # Click the upload button to open the menu
        await page.locator("[data-testid='upload-file-selector']").click()
        await page.wait_for_timeout(2000)
        
        await page.screenshot(path="screenshot_home.png", full_page=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
