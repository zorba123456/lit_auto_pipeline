from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
from datetime import datetime

# === 配置区域 ===
RSS_FILENAME = "freshrss/wiley_dth.xml"
MEMORY_FILE = "freshrss/last_link.txt"
JOURNAL_URL = "https://onlinelibrary.wiley.com/journal/dth"

def generate_rss(articles, filename):
    """生成 RSS XML 文件"""
    rss_template = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Wiley - Dermatologic Therapy</title>
    <link>https://onlinelibrary.wiley.com/journal/dth</link>
    <description>Latest articles from Dermatologic Therapy (Auto-Sync)</description>
    <lastBuildDate>{build_date}</lastBuildDate>
    {items}
</channel>
</rss>"""

    item_template = """
    <item>
        <title><![CDATA[{title}]]></title>
        <link>{link}</link>
        <guid>{link}</guid>
    </item>"""

    items_str = ""
    for article in articles:
        items_str += item_template.format(title=article['title'], link=article['link'])

    build_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss_content = rss_template.format(build_date=build_date, items=items_str)

    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"\n✅ RSS 文件已更新: {filename}")

def get_last_link():
    """读取上次抓取的最新一条链接"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def save_last_link(link):
    """记录本次抓取的最新一条链接"""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(link)

def test_wiley_scraper():
    print("🚀 启动自动化同步程序...")
    
    co = ChromiumOptions()
    co.set_browser_path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_user_data_path('~/Documents/DrissionPage_Chrome_Data_v2')
    co.set_argument('--new-window') 
    co.auto_port()

    page = ChromiumPage(co)
    page.get(JOURNAL_URL)
    
    # 1. 自动绕过验证
    print("⏳ 等待 Cloudflare 验证...")
    wait_time = 0
    while ("Just a moment" in page.title or "Cloudflare" in page.title) and wait_time < 45:
        time.sleep(2)
        wait_time += 2
    
    if "Just a moment" in page.title:
        print("❌ 验证超时，请检查网络节点。")
        return

    print(f"✅ 已进入期刊主页: {page.title}")
    
    # 2. 读取记忆
    last_top_link = get_last_link()
    print(f"📜 记忆中的最后一条文献链接: {last_top_link}")

    articles = []
    found_old_article = False
    
    # 3. 智能抓取逻辑
    for page_num in range(1, 6):  # 最多尝试翻 5 页，防止极端情况死循环
        print(f"🔍 正在扫描第 {page_num} 页内容...")
        
        # 触发一点滚动确保加载
        page.scroll.down(800)
        time.sleep(2)
        
        # 获取当前页面所有文献标题链接
        # 修正：DrissionPage 推荐使用更加健壮的定位方式
        links = page.eles('tag:a@@class:issue-item__title')
        
        if not links:
            print("⚠️ 未能在当前页面找到文献元素。")
            break

        for a in links:
            title = a.attr('title') or a.text.strip()
            href = a.attr('href')
            if not href.startswith('http'):
                href = "https://onlinelibrary.wiley.com" + href
            
            # 命中记忆：如果遇到上次抓过的链接，立即停止
            if last_top_link and href == last_top_link:
                print(f"✨ 发现旧文献节点，停止采集：{title}")
                found_old_article = True
                break
            
            if not any(item['link'] == href for item in articles):
                articles.append({'title': title, 'link': href})

        # 如果抓到了旧文章，或者没看到 "More Articles" 按钮，就彻底退出循环
        more_btn = page.ele('text:More Articles')
        if found_old_article or not more_btn:
            if not more_btn: print("🏁 已到达网页最底部。")
            break
        
        # 如果第一页全是新文章，没撞到记忆，则点击加载更多
        print("🚩 未触达旧节点，尝试加载更多文献...")
        more_btn.click()
        time.sleep(4)

    # 4. 结算与保存
    if articles:
        # 将本次抓到的第一条存入记忆（作为下次的终点）
        save_last_link(articles[0]['link'])
        # 生成 XML
        generate_rss(articles, RSS_FILENAME)
        print(f"🎉 同步完成！本次新增/更新了 {len(articles)} 条文献。")
    else:
        print("☕ 没有检测到新文献更新。")

if __name__ == "__main__":
    test_wiley_scraper()