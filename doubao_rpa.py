import asyncio
import os
import argparse
from playwright.async_api import async_playwright

async def upload_and_chat(page, pdf_path, prompt):
    print("🔗 正在打开豆包对话页...")
    await page.goto("https://www.doubao.com/chat/", wait_until="domcontentloaded")
    
    await page.wait_for_selector("textarea", timeout=15000)
    await page.wait_for_timeout(2000)
    
    print(f"📄 正在上传 PDF 文件: {os.path.basename(pdf_path)}")
    await page.set_input_files("input[type='file']", pdf_path)
        
    print("⏳ 等待文件解析 (5秒)...")
    await page.wait_for_timeout(5000)
    
    print(f"✍️ 输入提示词: {prompt}")
    await page.locator("textarea").first.fill(prompt)
    await page.wait_for_timeout(500)
    
    print("🚀 发送！")
    await page.keyboard.press("Enter")
    
    print("⏳ 智能监听 AI 输出状态...")
    await page.wait_for_timeout(3000) 
    
    stable_count = 0
    last_len = 0
    while stable_count < 10: # 连续 5 秒不增长
        await page.wait_for_timeout(500)
        current_len = await page.evaluate("document.body.innerText.length")
        if current_len > last_len:
            last_len = current_len
            stable_count = 0
        else:
            stable_count += 1
            
    print("✅ AI 判定输出完毕！")
    
    # 提取文字总结
    print("🔍 提取文字总结...")
    full_text = await page.evaluate("document.body.innerText")
    summary = ""
    if prompt in full_text:
        raw_summary = full_text.split(prompt)[-1].strip()
        # 简单清洗掉尾部的乱码按钮文字
        lines = raw_summary.split('\n')
        clean_lines = []
        for line in lines:
            txt = line.strip()
            if txt in ["分享", "复制", "重新生成", "不满意", "满意", "下载电脑版", "新对话", "复制链接", "下载", "朗读"]:
                continue
            clean_lines.append(txt)
        summary = '\n'.join(clean_lines).strip()
    else:
        summary = full_text # fallback
        
    return summary


async def get_share_link(page):
    intercepted_share_id = None
    
    async def on_response(response):
        nonlocal intercepted_share_id
        if "/im/message/share/share_token" in response.url and response.status == 200:
            try:
                data = await response.json()
                if "data" in data and "share_token" in data["data"]:
                    token = data["data"]["share_token"]
                    print(f"🔥 截获核心 Token: {token[:20]}...")
                    import base64, json
                    payload = token.split('.')[1]
                    payload += "=" * ((4 - len(payload) % 4) % 4)
                    decoded = base64.b64decode(payload).decode('utf-8')
                    payload_data = json.loads(decoded)
                    if "share_id" in payload_data:
                        intercepted_share_id = payload_data["share_id"]
            except:
                pass
                
    page.on("response", on_response)
    
    print("📤 锁定并点击右上角『分享』按钮...")
    share_btn = page.locator('button:has(svg path[d^="M11.052 3.80762"])').first
    try:
        await share_btn.click(timeout=5000)
    except:
        print("⚠️ 未找到全局分享按钮！")
        return None
        
    print("⏳ 等待分享面板弹出...")
    await page.wait_for_timeout(1500)
    
    print("👆 点击『确认分享』按钮...")
    await page.evaluate('''() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const primaryBtns = buttons.filter(b => b.className.includes('semi-button-primary'));
        const textBtns = buttons.filter(b => b.innerText && (b.innerText.includes('复制链接') || b.innerText.includes('创建') || b.innerText.includes('分享')));
        
        if (primaryBtns.length > 0) {
            primaryBtns[primaryBtns.length - 1].click();
        } else if (textBtns.length > 0) {
            textBtns[textBtns.length - 1].click();
        }
    }''')
        
    await page.wait_for_timeout(3000)
    
    if intercepted_share_id:
        return f"https://www.doubao.com/thread/{intercepted_share_id}"
    return None

async def process_pdf_with_doubao(pdf_path, prompt, mode="share"):
    async with async_playwright() as p:
        user_data_dir = "./doubao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 800);")
        
        summary = await upload_and_chat(page, pdf_path, prompt)
        
        share_link = None
        if mode == "share":
            share_link = await get_share_link(page)
            
        await browser.close()
        return summary, share_link

def main():
    parser = argparse.ArgumentParser(description="Doubao PDF RPA Pipeline")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--prompt", default="这是一篇真实的医美测试文献，请总结其核心医学观点。", help="Prompt to send to AI")
    parser.add_argument("--mode", choices=["silent", "share"], default="share", help="Running mode")
    args = parser.parse_args()
    
    abs_pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(abs_pdf_path):
        print(f"❌ 文件不存在: {abs_pdf_path}")
        return
        
    print(f"===== 🚀 启动豆包 RPA =====")
    print(f"📄 Target: {abs_pdf_path}")
    
    summary, share_link = asyncio.run(process_pdf_with_doubao(abs_pdf_path, args.prompt, args.mode))
    
    out_file = abs_pdf_path + "_doubao_result.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        if share_link:
            f.write(f"Share Link: {share_link}\n\n")
        f.write("Summary:\n")
        f.write(summary)
        
    print("\n" + "="*40 + " SUMMARY " + "="*40)
    print(summary[:500] + "..." if len(summary) > 500 else summary)
    print("="*89 + "\n")
    if share_link:
        print(f"🔗 专属分享链接: {share_link}")
        
    print(f"✅ 结果已保存至: {out_file}")

if __name__ == "__main__":
    main()
