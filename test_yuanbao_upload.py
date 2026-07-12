import asyncio
from playwright.async_api import async_playwright
import os
import time

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
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        
        print("Navigating to Yuanbao Chat...")
        await page.goto("https://yuanbao.tencent.com/chat")
        
        # Wait for the chat input to appear
        print("Waiting for chat input...")
        await page.wait_for_selector(".ql-editor", timeout=15000)
        await page.wait_for_timeout(2000) # Give React a moment to bind listeners
        
        # Upload the PDF file
        pdf_path = "/Users/meiyiwangluokeji/Desktop/collagen/CCID-603794-operational-standard-for-tissue-extracted-collagen-facial-in.pdf"
        print(f"Uploading {pdf_path}...")
        try:
            # 1. Click the + attachment button to open the menu
            await page.locator("div[data-testid='upload-file-selector'] svg").click(force=True)
            await page.wait_for_timeout(1000) # wait for menu animation
            
            # 2. Click "Local Files" (or its Chinese equivalent) to trigger the file chooser
            async with page.expect_file_chooser(timeout=15000) as fc_info:
                # Find the Local Files button (try English first, then Chinese)
                local_file_btn = page.locator("text='Local Files'")
                if await local_file_btn.count() == 0:
                    local_file_btn = page.locator("text='本地文件'")
                await local_file_btn.click(force=True)
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(pdf_path)
            print("File set.")
        except Exception as e:
            print("Failed to set file via file chooser. Error:", e)
        
        # Wait a bit for upload UI to register and the file to upload
        print("Waiting for file to upload to the server...")
        await page.wait_for_timeout(5000)
        
        # Type the prompt
        print("Typing prompt...")
        prompt_text = "这是一篇真实的医美测试文献，请总结其核心医学观点。"
        await page.locator(".ql-editor").fill(prompt_text)
        
        # Click send button
        print("Clicking send...")
        await page.locator("#yuanbao-send-btn").click(force=True)
        
        # Wait for generation to start and finish
        print("Waiting for generation to finish... (sleeping for 40s)")
        await page.wait_for_timeout(40000)
        
        # Dump the HTML so we can find the "Share" button selector
        html = await page.content()
        with open("yuanbao_chat_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print("Dumped HTML to yuanbao_chat_dump.html. Please inspect to find the Share button.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
