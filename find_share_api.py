import asyncio
import os
import subprocess
import json
from playwright.async_api import async_playwright
import pyautogui
import pyperclip

responses_data = []

async def handle_response(response):
    # We only care about XHR/Fetch/WebSocket or maybe document
    try:
        url = response.url
        if "yb.tencent.com" in url or "yuanbao.tencent.com" in url:
            try:
                body = await response.text()
            except Exception:
                body = ""
            responses_data.append({
                "url": url,
                "status": response.status,
                "request_post_data": response.request.post_data,
                "body": body
            })
    except Exception:
        pass

async def main():
    pdf_path = os.path.abspath("/Users/meiyiwangluokeji/Desktop/collagen/CCID-603794-operational-standard-for-tissue-extracted-collagen-facial-in.pdf")
    
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
        page.on("response", handle_response)
        
        print(f"Navigating to Yuanbao chat...")
        await page.goto("https://yuanbao.tencent.com/chat")
        
        print("Waiting for recent conversation list...")
        await page.wait_for_selector(".yb-recent-conv-list__item", timeout=15000)
        
        print("Clicking the first conversation...")
        await page.locator(".yb-recent-conv-list__item").first.click()
        
        print("Waiting for conversation to load...")
        await page.wait_for_timeout(5000)
        
        print("Waiting for AI response generation...")
        await page.wait_for_timeout(5000)
        try:
            await page.wait_for_selector(".agent-chat__list__item--ai[data-conv-outputting='false']", state="attached", timeout=120000)
        except Exception as e:
            print("Wait for outputting=false timed out. Assuming done.")
            
        await page.wait_for_timeout(3000)
        
        print("Opening share menu...")
        share_btns = page.locator("div[aria-label='分享']")
        count = await share_btns.count()
        btn = share_btns.nth(count - 1)
        await btn.scroll_into_view_if_needed()
        await btn.click()
        await page.wait_for_timeout(2000)
        
        copy_link_btn = page.locator(".agent-chat__share-bar__item").first
        coords = await copy_link_btn.evaluate("""(element) => {
            const rect = element.getBoundingClientRect();
            const x = window.screenX + rect.left + rect.width / 2;
            const y = window.screenY + (window.outerHeight - window.innerHeight) + rect.top + rect.height / 2;
            return {x, y};
        }""")
        
        print("Clearing clipboard...")
        pyperclip.copy("")
        
        print("Stealing focus to click...")
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
        await asyncio.sleep(1)
        
        original_x, original_y = pyautogui.position()
        pyautogui.moveTo(coords["x"], coords["y"], duration=0.2)
        pyautogui.click()
        pyautogui.moveTo(original_x, original_y, duration=0.2)
        
        await asyncio.sleep(1)
        
        link = pyperclip.paste()
        print(f"Obtained link: {link}")
        
        await browser.close()
        
        # Now search the recorded responses!
        if "yb.tencent.com/s/" in link:
            share_id = link.split("yb.tencent.com/s/")[-1].strip()
            print(f"Searching network logs for share ID: {share_id}")
            found = False
            for r in responses_data:
                if share_id in r.get("body", "") or share_id in r.get("url", ""):
                    print("\n" + "="*50)
                    print(f"FOUND API MATCH!")
                    print(f"URL: {r['url']}")
                    print(f"POST DATA: {r['request_post_data']}")
                    print(f"RESPONSE BODY: {r['body'][:500]}...")
                    print("="*50 + "\n")
                    found = True
            if not found:
                print(f"CRITICAL FAILURE: {share_id} was NOT found in ANY network response body. It might be encrypted, WebSocket binary, or generated locally via algorithm.")
        else:
            print("Link did not contain yb.tencent.com/s/")

if __name__ == "__main__":
    asyncio.run(main())
