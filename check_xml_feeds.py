import os
import glob
import xml.etree.ElementTree as ET

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDS_DIR = os.path.join(CURRENT_DIR, "aes-feeds")

def main():
    print("=" * 80)
    print("📋 AES-INTEL CNKI 本地 XML 盘片数据排查工具")
    print("=" * 80)
    
    xml_files = glob.glob(os.path.join(FEEDS_DIR, "cnki_*.xml"))
    if not xml_files:
        print(f"❌ 未在 {FEEDS_DIR} 目录下找到 cnki_*.xml 文件！")
        return
        
    xml_files.sort()
    
    for xml_path in xml_files:
        filename = os.path.basename(xml_path)
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                print(f"⚠️ {filename}: 格式错误，找不到 <channel> 节点")
                continue
                
            title = channel.find("title").text if channel.find("title") is not None else "未知"
            last_build = channel.find("pubDate").text if channel.find("pubDate") is not None else (
                channel.find("lastBuildDate").text if channel.find("lastBuildDate") is not None else "未知"
            )
            
            items = channel.findall("item")
            print(f"\n📰 期刊: {title} ({filename})")
            print(f"⏰ 最近生成时间: {last_build}")
            print(f"📦 包含文献总数: {len(items)} 篇")
            
            if items:
                print("🔥 最新 3 篇文献预览:")
                for i, item in enumerate(items[:3]):
                    item_title = item.find("title").text if item.find("title") is not None else "无标题"
                    item_link = item.find("link").text if item.find("link") is not None else "无链接"
                    item_pub = item.find("pubDate").text if item.find("pubDate") is not None else "无时间"
                    print(f"  {i+1}. {item_title}")
                    print(f"     PubDate: {item_pub}")
                    print(f"     Link:    {item_link}")
            else:
                print("  📭 目前无文献数据")
            print("-" * 80)
            
        except Exception as e:
            print(f"❌ 解析 {filename} 失败: {e}")

if __name__ == "__main__":
    main()
