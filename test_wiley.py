from DrissionPage import ChromiumPage, ChromiumOptions
import time

def test_wiley_scraper():
    print("🚀 正在启动 DrissionPage 浏览器...")
    
    co = ChromiumOptions()
    co.set_browser_path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_user_data_path('~/Documents/DrissionPage_Chrome_Data_v2')
    co.set_argument('--new-window') 
    co.auto_port()

    page = ChromiumPage(co)
    
    url = "https://onlinelibrary.wiley.com/journal/dth" 
    print(f"🌐 正在访问目标页面: {url}")
    page.get(url)
    
    # --- 全自动侦测逻辑：根据网页标题判断是否绕过 Cloudflare ---
    print("🤖 正在全自动突破 Cloudflare 防护屏障...")
    
    wait_time = 0
    # 只要标题里还有 "Just a moment" 或 "Cloudflare"，就说明还在验证中
    while ("Just a moment" in page.title or "Cloudflare" in page.title) and wait_time < 30:
        time.sleep(1)
        wait_time += 1
        
    if "Just a moment" in page.title:
        print("❌ 突破失败，遇到死循环验证。")
        return
        
    print(f"✅ 突破成功！已自动进入期刊主页: {page.title}")
    
    # 触发动态内容加载
    print("⏳ 正在模拟真实用户滚动页面获取文献列表...")
    page.scroll.down(1000) 
    time.sleep(3) # 稍微多等一秒，让底部的文章标题充分加载

    print("🔍 开始提取文献标题和链接...")
    
    all_links = page.eles('tag:a')
    articles = []
    
    for a in all_links:
        class_name = a.attr('class')
        if class_name and 'issue-item__title' in class_name:
            title = a.attr('title')
            if not title:
                title = a.text.strip()
                
            href = a.attr('href')
            if title and href:
                if not href.startswith('http'):
                    href = "https://onlinelibrary.wiley.com" + href
                if not any(item['link'] == href for item in articles):
                    articles.append({'title': title, 'link': href})

    if not articles:
        print("❌ 未能提取到数据！可能是网页结构有变。")
        return

    print(f"🎉 提取成功！共找到 {len(articles)} 篇文献，下面打印前 5 篇：\n")
    print("-" * 40)
    for i, article in enumerate(articles[:5]):
        print(f"[{i+1}] {article['title']}")
        print(f"🔗 {article['link']}\n")
    print("-" * 40)

if __name__ == "__main__":
    test_wiley_scraper()