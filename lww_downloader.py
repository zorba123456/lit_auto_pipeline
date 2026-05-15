import os
import json
import time
from drission_page import ChromiumPage, ChromiumOptions

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def download_403_feeds():
    config = load_config()
    
    # 1. 初始化 DrissionPage (复用 Mac 本地 Chrome)
    co = ChromiumOptions()
    co.set_argument('--headless')  # 无头模式，不弹出浏览器窗口
    co.set_argument('--no-sandbox')
    
    print("🚀 启动 Chromium 浏览器内核...")
    page = ChromiumPage(co)
    
    # 2. 设定输出目录为目前的 freshrss 文件夹
    output_dir = './freshrss'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 3. 遍历配置文件，逐个突破
    for journal in config['lww_journals']:
        name = journal['name']
        url = journal['url']
        output_path = os.path.join(output_dir, f"{name}.xml")
        
        print(f"📡 正在攻坚: {name}")
        
        try:
            # 访问 RSS 地址
            page.get(url)
            
            # 强制等待 3 秒，留给 Cloudflare 走完五秒盾验证
            time.sleep(3) 
            
            # 提取浏览器渲染出的纯文本源码 (即 XML)
            raw_xml = page.html
            
            # 基础校验：确认抓下来的是 XML 而不是 403 拦截页
            if "<rss" in raw_xml or "<feed" in raw_xml:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(raw_xml)
                print(f"✅ 成功存盘: {output_path}")
            else:
                print(f"❌ 抓取失败，未检测到有效 RSS 标记: {name}")
                
        except Exception as e:
            print(f"💥 {name} 发生异常: {e}")
            
    # 关闭浏览器
    page.quit()
    print("🏁 代购完毕。")

if __name__ == "__main__":
    download_403_feeds()