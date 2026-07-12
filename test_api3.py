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
        
        with open("network_dump.jsonl", "w", encoding="utf-8") as f:
            pass
            
        async def handle_response(response):
            if "ping" in response.url or "log" in response.url or "report" in response.url or "beacon" in response.url: return
            try:
                req = response.request
                req_post_data = req.post_data
                res_body = await response.text()
                
                log_data = {
                    "url": response.url,
                    "method": req.method,
                    "req_body": req_post_data,
                    "res_body": res_body[:2000]
                }
                with open("network_dump.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
            except:
                pass
                
        page.on("response", handle_response)
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        # Click Share using regular click, ensuring it's scrolled into view
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            print("Clicked share menu.")
            
        await page.wait_for_timeout(1000)
        
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
            
        if await copy_btn.count() > 0:
            await copy_btn.first.scroll_into_view_if_needed()
            await copy_btn.first.click()
            print("Clicked copy link.")
            
        await page.wait_for_timeout(2000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
