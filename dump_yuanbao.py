import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        user_data_dir = "./yuanbao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        
        print("Navigating to Yuanbao...")
        await page.goto("https://yuanbao.tencent.com/chat")
        
        # Wait for page to load
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        with open("yuanbao_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Dumped HTML to yuanbao_dump.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
