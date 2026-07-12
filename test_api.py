import asyncio
from playwright.async_api import async_playwright
import json

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
        
        captured_data = []
        
        async def handle_response(response):
            if "json" in response.headers.get("content-type", ""):
                try:
                    data = await response.json()
                    # Convert to string and search for typical URL structures
                    data_str = json.dumps(data)
                    if "http" in data_str:
                        captured_data.append((response.url, data_str))
                except:
                    pass
        
        page.on("response", handle_response)
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        print("Waiting for recent chats...")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        print("Clicking share menu...")
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            await share_btns.nth(count - 1).click(force=True)
            print("Clicked share menu.")
        
        await page.wait_for_timeout(2000)
        
        print("Clicking Copy Link...")
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
        if await copy_btn.count() > 0:
            # Click the parent div just in case
            await copy_btn.first.locator("..").click(force=True)
            print("Clicked copy link parent.")
        
        await page.wait_for_timeout(2000)
        
        print("Captured API Responses with URLs:")
        for url, data in captured_data:
            print(f"URL: {url}")
            if "share" in data.lower() or "http" in data.lower():
                print(f"Data: {data[:500]}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
