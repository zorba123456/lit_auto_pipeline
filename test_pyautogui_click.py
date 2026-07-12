import asyncio
import os
import subprocess
from playwright.async_api import async_playwright
import pyautogui
import pyperclip

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
        
        # Bring to front using osascript
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
        
        # Clear clipboard
        pyperclip.copy("")
        
        await page.goto("https://yuanbao.tencent.com/chat")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        await page.locator(".yb-recent-conv-list__item").first.click()
        await page.wait_for_timeout(3000)
        
        # Click Share (using playwright is fine for the first click to open the menu)
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        if count > 0:
            btn = share_btns.nth(count - 1)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            print("Opened share menu.")
            
        await page.wait_for_timeout(2000)
        
        # Find Copy Link
        copy_btn = page.locator("text='Copy Link'")
        if await copy_btn.count() == 0:
            copy_btn = page.locator("text='复制链接'")
            
        if await copy_btn.count() > 0:
            parent = copy_btn.first.locator("..")
            
            # Get screen coordinates
            coords = await parent.evaluate("""(element) => {
                const rect = element.getBoundingClientRect();
                const x = window.screenX + rect.left + rect.width / 2;
                // top bar offset
                const y = window.screenY + (window.outerHeight - window.innerHeight) + rect.top + rect.height / 2;
                return {x, y};
            }""")
            
            print(f"Calculated screen coords: {coords}")
            
            # Ensure window is frontmost
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
            await asyncio.sleep(1)
            
            # Move and click using PyAutoGUI
            pyautogui.moveTo(coords["x"], coords["y"], duration=0.5)
            pyautogui.click()
            print("Clicked with pyautogui!")
            
        await asyncio.sleep(2)
        
        clipboard_content = pyperclip.paste()
        print(f"Clipboard after pyautogui click: {clipboard_content}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
