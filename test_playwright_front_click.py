import asyncio
import os
import subprocess
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
        
        # Bring to front using osascript to ensure OS-level focus
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
        
        # Clear clipboard via python to avoid JS origin issues
        import pyperclip
        pyperclip.copy("")
        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            print("Opened share menu.")
            
        await page.wait_for_timeout(2000)
        
        share_items = page.locator(".agent-chat__share-bar__item")
        if await share_items.count() > 0:
            copy_link_btn = share_items.first
            await copy_link_btn.scroll_into_view_if_needed()
            
            # Make absolutely sure Chrome is frontmost before clicking
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
            await asyncio.sleep(1)
            
            # Use Playwright's click (does not move physical mouse)
            await copy_link_btn.click(force=True)
            print("Clicked Copy Link button via Playwright.")
            
        await page.wait_for_timeout(2000)
        
        # Read the OS clipboard
        clipboard_content = pyperclip.paste()
        print(f"Clipboard after Playwright click: {clipboard_content}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
