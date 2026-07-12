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
        
        with open("manual_network_log.txt", "w", encoding="utf-8") as f:
            f.write("")
            
        page.on("request", lambda req: open("manual_network_log.txt", "a", encoding="utf-8").write(f"REQ: {req.method} {req.url}\n"))
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        try:
            await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
            await page.locator(".yb-recent-conv-list__item").first.click()
        except:
            pass
            
        print("Waiting for 2 minutes for manual interaction...")
        await page.wait_for_timeout(120000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
