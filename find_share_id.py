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
        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(5000)
        
        # Click Share to make sure states are populated
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(2000)
            
        # Extract ALL strings from the page's JS context that might contain a share URL
        # We can search through the window object or __NEXT_DATA__
        search_result = await page.evaluate('''() => {
            let found = [];
            const str = JSON.stringify(window.__NEXT_DATA__ || {});
            const matches = str.match(/yb\\.tencent\\.com\\/s\\/[a-zA-Z0-9]+/g);
            if (matches) {
                found.push(...matches);
            }
            
            // Also search all Redux/Mobx states attached to window
            for (let key of Object.keys(window)) {
                try {
                    const s = JSON.stringify(window[key]);
                    if (s && s.includes('yb.tencent.com/s/')) {
                        const m = s.match(/yb\\.tencent\\.com\\/s\\/[a-zA-Z0-9]+/g);
                        if (m) found.push(...m);
                    }
                } catch(e) {}
            }
            return [...new Set(found)];
        }''')
        
        print(f"Found share URLs in window state: {search_result}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
