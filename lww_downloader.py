import os
import json
import time
from DrissionPage import ChromiumPage, ChromiumOptions

def load_config():
    """读取配置文件"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def download_403_feeds():
    config = load_config()
    meta = config.get('_meta', {})
    version = meta.get('version', '1.0.1') # 升级为智能等待版本
    
    print("=" * 45)
    print(f"🚀 启动 LWW 强攻管线 [v{version} - 智能雷达版]")
    print("=" * 45)
    
    co = ChromiumOptions()
    
    # 暂时保持 False，让你亲眼看着它通关。确认全部成功后，把这行改成 True 就可以静默后台运行了。
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
            
            # 【核心优化】：智能雷达扫描，最高等 15 秒
            success = False
            for i in range(15):
                raw_xml = page.html
                # 只要页面源码里刷出了 rss 或 feed 标签，说明盾已经过了
                if "<rss" in raw_xml.lower() or "<feed" in raw_xml.lower():
                    success = True
                    break
                time.sleep(1)  # 没刷出来就等 1 秒再看一眼
            
            if success:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(raw_xml)
                print(f"✅ 成功存盘: {output_path}")
            else:
                print(f"❌ 超时 15 秒仍未看到有效内容，抓取失败。")
                
        except Exception as e:
            print(f"⚠️ 抓取 {name} 时发生异常: {e}")
            
    page.quit()
    print("\n" + "=" * 45)
    print(f"🏁 [v{version}] 任务结束，所有阵地攻克完毕！")
    print("=" * 45)

if __name__ == "__main__":
    download_403_feeds()