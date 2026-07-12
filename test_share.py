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
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        # Click the first conversation in the recent list just in case
        print("Waiting for recent chats...")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000) # wait for chat to load
        
        print("Clicking share button...")
        # Get the last share button on the page
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            await share_btns.nth(count - 1).click(force=True)
            print("Clicked share button.")
        else:
            print("No share button found.")
            
        print("Waiting for share popup to open...")
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        with open("yuanbao_share_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Dumped HTML to yuanbao_share_dump.html")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
