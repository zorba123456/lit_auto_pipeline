import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    profile_dir = "./doubao_profile"
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=True,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        await page.goto("https://www.doubao.com/chat/")
        
        # Wait for the chat to render
        await page.wait_for_selector("textarea", timeout=15000)
        await page.wait_for_timeout(3000)
        
        inputs = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('input')).map(el => el.outerHTML);
        }''')
        
        buttons = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('button')).map(el => {
                return {
                    class: el.className,
                    text: el.innerText,
                    aria: el.getAttribute('aria-label') || el.getAttribute('title')
                };
            });
        }''')
        
        with open("doubao_elements.txt", "w", encoding="utf-8") as f:
            f.write("INPUTS:\n")
            for i in inputs: f.write(i + "\n")
            f.write("\nBUTTONS:\n")
            for b in buttons: f.write(json.dumps(b, ensure_ascii=False) + "\n")
            
        print("Done!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
