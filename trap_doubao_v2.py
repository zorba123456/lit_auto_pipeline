import asyncio
from playwright.async_api import async_playwright
import json
import os

async def handle_request(route, request):
    # Log any request that looks like creating a share/thread
    url = request.url.lower()
    if "share" in url or "publish" in url or "thread" in url:
        with open("doubao_api_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[INTERCEPTED API REQUEST]\n")
            f.write(f"URL: {request.url}\n")
            f.write(f"Method: {request.method}\n")
            # We don't print all headers to avoid clutter, just the crucial ones
            f.write("Headers intercepted.\n") 
            
            post_data = request.post_data
            if post_data:
                f.write("Payload:\n")
                try:
                    parsed = json.loads(post_data)
                    f.write(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n")
                except:
                    f.write(post_data + "\n")
            f.write("--------------------------------------------------\n")
            f.flush()
            print(f"Captured a potential API: {request.url}")
        
    await route.continue_()

async def main():
    print("Launching Doubao Trap Script V2...")
    
    # Clear previous log
    if os.path.exists("doubao_api_log.txt"):
        os.remove("doubao_api_log.txt")
        
    profile_dir = "./doubao_profile"
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        await page.route("**/*", handle_request)
        
        print("\n=======================================================")
        print("Please click the TOP-RIGHT Share Button (Button 2)!")
        print("Logs are being written to doubao_api_log.txt in real-time.")
        print("=======================================================\n")
        
        await page.goto("https://www.doubao.com/chat/")
        
        # Keep open for 5 minutes
        try:
            await page.wait_for_timeout(300 * 1000)
        except KeyboardInterrupt:
            pass
            
        print("Closing browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
