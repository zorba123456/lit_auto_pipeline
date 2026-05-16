import os
import json
import time
from DrissionPage import ChromiumPage, ChromiumOptions

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def download_403_feeds():
    config = load_config()
    meta = config.get('_meta', {})
    version = meta.get('version', '1.0.4') # 升级为悬停侦查版
    
    print("=" * 45)
    print(f"🚀 启动 LWW 强攻管线 [v{version} - 悬停侦查版]")
    print("=" * 45)
    
    co = ChromiumOptions()
    co.headless(False) 
    co.set_argument('--no-sandbox')    
    co.set_argument('--disable-gpu')   
    co.set_local_port(9666)            
    
    try:
        print("🔧 正在初始化浏览器内核 (Port: 9666)...")
        page = ChromiumPage(co)
    except Exception as e:
        print(f"💥 内核启动失败！错误详情: {e}")
        return

    output_dir = './freshrss/lww_feeds'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    journals = config.get('lww_journals', [])
    for journal in journals:
        name = journal['name']
        url = journal['url']
        output_path = os.path.join(output_dir, f"{name}.xml")
        
        print(f"\n📡 正在抓取: {name}")
        
        try:
            page.get(url)
            success = False
            
            for attempt in range(2):
                if success:
                    break
                if attempt == 1:
                    print("   🔄 触发防卡死机制，刷新页面重试...")
                    page.refresh()
                    time.sleep(2) 
                
                for i in range(20):
                    raw_xml = page.html
                    if any(tag in raw_xml.lower() for tag in ["<rss", "<feed", "<?xml", "cdata"]):
                        success = True
                        break
                    
                    try:
                        cf_frame = page.get_frame('@src^https://challenges.cloudflare.com', timeout=0.5)
                        if cf_frame:
                            box = cf_frame.ele('.mark', timeout=0.5) or cf_frame.ele('t:label', timeout=0.5)
                            if box:
                                box.click()
                    except:
                        pass
                        
                    time.sleep(1) 
            
            if success:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(raw_xml)
                print(f"✅ 成功存盘: {output_path}")
            else:
                error_img_path = os.path.join(output_dir, f"error_{name}.png")
                page.get_screenshot(path=error_img_path)
                print(f"❌ 抓取失败！已截图存至: {error_img_path}")
                
                # 【核心修改】：强制程序在这里挂起，保留案发现场！
                print("\n🛑 【系统暂停】已为你保留案发现场！")
                print("👉 请立刻切换到弹出的浏览器窗口，看看页面上到底卡在了哪里。")
                input("🕵️‍♂️ 看完情报后，请在终端里点击一下，然后按【回车键】继续...")
                
        except Exception as e:
            print(f"⚠️ 抓取 {name} 时发生异常: {e}")
            
    # 【核心修改】：注释掉退出命令，防止浏览器自动闪退
    page.quit() 
    print("\n" + "=" * 45)
    print(f"🏁 [v{version}] 任务结束！(浏览器保留开启状态，请手动关闭)")
    print("=" * 45)

if __name__ == "__main__":
    download_403_feeds()