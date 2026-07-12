import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        user_data_dir = "./yuanbao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        
        print("Navigating to Yuanbao Chat...")
        await page.goto("https://yuanbao.tencent.com/chat")
        
        # Click the first conversation just to make sure we are on the latest one
        try:
            await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
            await page.locator(".yb-recent-conv-list__item").first.click()
        except:
            pass
            
        print("Browser is open and waiting for 5 minutes...")
        await page.wait_for_timeout(300000) # 5 minutes
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
