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
            
            // Also hook execCommand
            const originalExecCommand = document.execCommand;
            document.execCommand = function(command, ...args) {
                if (command.toLowerCase() === 'copy') {
                    window.__interceptedClipboard = window.getSelection().toString();
                }
                return originalExecCommand.call(this, command, ...args);
            };
        """)
        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        # Click Share
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            box = await btn.bounding_box()
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            print("Clicked share menu.")
            
        await page.wait_for_timeout(2000)
        
        # Click Copy Link parent
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
            
        if await copy_btn.count() > 0:
            parent = copy_btn.first.locator("..")
            await parent.scroll_into_view_if_needed()
            box2 = await parent.bounding_box()
            await page.mouse.click(box2["x"] + box2["width"] / 2, box2["y"] + box2["height"] / 2)
            print("Clicked copy link parent natively.")
            
        await page.wait_for_timeout(2000)
        
        clipboard_text = await page.evaluate("window.__interceptedClipboard")
        print(f"Intercepted clipboard content: {clipboard_text}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
