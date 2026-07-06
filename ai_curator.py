import os
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests

# === Configuration ===
DATA_DIR = "/Users/meiyiwangluokeji/coding/inoreader-aes-filter/data"
RSS_INPUT_DIR = "/Users/meiyiwangluokeji/coding/lit_auto_pipeline/aes-feeds"
OUTPUT_FILE = "/Users/meiyiwangluokeji/coding/lit_auto_pipeline/aes-feeds/filtered_literature.xml"

# We support DeepSeek and Gemini API endpoints.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

def load_training_data():
    """Dynamically loads the training set and notes from the 8300 local system."""
    system_prompt_path = os.path.join(DATA_DIR, "system-prompt.txt")
    learning_set_path = os.path.join(DATA_DIR, "learning-set.json")
    learning_notes_path = os.path.join(DATA_DIR, "learning_notes.jsonl")
    taxonomy_notes_path = os.path.join(DATA_DIR, "taxonomy_notes.jsonl")

    # 1. System Prompt
    system_prompt = "你是医美内容筛选专家。"
    if os.path.exists(system_prompt_path):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

    # 2. Learning Notes (The human's dynamic rules & corrections)
    notes = []
    if os.path.exists(learning_notes_path):
        with open(learning_notes_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        title = item.get("title", "")
                        relevant = item.get("relevant", None)
                        reason = item.get("reason", "")
                        note_val = item.get("note", "")
                        
                        rule = ""
                        if reason:
                            status = "符合/保留" if relevant is True else "不符合/剔除"
                            rule = f"文献《{title}》判定为【{status}】，原因: {reason}"
                        elif note_val:
                            rule = f"文献《{title}》的分类为: {note_val}"
                        
                        if rule:
                            notes.append(rule)
                    except:
                        pass

    # 2b. Taxonomy Notes (Human categorization)
    if os.path.exists(taxonomy_notes_path):
        with open(taxonomy_notes_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        title = item.get("title", "")
                        note_val = item.get("note", "")
                        tags = item.get("tags", [])
                        if tags:
                            notes.append(f"文献《{title}》的分类应为: {', '.join(tags)}")
                        elif note_val:
                            notes.append(f"文献《{title}》的分类应为: {note_val}")
                    except:
                        pass
    
    notes_text = ""
    if notes:
        # Take the most recent 20 notes to keep prompt size manageable
        notes_text = "\n\n【人类导师最新强调的判断法则与纠错记录】\n" + "\n".join([f"- {n}" for n in notes[-20:]])

    # 3. Few-Shot Examples
    positives = []
    negatives = []
    if os.path.exists(learning_set_path):
        try:
            with open(learning_set_path, "r", encoding="utf-8") as f:
                ls = json.load(f)
                # Take the most recent 15 examples
                raw_pos = ls.get("positives", [])[-15:]
                raw_neg = ls.get("negatives", [])[-15:]
                
                for p in raw_pos:
                    title = p.get("title", "")
                    reason = p.get("reason", "")
                    if reason:
                        positives.append(f"《{title}》 (理由: {reason})")
                    else:
                        positives.append(f"《{title}》")
                        
                for n in raw_neg:
                    title = n.get("title", "")
                    reason = n.get("reason", "")
                    if reason:
                        negatives.append(f"《{title}》 (理由: {reason})")
                    else:
                        negatives.append(f"《{title}》")
        except Exception as e:
            print(f"Failed to load learning set: {e}")

    few_shot_text = ""
    if positives or negatives:
        few_shot_text = "\n\n【Few-Shot 示例参考】\n"
        if positives:
            few_shot_text += "以下文献是符合要求的（Positives）：\n" + "\n".join([f"- {p}" for p in positives]) + "\n"
        if negatives:
            few_shot_text += "以下文献是不符合要求的（Negatives）：\n" + "\n".join([f"- {n}" for n in negatives]) + "\n"

    final_system_prompt = system_prompt + notes_text + few_shot_text
    return final_system_prompt


def evaluate_article_with_llm(title, abstract, system_prompt):
    """Calls DeepSeek or Gemini API to evaluate the article."""
    if not DEEPSEEK_API_KEY and not GEMINI_API_KEY:
        print("⚠️ Warning: Neither DEEPSEEK_API_KEY nor GEMINI_API_KEY is set. Mocking the API response to 'pass' for testing.")
        return {"pass": True, "reason": "Mocked pass", "tags": ["MockTag"]}

    user_content = f"标题: {title}\n\n摘要: {abstract}\n\n请严格判断该文献是否值得医美专业人士阅读，并打上1-2个分类标签。"
    user_content += "\n必须返回JSON格式，且仅返回JSON。格式：{\"pass\": true/false, \"reason\": \"简短理由\", \"tags\": [\"标签1\", \"标签2\"]}"

    if DEEPSEEK_API_KEY:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        data = {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            resp_json = response.json()

            # 向 8300 总控台上报调用消耗
            try:
                usage = resp_json.get("usage", {})
                log_payload = {
                    "app": "lit_auto_pipeline",
                    "article_count": 1,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "model": resp_json.get("model", "deepseek-v4-flash"),
                    "status": "ok"
                }
                requests.post("http://127.0.0.1:8300/api/aes/log-usage", json=log_payload, timeout=1.0)
            except Exception:
                pass

            content = resp_json["choices"][0]["message"]["content"]
            # In case the model returns markdown wrapped json
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error calling DeepSeek LLM for '{title}': {e}")
            return {"pass": False, "reason": "Error during DeepSeek LLM call", "tags": []}

    elif GEMINI_API_KEY:
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": user_content}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            content = res_json["candidates"][0]["content"]["parts"][0]["text"]
            # In case the model returns markdown wrapped json
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error calling Gemini LLM for '{title}': {e}")
            return {"pass": False, "reason": "Error during Gemini LLM call", "tags": []}


def process_rss_feeds():
    print("🚀 启动 AI Curator (文献过滤打标引擎)...")
    system_prompt = load_training_data()
    print("✅ 已动态挂载最新训练集 (System Prompt + Notes + Few-Shot)")
    
    if not os.path.exists(RSS_INPUT_DIR):
        print(f"Input directory not found: {RSS_INPUT_DIR}")
        return

    # Find an XML file to process. (For now, we just pick the first XML we find)
    xml_files = [f for f in os.listdir(RSS_INPUT_DIR) if f.endswith('.xml') and f != "filtered_literature.xml"]
    if not xml_files:
        print("No raw XML feeds found to process.")
        return
        
    input_file = os.path.join(RSS_INPUT_DIR, xml_files[0])
    print(f"📄 Processing: {input_file}")
    
    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML {input_file}: {e}")
        return

    channel = root.find("channel")
    if channel is None:
        print("Invalid RSS feed: no <channel>")
        return

    items_to_remove = []
    
    # Evaluate each item
    for item in channel.findall("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        
        title = title_el.text if title_el is not None else ""
        abstract = desc_el.text if desc_el is not None else ""
        
        print(f"\n🔍 正在评估: {title[:50]}...")
        result = evaluate_article_with_llm(title, abstract, system_prompt)
        
        if result.get("pass", False):
            print(f"✅ Pass! Tags: {result.get('tags', [])}")
            # Inject tags as category
            for tag in result.get("tags", []):
                cat_el = ET.SubElement(item, "category")
                cat_el.text = tag
        else:
            print(f"❌ Reject: {result.get('reason', 'No reason provided')}")
            items_to_remove.append(item)

    # Remove rejected items from the tree
    for item in items_to_remove:
        channel.remove(item)

    # Save the filtered XML
    xml_str = ET.tostring(root, encoding='utf-8')
    parsed_str = minidom.parseString(xml_str)
    pretty_str = parsed_str.toprettyxml(indent="  ")
    
    # Remove blank lines caused by toprettyxml
    pretty_str = '\n'.join([line for line in pretty_str.split('\n') if line.strip()])
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(pretty_str)
        
    print(f"\n🎉 处理完毕! 过滤后的精华 RSS 已输出至: {OUTPUT_FILE}")
    print(f"保留了 {len(channel.findall('item'))} 条文献。")

if __name__ == "__main__":
    process_rss_feeds()
