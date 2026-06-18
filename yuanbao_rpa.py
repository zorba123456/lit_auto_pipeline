import asyncio
import os
import subprocess
import argparse
import time
from playwright.async_api import async_playwright
import pyautogui
import pyperclip

def get_idle_time():
    """Returns macOS system idle time in seconds."""
    try:
        res = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True
        )
        for line in res.stdout.splitlines():
            if "HIDIdleTime" in line:
                return int(line.split("=")[-1].strip()) / 1000000000.0
    except Exception as e:
        print(f"Error getting idle time: {e}")
    return 0.0

async def wait_for_idle(target_idle_sec=60):
    """Wait until the system is idle for target_idle_sec."""
    print(f"Waiting for system to be idle for {target_idle_sec} seconds...")
    while True:
        idle_time = get_idle_time()
        if idle_time >= target_idle_sec:
            print(f"System has been idle for {idle_time:.1f}s. Proceeding!")
            break
        
        remaining = target_idle_sec - idle_time
        sleep_time = min(remaining, 5.0)
        if sleep_time < 0.5: sleep_time = 0.5
        print(f"Current idle time: {idle_time:.1f}s. Waiting...")
        await asyncio.sleep(sleep_time)

async def upload_pdf_and_chat(page, pdf_path, prompt):
    print(f"Navigating to Yuanbao chat...")
    await page.goto("https://yuanbao.tencent.com/chat")
    
    print("Waiting for chat input...")
    await page.wait_for_selector(".agent-chat__input-wrapper", timeout=20000)
    
    print(f"Uploading PDF: {pdf_path}")
    async with page.expect_file_chooser() as fc_info:
        await page.locator("div[dt-button-id='upload_file']").click()
    file_chooser = await fc_info.value
    await file_chooser.set_files(pdf_path)
    
    print("Waiting for upload to complete...")
    await page.wait_for_selector(".hyc-content-file__info__name", timeout=30000)
    await page.wait_for_timeout(1000)
    
    print(f"Sending prompt: {prompt}")
    await page.locator(".ProseMirror").fill(prompt)
    await page.wait_for_timeout(500)
    await page.locator("div[dt-button-id='send_btn']").click()
    
    print("Waiting for AI response generation...")
    await page.wait_for_timeout(5000)
    try:
        await page.wait_for_selector(".agent-chat__list__item--ai[data-conv-outputting='false']", state="attached", timeout=120000)
    except Exception as e:
        print("Wait for outputting=false timed out. Assuming done.")
        
    await page.wait_for_timeout(2000)
    
    print("Extracting summary text...")
    ai_bubbles = page.locator(".agent-chat__list__item--ai .hyc-content-text")
    count = await ai_bubbles.count()
    if count > 0:
        summary_text = await ai_bubbles.last.inner_text()
        return summary_text
    return ""

async def get_share_link(page):
    print("Opening share menu...")
    share_btns = page.locator("div[aria-label='分享']")
    count = await share_btns.count()
    if count == 0:
        print("Share button not found!")
        return None
        
    btn = share_btns.nth(count - 1)
    await btn.scroll_into_view_if_needed()
    await btn.click()
    await page.wait_for_timeout(1000)
    
    copy_link_btn = page.locator(".agent-chat__share-bar__item").first
    if await copy_link_btn.count() == 0:
        print("Copy link item not found!")
        return None
        
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
    await asyncio.sleep(0.5)
    
    original_x, original_y = pyautogui.position()
    
    pyautogui.moveTo(coords["x"], coords["y"], duration=0.2)
    pyautogui.click()
    pyautogui.moveTo(original_x, original_y, duration=0.2)
    
    await asyncio.sleep(1)
    
    link = pyperclip.paste()
    return link

async def main():
    parser = argparse.ArgumentParser(description="Yuanbao PDF RPA")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--prompt", default="这是一篇真实的医美测试文献，请总结其核心医学观点。", help="Prompt to send")
    parser.add_argument("--mode", choices=["silent", "share"], default="share", help="Running mode")
    parser.add_argument("--idle", type=int, default=60, help="Idle wait time in seconds (for share mode)")
    args = parser.parse_args()
    
    abs_pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(abs_pdf_path):
        print(f"File not found: {abs_pdf_path}")
        return
        
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
        
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 800);")
        
        summary = await upload_pdf_and_chat(page, abs_pdf_path, args.prompt)
        print("\n--- SUMMARY ---")
        print(summary)
        print("---------------\n")
        
        share_link = None
        if args.mode == "share":
            await wait_for_idle(args.idle)
            share_link = await get_share_link(page)
            print(f"Share link obtained: {share_link}")
            
        await browser.close()
        
        out_file = abs_pdf_path + "_result.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            if share_link:
                f.write(f"Share Link: {share_link}\n\n")
            f.write("Summary:\n")
            f.write(summary)
        print(f"Result saved to {out_file}")

if __name__ == "__main__":
    asyncio.run(main())
