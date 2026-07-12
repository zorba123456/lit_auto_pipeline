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
        
        # clear log
        with open("network_log.txt", "w", encoding="utf-8") as f:
            f.write("")
            
        async def handle_response(response):
            if "ping" in response.url or "log" in response.url or "report" in response.url: return
            try:
                body = await response.text()
                with open("network_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"URL: {response.url}\nBODY: {body[:1000]}\n\n")
            except:
                pass
        
        page.on("response", handle_response)
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            await share_btns.nth(count - 1).click()
            
        await page.wait_for_timeout(1000)
        
        # Try finding copy button by text
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
        if await copy_btn.count() > 0:
            # use standard click
            await copy_btn.first.click()
            
        await page.wait_for_timeout(2000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
