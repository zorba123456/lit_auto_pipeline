import asyncio
import os
from playwright.async_api import async_playwright

async def upload_pdf_and_chat(page, pdf_path, prompt):
    print(f"Navigating to Yuanbao chat...")
    await page.goto("https://yuanbao.tencent.com/chat")
    
    print("Waiting for upload button...")
    await page.wait_for_selector("[data-testid='upload-file-selector']", timeout=20000)
    
    print("Clicking upload button to open menu...")
    await page.locator("[data-testid='upload-file-selector']").click()
    await page.wait_for_timeout(1000)
    
    print(f"Uploading PDF: {pdf_path}")
    print(f"Uploading PDF: {pdf_path}")
    async with page.expect_file_chooser() as fc_info:
        # Use get_by_text to find the visible menu item
        menu_item = page.get_by_text("Local Files")
        if await menu_item.count() == 0:
            menu_item = page.get_by_text("上传本地文件")
        await menu_item.click()
        
    file_chooser = await fc_info.value
    await file_chooser.set_files(pdf_path)
    
    print("Waiting 5s for upload to complete...")
    await page.wait_for_timeout(5000)
    
    print(f"Sending prompt...")
    # Find the input area
    prompt_area = page.locator(".ql-editor, .ProseMirror, textarea")
        
    await prompt_area.first.fill(prompt)
    await page.wait_for_timeout(500)
    
    print("Submitting prompt...")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1000)
    
    print("Waiting for AI response to start generating...")
    try:
        # Wait for the 'outputting=true' state to appear
        await page.wait_for_selector(".agent-chat__list__item--ai[data-conv-outputting='true']", timeout=15000)
        print("AI is generating... waiting for it to finish.")
        # Wait for the 'outputting=true' state to disappear (meaning it finished or failed)
        await page.wait_for_selector(".agent-chat__list__item--ai[data-conv-outputting='true']", state="hidden", timeout=120000)
    except Exception as e:
        print("Wait logic timed out or failed. Assuming done.")
        
    await page.wait_for_timeout(3000)
    
    print("Extracting summary text...")
    ai_bubbles = page.locator(".agent-chat__list__item--ai .hyc-content-text")
    count = await ai_bubbles.count()
    summary_text = ""
    if count > 0:
        summary_text = await ai_bubbles.last.inner_text()
        
    return summary_text

async def get_share_link_api(page):
    url = page.url
    conv_id = ""
    if "/chat/" in url:
        conv_id = url.split("/chat/")[-1].split("?")[0].split("/")[-1]
    else:
        print("Could not find conversation ID from URL! Trying to extract from DOM.")
        conv_id = await page.evaluate("window.location.pathname.split('/').pop()")
        
    print(f"Calling Share API for conversation ID: {conv_id}...")
    
    print("Taking screenshot to debug empty summary...")
    await page.screenshot(path="screenshot_debug.png", full_page=True)
    
    js_code = f"""
    async () => {{
        try {{
            const response = await fetch("https://yuanbao.tencent.com/api/conversations/v2/share", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                body: JSON.stringify({{
                    "conversationId": "{conv_id}",
                    "agentId": "naQivTmsDa",
                    "selectAll": true,
                    "platform": "WEB"
                }})
            }});
            const data = await response.json();
            return data;
        }} catch(e) {{
            return {{error: e.toString()}};
        }}
    }}
    """
    
    result = await page.evaluate(js_code)
    print(f"API Result: {result}")
    
    if result and "shareId" in result:
        share_id = result["shareId"]
        return f"https://yb.tencent.com/s/{share_id}"
    return None

async def main():
    pdf_path = os.path.abspath("/Users/meiyiwangluokeji/Desktop/PRP/1-s2.0-S0733863526000185.pdf")
    prompt = "这是一篇真实的医美测试文献，请总结其核心医学观点。"
    
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
        
        summary = await upload_pdf_and_chat(page, pdf_path, prompt)
        print("\n" + "="*40 + " SUMMARY " + "="*40)
        print(summary)
        print("="*89 + "\n")
        
        share_link = await get_share_link_api(page)
        print(f"\n🚀 Final Share Link: {share_link}")
            
        await browser.close()
        
if __name__ == "__main__":
    asyncio.run(main())
