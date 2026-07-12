import asyncio
from playwright.async_api import async_playwright

async def main():
    profile_dir = "./doubao_profile"
    async with async_playwright() as p:
        # Launch headless to silently get the DOM
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=True,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        print("Navigating to doubao.com...")
        await page.goto("https://www.doubao.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        content = await page.content()
        with open("doubao_home_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("DOM dumped successfully to doubao_home_dump.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
