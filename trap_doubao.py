import asyncio
from playwright.async_api import async_playwright
import json
import os

async def handle_request(route, request):
    # Log requests that look like a share API call
    if "share" in request.url.lower():
        print(f"\n[INTERCEPTED SHARE API REQUEST]")
        print(f"URL: {request.url}")
        print(f"Method: {request.method}")
        print(f"Headers: {request.headers}")
        
        post_data = request.post_data
        if post_data:
            print("Payload:")
            try:
                # Try to pretty print JSON if it's JSON
                parsed = json.loads(post_data)
                print(json.dumps(parsed, indent=2, ensure_ascii=False))
            except:
                print(post_data)
        print("--------------------------------------------------\n")
        
    await route.continue_()

async def main():
    print("Launching Doubao Trap Script...")
    
    # Ensure profile dir exists
    profile_dir = "./doubao_profile"
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,  # Must be visible so user can operate
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        # Intercept ALL network requests to look for the share API
        await page.route("**/*", handle_request)
        
        print("\n=======================================================")
        print("1. Opening doubao.com. Please log in if you haven't.")
        print("2. Upload a PDF, ask a question, and manually click 'Share'.")
        print("3. I am listening in the background to steal the Share API!")
        print("=======================================================\n")
        
        await page.goto("https://www.doubao.com/")
        
        # Keep the script running for 10 minutes to give the user time
        print("Script will remain active for 10 minutes. Press Ctrl+C in terminal to stop earlier.")
        try:
            await page.wait_for_timeout(600 * 1000)
        except KeyboardInterrupt:
            pass
            
        print("Closing browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
