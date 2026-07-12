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
        
        # log websockets
        with open("ws_log.txt", "w", encoding="utf-8") as f:
            pass
            
        def log_ws_frame(action, payload):
            with open("ws_log.txt", "a", encoding="utf-8") as f:
                f.write(f"WS {action}: {payload}\n")
                
        page.on("websocket", lambda ws: [
            ws.on("framesent", lambda p: log_ws_frame("SENT", p)),
            ws.on("framereceived", lambda p: log_ws_frame("RECEIVED", p))
        ])
        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            box = await btn.bounding_box()
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            print("Clicked share menu natively.")
            
        await page.wait_for_timeout(1000)
        
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
            
        if await copy_btn.count() > 0:
            btn2 = copy_btn.first
            await btn2.scroll_into_view_if_needed()
            box2 = await btn2.bounding_box()
            await page.mouse.click(box2["x"] + box2["width"] / 2, box2["y"] + box2["height"] / 2)
            print("Clicked copy link natively.")
            
        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
