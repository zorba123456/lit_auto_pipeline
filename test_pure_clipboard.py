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
        

        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        # Click Share icon to open bottom menu
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            print("Clicked Share menu icon.")
            
        await page.wait_for_timeout(2000)
        
        # Now find the "Copy Link" button. It's the first .agent-chat__share-bar__item
        share_items = page.locator(".agent-chat__share-bar__item")
        if await share_items.count() > 0:
            copy_link_btn = share_items.first
            await copy_link_btn.scroll_into_view_if_needed()
            await copy_link_btn.click()
            print("Clicked Copy Link button.")
            
        await page.wait_for_timeout(2000)
        
        # Read the clipboard using JS
        clipboard_content = await page.evaluate("navigator.clipboard.readText()")
        print(f"Browser Clipboard output: {clipboard_content}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
