import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 启动豆包全自动分享流程（稳定版）...")
    profile_dir = "./doubao_profile"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        
        # 拦截剪贴板写入，这是最绝的一招，100% 成功率！
        await page.add_init_script("""
            window.interceptedShareLink = "";
            const originalWriteText = navigator.clipboard.writeText;
            navigator.clipboard.writeText = async function(text) {
                window.interceptedShareLink = text;
                return Promise.resolve();
            };
        """)
        
        print("🔗 正在打开豆包对话页...")
        # 修改等待策略：不要死等所有资源和广告加载完毕（可能长达30秒），只要页面骨架出来就立刻开始行动！
        await page.goto("https://www.doubao.com/chat/", wait_until="domcontentloaded")
        
        await page.wait_for_selector("textarea", timeout=15000)
        await page.wait_for_timeout(3000)
        
        pdf_path = "/Users/meiyiwangluokeji/Desktop/collagen/CCID-603794-operational-standard-for-tissue-extracted-collagen-facial-in.pdf"
        
        print("📄 正在自动上传 PDF 文件...")
        # 豆包的文件上传输入框是预先渲染好的 hidden input
        await page.set_input_files("input[type='file']", pdf_path)
            
        print("⏳ 等待文件解析 (5秒)...")
        await page.wait_for_timeout(5000)
        
        prompt = "这是一篇真实的医美测试文献，请总结其核心医学观点。"
        print(f"✍️ 正在输入提示词: {prompt}")
        
        # 1. 使用原生的 fill，让输入过程可见，并确保 React 能监听到
        # 加上 .first 解决 strict mode 问题（页面上有两个 textarea）
        await page.locator("textarea").first.fill(prompt)
        await page.wait_for_timeout(500)
        
        print("🚀 发送！")
        await page.keyboard.press("Enter")
        
        # 2. 智能等待机制：监听页面文字增长，真正判断 AI 是否“吐完”！
        print("⏳ 正在智能监听 AI 输出状态...")
        await page.wait_for_timeout(3000) # 给 AI 一点“思考”起步的时间
        
        stable_count = 0
        last_len = 0
        while stable_count < 10: # 连续 5 秒（10次 * 0.5s）字数没变，就认为吐完了
            await page.wait_for_timeout(500)
            current_len = await page.evaluate("document.body.innerText.length")
            if current_len > last_len:
                last_len = current_len
                stable_count = 0
            else:
                stable_count += 1
                
        print("✅ AI 字数停止增长，判定为回答输出完毕！")
        
        # 监听分享 API
        intercepted_share_id = None
        async def on_response(response):
            nonlocal intercepted_share_id
            if "/im/message/share/share_token" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    if "data" in data and "share_token" in data["data"]:
                        token = data["data"]["share_token"]
                        print(f"🔥 截获到核心分享 Token: {token[:30]}...")
                        import base64
                        import json
                        payload = token.split('.')[1]
                        payload += "=" * ((4 - len(payload) % 4) % 4)
                        decoded = base64.b64decode(payload).decode('utf-8')
                        payload_data = json.loads(decoded)
                        if "share_id" in payload_data:
                            intercepted_share_id = payload_data["share_id"]
                            print(f"🎯 成功解析出 share_id: {intercepted_share_id}")
                except Exception as e:
                    pass
        page.on("response", on_response)
        
        # 3. 终极一击：直接通过 SVG 矢量图路径的开头精准锁定“分享”图标！
        # 分享图标的 path d 以 M11.052 3.80762 开头，这个是一个向外指的箭头，绝对不可能点错！
        print("📤 正在通过 SVG 矢量特征精准锁定并点击右上角『分享』按钮...")
        share_btn = page.locator('button:has(svg path[d^="M11.052 3.80762"])').first
        
        try:
            await share_btn.click(timeout=5000)
            print("✅ 成功点击真正的分享按钮！")
        except Exception as e:
            print("⚠️ 未能找到或点击分享按钮，可能是 AI 还在生成，或者界面有变动！")
            
        print("⏳ 正在等待分享面板弹出...")
        await page.wait_for_timeout(1500)
        
        # 4. 点击面板中的确认按钮（通常是带有 semi-button-primary class 的蓝色大按钮，或是写着“复制链接”的按钮）
        print("👆 正在点击面板中的『创建分享/复制链接』按钮...")
        await page.evaluate('''() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            // 寻找带有 primary 样式的主按钮
            const primaryBtns = buttons.filter(b => b.className.includes('semi-button-primary'));
            // 寻找包含相关文字的按钮
            const textBtns = buttons.filter(b => b.innerText && (b.innerText.includes('复制链接') || b.innerText.includes('创建') || b.innerText.includes('分享')));
            
            if (primaryBtns.length > 0) {
                // 点击最靠后渲染的 primary 按钮（通常是刚弹出来的弹窗按钮）
                primaryBtns[primaryBtns.length - 1].click();
            } else if (textBtns.length > 0) {
                textBtns[textBtns.length - 1].click();
            }
        }''')
            
        # 等待 3 秒看有没有触发分享网络请求
        print("⏳ 正在等待接口返回...")
        await page.wait_for_timeout(3000)
                
        print("\\n=======================================================")
        if intercepted_share_id:
            share_url = f"https://www.doubao.com/thread/{intercepted_share_id}"
            print("🎉 恭喜！全流程自动化执行完毕！神乎其技的拦截！")
            print(f"🔗 纯后端拦截提取的最终分享链接: {share_url}")
        else:
            print("❌ 提取链接失败，未能触发分享 API！")
        print("=======================================================\\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
