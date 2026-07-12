import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        user_data_dir = "./yuanbao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled'],
            permissions=['clipboard-read', 'clipboard-write']
        )
        page = await browser.new_page()
        
        await page.add_init_script("""
            window.__interceptedClipboard = null;
            Object.defineProperty(navigator, 'clipboard', {
                value: {
                    writeText: async (text) => {
                        window.__interceptedClipboard = text;
                        return Promise.resolve();
                    },
                    readText: async () => {
                        return window.__interceptedClipboard;
                    }
                },
                configurable: true
            });
        """)
        
        await page.goto("https://yuanbao.tencent.com/chat")
        
        # Click the first conversation
        print("Waiting for recent chats...")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        print("Clicking share button...")
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            await share_btns.nth(count - 1).click(force=True)
            print("Clicked share menu.")
        else:
            print("No share menu found.")
            
        print("Waiting for popup and clicking Copy Link...")
        await page.wait_for_timeout(1000)
        
        # Try both English and Chinese
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
            
        print("Clicking copy link...")
        # Listen to network responses to see if an API is called to generate the share link
        responses = []
        page.on("response", lambda r: responses.append(r.url) if "share" in r.url.lower() or "export" in r.url.lower() else None)
        
        await copy_btn.click(force=True)
        print("Clicked copy link.")
        
        await page.wait_for_timeout(3000)
        
        print("Network responses related to share/export:")
        for url in responses:
            print(f"Intercepted: {url}")
            
        try:
            # Wait a moment for the JS to execute
            await page.wait_for_timeout(1000)
            
            # Retrieve the intercepted clipboard content
            clipboard_text = await page.evaluate("window.__interceptedClipboard")
            print(f"Intercepted clipboard content: {clipboard_text}")
        except Exception as e:
            print(f"Failed to read intercepted clipboard: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
