#!/usr/bin/env python3
"""
IMA 医美文献知识库 — 定时巡查脚本（搜索定位版）
"""
VENV_PYTHON = "/Users/meiyiwangluokeji/.hermes/scripts/venv_ima/bin/python"
import sys, os
if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import uiautomator2 as u2
import time, subprocess, re, json, sys, os
from lxml import etree
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
ADB = "/opt/homebrew/bin/adb"
EMULATOR = os.path.expanduser("~/Library/Android/sdk/emulator/emulator/emulator")
AVD_NAME = "pixel_ima_cn"
SNAPSHOT = BASE / "ima_snapshot.json"
FAILED = BASE / "failed_list.json"
NEEDS_MANUAL = BASE / "needs_manual.json"
BASE_INBOX = Path(os.path.expanduser("~/coding/lit_auto_pipeline/data/pdf_inbox/ima"))
DLDIR = "/sdcard/Download/"

# 掉线重登防护：navigate 失败后用户点「现在重新登录」时置 True，
# 让主流程 finally 跳过关模拟器，保持模拟器供用户扫码登录。
KEEP_EMULATOR_BE = False

BATCH_DATE = datetime.now().strftime("%Y-%m-%d")
INBOX = str(BASE_INBOX / BATCH_DATE)

# ─── 工具函数 ───

# 通知中心统一写入端（P0，见 ~/coding/notification-hub/PLAN.md §5）
NOTIFY_CLI = Path(os.path.expanduser("~/coding/notification-hub/notify_cli.py"))

def notify(title, msg, level="info", result=""):
    """事后通知：留档 notifications.jsonl + 非阻塞横幅（P0 接入通知中心）。
    不阻塞脚本，弹窗失败不影响留档。"""
    try:
        subprocess.run(
            ["python3", str(NOTIFY_CLI), "--source", "ima_patrol",
             "--level", level, "--title", title, "--msg", msg, "--result", result,
             "--type", "report"],
            capture_output=True, timeout=30,
        )
    except Exception:
        pass

def notify_urgent(title, msg, button="我处理好了"):
    """阻塞式重要通知：IMA 需登录或异常时用（弹出对话框，等用户点按钮才继续）。

    v1 加固：对 osascript 单行 -e 做转义（\\\\、\"、换行→空格），否则含换行/引号的消息会让
    osascript 语法报错导致 notification 静默失败——正是要防的『掉线却无提醒』主因。
    返回用户点击的按钮名（一般唯一按钮）；空串/异常表示未正常完成。
    """
    def _esc(s: str) -> str:
        return (s.replace("\\", "\\\\").replace('"', '\\"')
                 .replace("\n", " ").replace("\r", " "))
    try:
        r = subprocess.run(
            ["osascript", "-e",
             f'display dialog "{_esc(msg)}" with title "{_esc(title)}" '
             f'buttons {{"{_esc(button)}"}} default button 1 with icon 1'],
            timeout=3600, capture_output=True, text=True,
        )
        if r.returncode == 0:
            # osascript 输出形如  button returned:现在重新登录
            m = re.search(r"button returned:(.+)", r.stdout or "")
            return (button if not m else m.group(1).strip())
        return ""
    except Exception:
        return ""

def load_snapshot():
    if SNAPSHOT.exists():
        try: return json.load(open(SNAPSHOT))
        except: return {}
    return {}

def save_snapshot(data):
    json.dump(data, open(SNAPSHOT, "w"), ensure_ascii=False, indent=2)

# ─── 模拟器 ───

EMU_LOG = "/tmp/ima_emulator.log"

def _clear_stale_locks():
    """清理 AVD 陈旧锁文件（上次异常强杀可能残留，导致本次启动即退）。"""
    import glob
    for lock in glob.glob(os.path.expanduser(f"~/.android/avd/{AVD_NAME}.avd/*.lock")):
        try:
            os.remove(lock)
        except Exception:
            pass

def _launch_emulator():
    """启动模拟器（无窗口 + 软件渲染，最稳；日志落盘便于诊断）。返回 Popen。"""
    _clear_stale_locks()
    subprocess.run([ADB, "start-server"], capture_output=True, timeout=10)
    log = open(EMU_LOG, "a", encoding="utf-8")
    # 2026-08-06 检修: 加 -no-snapshot 冷启动(跳过 default_boot 快照恢复)。
    # 根因: 快照恢复后的 adb/adb-shell 通道运行几分钟后间歇退化(am start 超时/AdbError closed)。
    # 冷启动验证 adb 是否全程稳定; 若登录态受影响(导航停在登录页)再回退该参数。
    return subprocess.Popen(
        [EMULATOR, "-avd", AVD_NAME, "-no-window", "-netdelay", "none", "-netspeed", "full",
         "-gpu", "swiftshader_indirect", "-no-audio", "-no-boot-anim", "-no-snapshot"],
        stdout=log, stderr=log)

def start_emulator():
    # 已存在可用设备则直接用
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=10)
    if "emulator-5554" in r.stdout and "device" in r.stdout:
        return True
    _launch_emulator()
    # 等待 boot（60次×2s=120s）；失败则清锁重试一次
    for attempt in range(2):
        for i in range(60):
            time.sleep(2)
            r = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=10)
            if "emulator-5554" in r.stdout and "device" in r.stdout:
                r2 = subprocess.run([ADB, "shell", "getprop", "sys.boot_completed"], capture_output=True, text=True, timeout=5)
                if r2.stdout.strip() == "1":
                    time.sleep(5)
                    return True
        if attempt == 0:
            print("⚠️ 模拟器启动超时，清理残留后重试...")
            _clear_stale_locks()
            try:
                subprocess.run(["pkill", "-f", f"qemu-system.*{AVD_NAME}"], capture_output=True, timeout=5)
            except Exception:
                pass
            time.sleep(3)
            _launch_emulator()
    return False

def stop_emulator():
    """关闭模拟器：先 adb emu kill（优雅），失败/超时则进程级强杀。
    全程容错，绝不抛异常，避免 cron 误标 failed。"""
    # 1. 优雅关闭（超时/异常都吞掉，不中断 finally）
    try:
        subprocess.run([ADB, "emu", "kill"], capture_output=True, timeout=8)
    except subprocess.TimeoutExpired:
        print("adb emu kill 超时，转进程级强杀")
    except Exception:
        pass

    # 2. 短等待其退出，未退出则补强杀
    for _ in range(10):
        try:
            r = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=5)
        except Exception:
            break
        if "emulator-5554" not in r.stdout:
            return True
        time.sleep(0.5)

    # adb emu kill 未生效 → 按 AVD 名匹配 qemu 进程强杀
    try:
        subprocess.run(
            ["pkill", "-f", f"qemu-system.*{AVD_NAME}"],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass

    # 3. 再确认一次，已消失即视为成功
    time.sleep(2)
    try:
        r = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=5)
        if "emulator-5554" not in r.stdout:
            return True
    except Exception:
        pass
    return True

# ─── 导航 ───

def navigate():
    d = u2.connect('emulator-5554'); time.sleep(2)
    subprocess.run([ADB, "shell", "am", "force-stop", "com.tencent.ima"], capture_output=True, timeout=10)
    time.sleep(2)
    subprocess.run([ADB, "shell", "am", "start", "-n", "com.tencent.ima/.MainActivity"], capture_output=True, timeout=10)
    time.sleep(3)
    for retry in range(8):
        kb = d(text='知识库')
        if kb.exists(timeout=3): break
        subprocess.run([ADB, "shell", "am", "start", "-n", "com.tencent.ima/.MainActivity"], capture_output=True, timeout=10)
        time.sleep(3)
    else:
        return None
    kb = d(text='知识库')
    if kb.exists(timeout=3): kb.click(); time.sleep(2)
    ymwx = d(text='医美文献')
    if ymwx.exists(timeout=5): ymwx.click(); time.sleep(3)
    else: return None
    xml = d.dump_hierarchy()
    if xml.lower().count('.pdf') < 3: return None
    return d

# ─── 检查 ───

def _time_from_node(node):
    """在节点及其后代里找时间标签，返回匹配值或空。"""
    ct = (node.get('text','') or '').strip()
    if ct and ct != 'PDF' and len(ct) <= 10:
        if re.match(r'^\d{1,2}:\d{2}$', ct) or re.match(r'^\d{1,2}/\d{1,2}$', ct) or ct in ('昨天','前天'):
            return ct
    return ''

def get_time_label(xml_str, title):
    """从标题节点的层级结构里提取时间标签。
    修复：原实现只看「标题的直接父节点直接子节点」，卡片层级不同时(标题与时间
    不在同一直接父容器)会漏。改为向上回溯至多3级祖先，在每级后代中找时间。"""
    root = etree.fromstring(xml_str.encode())
    for n in root.iter():
        t = (n.get('text','') or '').strip()
        if t == title:
            # 层级1：直接父节点的直接子节点（原逻辑）
            p = n.getparent()
            if p is not None:
                for child in p:
                    r = _time_from_node(child)
                    if r: return r
            # 层级2/3：向上回溯祖先，在祖先的后代里找时间
            anc = p
            for _ in range(2):
                anc = anc.getparent() if anc is not None else None
                if anc is None:
                    break
                for node in anc.iter():
                    r = _time_from_node(node)
                    if r: return r
            return ''
    return ''

def scan_all(d, hit_by_file=None):
    """全屏扫描到锚点停，返回 [entries], first_title"""
    seen = set()
    entries = []
    first_title = None
    hit = False
    
    for batch in range(60):
        xml = d.dump_hierarchy()
        root = etree.fromstring(xml.encode())
        page_new = 0
        
        for n in root.iter():
            t = (n.get('text','') or '').strip()
            if '.pdf' not in t.lower() or len(t) < 15:
                continue
            if t in seen:
                continue
            seen.add(t)
            page_new += 1
            
            if first_title is None:
                first_title = t
            
            tl = get_time_label(xml, t)
            # 如果传入了锚点文件名，按文件名匹配停止
            if hit_by_file:
                if t == hit_by_file:
                    hit = True
                    break
            else:
                # 无锚点文件名时用时间标签停（兼容旧锚点格式）
                if tl == '7/27':
                    hit = True
                    break
            
            entries.append({"title": t, "label": tl})
        
        if hit:
            break
        if page_new == 0:
            # 连续3屏无新条目结束
            time.sleep(0.5)
            continue
        d.swipe(540, 1200, 540, 300, duration=0.15)
        time.sleep(1.5)
    
    return entries, first_title

# ─── 下载 ───

def pdf_count():
    r = subprocess.run([ADB, "shell", "ls", DLDIR], capture_output=True, text=True, timeout=10)
    return len([f for f in r.stdout.strip().split('\n') if f.strip().endswith('.pdf')])

def _downloaded_match(title):
    """核对模拟器 Download 里最新 PDF 是否与目标标题匹配（防下错篇）。
    文件名常被截断(>100字符)，所以比「共同前缀」而非全等。
    修复：改用 `ls -t` 按修改时间取真正最新（原 `ls` 默认按文件名排序，
    "最后一个"≠最新，导致误判不匹配）。"""
    target = title.replace('.pdf','').strip()
    try:
        r = subprocess.run([ADB, "shell", "ls", "-t", DLDIR], capture_output=True, text=True, timeout=10)
        pdfs = [f for f in r.stdout.strip().split('\n') if f.strip().endswith('.pdf')]
    except Exception:
        return False
    if not pdfs:
        return False
    latest = pdfs[0].replace('.pdf','').strip()  # ls -t 第一个 = 刚修改的最新文件
    # 目标前缀在最新文件名里出现多少字符
    n = 0
    for a, b in zip(latest, target):
        if a == b:
            n += 1
        else:
            break
    # ≥20 字符前缀命中即判为下对；否则再从 Download 里找是否已有该目标命名的文件
    if n >= 20:
        return True
    # 兜底：本目标可能因重试被系统存成 `(1)`/`(2)` 后缀，它在 ls -t 里仍最新；
    # 但也可能是最新的是别篇，而本目标其实已下到（文件名以 target 开头）。
    for f in pdfs:
        fc = f.replace('.pdf','').strip()
        # 去掉系统追加的 (n) 后缀后仍是同名缓存留下
        if fc.startswith(target) or target.startswith(fc):
            return True
    return False

def download_file(d, title):
    bef = pdf_count()
    d.click(1007, 202); time.sleep(2)
    sh = d(description='share_more')
    if sh.exists(timeout=3): sh.click()
    else:
        d.click(325, 1232)
        print("[dl] share_more 未找到,坐标兜底", end="")
    time.sleep(2)
    ps = d(text='Print')
    if ps.count >= 2: ps[1].click()
    elif ps.exists(timeout=2): ps.click()
    else:
        print("[dl] ❌ 无 Print 选项", end="")
        return False
    time.sleep(3)
    sm = d(descriptionContains='Summary')
    if sm.exists(timeout=2): sm.click(); time.sleep(1)
    sv = d(description='Save to PDF')
    if sv.exists(timeout=3): sv.click()
    else:
        d.click(975, 428)
        print("[dl] Save to PDF 未找到,坐标兜底", end="")
    time.sleep(2)
    fn = re.sub(r'[\\/:*?"<>|]', '_', title.replace('.pdf','').strip())[:100]+'.pdf'
    d.click(500, 2210); time.sleep(0.5)
    try: d.clear_text()
    except:
        d.click(500, 2210); time.sleep(0.3)
        d.long_click(500, 2210); time.sleep(0.5)
    time.sleep(0.5); d.send_keys(fn); time.sleep(0.5)
    sf = d(text='SAVE')
    if sf.exists(timeout=3): sf.click()
    else:
        d.click(927, 2211)
        print("[dl] SAVE 未找到,坐标兜底", end="")
    time.sleep(8)
    aft = pdf_count()
    if aft <= bef:
        print("[dl] ❌ pdf数未增加,下载未发生", end="")
        return False
    # 下载发生了 → 核对是否下对了目标（新增文件与目标标题是否匹配，防下错篇）
    if _downloaded_match(title):
        return True
    print("[dl] ⚠️ 新增PDF与目标标题不匹配(可能下错篇)", end="")
    return False

def tail_search_term(title):
    """取文件名尾部至少80字符，向后延伸到单词边界，作为回退搜索词"""
    clean = title.replace('.pdf','').strip()
    if len(clean) <= 80:
        return clean
    # 取最后80字符
    tail = clean[-80:]
    # 找第一个空格后的完整单词（向后延伸到单词边界）
    space_idx = tail.find(' ')
    if space_idx > 0 and space_idx < 20:
        # 如果开头截断了单词（第一个字符不是空格且20字符内有空格）
        tail = tail[space_idx+1:]
    return tail.strip()

def head_search_term(title):
    """抽取中文标题主干（首个分隔符前的'论文正题'），用于超长中文标题回退。

    这类标题常是「论文正题-机构-作者-…」结构，第一个分隔符前就是要搜的主干。
    仅对含中文的标题生成本词 && 标题超长；纯英文标题靠尾部回退即可（避免截断单词）。"""
    clean = title.replace('.pdf','').strip()
    if len(clean) <= 80:
        return None
    # 标题须含中文，否则退回尾部回退（英文在分隔符前取主干会截断单词）
    if not re.search(r'[\u4e00-\u9fff]', clean):
        return None
    # 常见分隔符（含中英文冒号、连字符、下划线、间隔号）
    for sep in ('－', '—', '：', ':', '-', '_', '·'):
        idx = clean.find(sep)
        if idx > 0:
            head = clean[:idx].strip()
            # 主干要像"正题"：不要太短，且不含作者名片段（作者名通常后面还有分隔符）
            if head and len(head) >= 5 and len(head) <= 60:
                return head
    return None

def _match_target(hits, target, search_term):
    """从搜索结果标题里，在『前3条』范围内逐条匹配目标。
    返回 (命中的标题, 命中序号) 或 (None, -1)。
    匹配优先级：精确相等 → 以目标开头(前缀) → 共同前缀最长(≥5)。
    前3条都不中返回 (None,-1)，由调用方换搜索词或转人工。"""
    target_clean = target.replace('.pdf','').strip()
    st_clean = (search_term or '').replace('.pdf','').strip()
    top = hits[:3]  # 只在前3条内匹配

    for idx, h in enumerate(top, start=1):
        hc = h.replace('.pdf','').strip()
        if hc == target_clean or hc == st_clean:
            return h, idx
    for idx, h in enumerate(top, start=1):
        hc = h.replace('.pdf','').strip()
        if hc.startswith(target_clean) or hc.startswith(st_clean):
            return h, idx
    best, best_idx, best_len = None, -1, 0
    for idx, h in enumerate(top, start=1):
        hc = h.replace('.pdf','').strip()
        n = 0
        for a, b in zip(hc, target_clean):
            if a == b:
                n += 1
            else:
                break
        if n > best_len and n >= 5:
            best, best_idx, best_len = h, idx, n
    return (best, best_idx) if best else (None, -1)

def search_and_open(d, title):
    """搜索定位文件：按序用搜索词，结果里在前3条逐条匹配目标（不盲点第一条）"""
    d.click(890, 196); time.sleep(2)
    for _ in range(3):
        try: d.clear_text()
        except: break
        time.sleep(0.3)

    # 三级搜索词：完整标题 → 中文主干 → 尾部回退（去重）
    search_terms = [title.replace('.pdf','').strip()]
    head_term = head_search_term(title)
    if head_term: search_terms.append(head_term)
    tail_term = tail_search_term(title)
    if tail_term and tail_term not in search_terms: search_terms.append(tail_term)

    target = title.replace('.pdf','').strip()
    for st in search_terms:
        d.send_keys(st); time.sleep(3)
        time.sleep(1)
        xml = d.dump_hierarchy()
        if 'pdf' in xml.lower():
            root = etree.fromstring(xml.encode())
            hits = []
            for n in root.iter():
                t = (n.get('text','') or '').strip()
                if '.pdf' in t.lower() and len(t) > 15:
                    hits.append(t)
            chosen, pos = _match_target(hits, target, st)
            if chosen:
                print(f"[match] 词「{st[:30]}…」命中第 {pos} 条", end="")
                el = d(text=chosen)
                if el.exists(timeout=2):
                    el.click(); time.sleep(2)
                    return True
            else:
                print(f"[match] 词「{st[:30]}…」前3条未命中({len(hits)}条结果),换词", end="")
        # 本轮未命中或未搜到 → 清空
        for _ in range(3):
            try: d.clear_text()
            except: break
            time.sleep(0.3)
    return False

def back_to_list(d):
    for _ in range(8):
        xml = d.dump_hierarchy()
        if xml.lower().count('.pdf') > 3:
            return True
        b = d(description='Back')
        (b.exists(timeout=1) and b.click() or d.click(60, 60))
        time.sleep(1)
    return False

def download_one(d, title):
    """下载单篇：搜索定位 → 下载重试(最多3次) → 返回列表。成功返回 True。"""
    if not search_and_open(d, title):
        print(" ❌ 搜索不到")
        return False
    ok = False
    for retry in range(3):
        if download_file(d, title):
            ok = True
            break
        print(f" 重试{retry+1}", end="")
        time.sleep(3)
    return ok

def download_all(d, entries):
    """用搜索定位下载所有条目"""
    os.makedirs(INBOX, exist_ok=True)
    
    # 清理 Download
    subprocess.run([ADB, "shell", "rm", "-f", DLDIR + "*.pdf"], capture_output=True, timeout=10)
    
    downloaded = 0
    failed = []
    
    for i, entry in enumerate(entries):
        title = entry['title']
        label = entry['label']
        print(f"\n[{i+1}/{len(entries)}] [{label}] {title[:45]}", end="")
        
        if download_one(d, title):
            downloaded += 1
            print(f" ✅ ({downloaded})")
        else:
            failed.append(title)
            print(" ❌ 放弃")
        
        if not back_to_list(d):
            print("  ⚠️ 无法返回列表")
            break
    
    # 拉取
    r = subprocess.run([ADB, "shell", "ls", DLDIR], capture_output=True, text=True, timeout=10)
    pdfs = [f for f in r.stdout.strip().split('\n') if f.strip().endswith('.pdf')]
    if pdfs:
        print(f"\n📥 拉取 {len(pdfs)} 个 → {INBOX}/")
        for f in pdfs:
            loc = os.path.join(INBOX, f)
            if not os.path.exists(loc):
                subprocess.run([ADB, "pull", DLDIR + f, loc], capture_output=True, timeout=60)
        subprocess.run([ADB, "shell", "rm", "-f", DLDIR + "*.pdf"], capture_output=True, timeout=10)
    
    # 本轮新增失败 → 直接转人工清单（不再写 failed_list 等下轮自动重试）
    if failed:
        for t in failed:
            record_manual(t)
        save_failed([])
    else:
        # 本轮全成功，确保无残留失败
        save_failed([])

    return downloaded, failed

# ─── 补抓旧失败项 ───

MAX_RETRY_ROUNDS = 3  # 同一篇连续多轮仍失败则不再自动重试，留给人工

def load_failed():
    """读取 failed_list.json（过去累计的失败标题），不存在则空。"""
    try:
        if FAILED.exists():
            return json.load(open(FAILED))
    except Exception:
        return []
    return []

def save_failed(items):
    """写 failed_list.json。空列表时删除文件（避免留下空待办）。"""
    try:
        if not items:
            if FAILED.exists():
                FAILED.unlink()
            return
        json.dump(items, open(FAILED, "w"), ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_manual():
    """读取 needs_manual.json（已转人工的条目），不存在则空。"""
    try:
        if NEEDS_MANUAL.exists():
            return json.load(open(NEEDS_MANUAL, encoding="utf-8"))
    except Exception:
        pass
    return []

def save_manual(items):
    """写 needs_manual.json。空列表时删除文件。"""
    try:
        if not items:
            NEEDS_MANUAL.unlink(missing_ok=True)
            return
        json.dump(items, open(NEEDS_MANUAL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

def record_manual(title):
    """把一篇写入人工清单（去重）。返回是否新增。"""
    items = load_manual()
    for it in items:
        if it.get("title") == title:
            return False
    items.append({
        "title": title,
        "source": "ima_patrol",
        "action": "需人工下载",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_manual(items)
    return True

def retry_failed(d):
    """补抓旧失败项：成功即移除；仍失败/新失败 → 直接转人工（不再跨轮自动重试）。"""
    old = load_failed()
    if not old:
        return 0, [], []
    print(f"\n🔄 补抓 {len(old)} 篇历史失败项...")
    ok_list = []
    still = []      # 本轮仍失败 → 转人工
    handoff = []    # 本轮成功补抓里，其实不涉及转移；转人工的在 still 里处理
    for title in old:
        print(f"\n[补抓] {title[:45]}", end="")
        if download_one(d, title):
            ok_list.append(title)
            print(f" ✅")
        else:
            still.append(title)
            print(" -> 转人工")
        if not back_to_list(d):
            print("  ⚠️ 无法返回列表，中止补抓")
            rest = [t for t in old if t not in ok_list and t not in still]
            save_failed(rest)
            return len(ok_list), still, []
    # 移除成功项，留下的全部转人工；不再写 failed_list 等下轮
    save_failed([])
    for t in still:
        record_manual(t)
    return len(ok_list), still, []


# ─── 主流程 ───

def main():
    import argparse
    ap = argparse.ArgumentParser(description="IMA 巡查")
    ap.add_argument("--scan-only", action="store_true",
                    help="仅拉更新清单(scan_all→导出_scan json→关模拟器)，不下载。管线A用")
    args = ap.parse_args()
    scan_only = args.scan_only

    print(f"\n{'='*50}")
    print(f"IMA 巡查  {datetime.now().strftime('%Y-%m-%d %H:%M')}" + ("  [仅扫描/管线A]" if scan_only else ""))
    print(f"{'='*50}")
    
    # 1. 启动模拟器（start_emulator 内部已含一次失败重试；外层再补一次完整救援）
    emu_ok = start_emulator()
    if not emu_ok:
        print("⚠️ start_emulator 失败，执行完整救援（重启 adb + 清残留 + 重试）...")
        try:
            subprocess.run([ADB, "kill-server"], capture_output=True, timeout=10)
            subprocess.run([ADB, "start-server"], capture_output=True, timeout=15)
        except Exception:
            pass
        time.sleep(5)
        _clear_stale_locks()
        try:
            subprocess.run(["pkill", "-9", "-f", f"qemu-system.*{AVD_NAME}"], capture_output=True, timeout=5)
        except Exception:
            pass
        time.sleep(3)
        emu_ok = start_emulator()  # 再次尝试（内部还会清锁+重试）
    if not emu_ok:
        # 掉线防护：模拟器多次启动失败（可能被关机/进程残留），必须显式告警而非静默空转
        clicked = notify_urgent(
            "⚠️ IMA 模拟器启动失败",
            "IMA 模拟器多次启动失败，任务未执行。点击【现在重新登录】将尝试带窗口启动模拟器以便处理登录。",
            button="现在重新登录",
        )
        if clicked:
            try:
                subprocess.run(
                    ["bash", str(Path.home() / ".hermes/scripts/ima_relogin.sh")],
                    timeout=180,
                )
            except Exception:
                pass
        print("❌ 模拟器多次启动失败 → 任务未完成。查看 /tmp/ima_emulator.log（exit=2）")
        sys.exit(2)
    print("✅ 模拟器已就绪")
    
    try:
        d = navigate()
        if not d:
            # 掉线/登录失效防护（v1 修复：登录态失效导致 navigate 失败时，不能静默空转
            # exit=0 让 cron 误判正常——必须阻塞式提醒用户重登，并以退出码 2 让脚本层跳过 ingest）
            clicked = notify_urgent(
                "⚠️ IMA 掉线需重新登录",
                "IMA 访问失败（可能登录失效）。点击【现在重新登录】将自动打开模拟器登录界面，"
                "请完成微信/扫码登录。登录完成后，下次 cron（或手动 run_ima_scan.sh）自动恢复。",
                button="现在重新登录",
            )
            if clicked:
                # 用户点了「现在重新登录」→ 关掉 cron 的无头模拟器，改用带窗口的
                # ima_relogin.sh 重新拉起（用户才能看到登录界面扫码）。
                global KEEP_EMULATOR_BE
                KEEP_EMULATOR_BE = True
                try:
                    stop_emulator()
                except Exception:
                    pass
                try:
                    subprocess.run(
                        ["bash", str(Path.home() / ".hermes/scripts/ima_relogin.sh")],
                        timeout=180,
                    )
                except Exception:
                    pass
                print("✅ 已用带窗口模拟器打开 IMA 登录界面，请完成扫码登录（进程保持模拟器运行）")
            print("❌ 导航失败 → 模拟器/登录态异常，需人工处理（exit=2）")
            sys.exit(2)
        print("✅ 已进入医美文献")

        # 1.5 补抓历史失败项（在扫描前，随本轮一并处理；不重新扫描、不动锚点）
        #    —— 仅下载模式执行；scan-only 不补抓（无下载）
        retry_ok, retry_still, retry_handoff = (0, 0, []) if scan_only else retry_failed(d)

        # 2. 全屏扫描
        snap = load_snapshot()
        anchor_title = snap.get("anchor", "")
        entries, anchor = scan_all(d, hit_by_file=anchor_title if anchor_title else None)
        print(f"\n扫描到 {len(entries)} 篇新文件")
        print(f"锚点: {anchor[:50] if anchor else '?'}")
        
        if not entries:
            print(f"✅ 无新文件" + (f"（补抓成功 {retry_ok} 篇）" if retry_ok else ""))
            save_snapshot({"anchor": anchor or "", "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "new_count": 0})
            note = f"补抓成功 {retry_ok} 篇" if retry_ok else "无新增"
            if retry_still:
                note += f"，仍有 {len(retry_still)} 篇补不上（已转人工）"
            level = "error" if (retry_still and not scan_only) else "info"
            notify("IMA 巡查", f"医美文献无新更新\n{note}", result=note, level=level)
            return
        
        # 3. 按日期分组输出
        groups = {}
        for e in entries:
            tl = e['label'] or '?'
            groups.setdefault(tl, []).append(e['title'])
        
        print("\n📊 新文件分布:")
        for k, v in sorted(groups.items()):
            print(f"  [{k}]: {len(v)} 篇")
        
        # 4. 产出扫描统计文档（下载之前）
        scan_time = datetime.now().strftime("%H%M")
        scan_report = {
            "scan_time": scan_time,
            "total_scan": len(entries),
            "entries": entries,
            "anchor": anchor or "",
        }
        os.makedirs(INBOX, exist_ok=True)
        json.dump(scan_report, open(os.path.join(INBOX, f"_scan_{scan_time}.json"), "w"), ensure_ascii=False, indent=2)
        print(f"\n📋 统计文档: {BATCH_DATE}/_scan_{scan_time}.json")

        # 4.5 仅扫描模式（管线A）：导出清单后立即结束，不下载、不写下载报告
        #     —— 下载逻辑(5~8)保留完整，下次接下载时参考，勿删。
        if scan_only:
            if anchor:
                save_snapshot({"anchor": anchor, "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "new_count": len(entries)})
                print(f"⚓ 锚点: {anchor[:50]}")
            detail = ", ".join(f"{k}{len(v)}篇" for k, v in sorted(groups.items()))
            print(f"\n✅ [仅扫描] 完成: 清单 {len(entries)} 篇已导出 → {BATCH_DATE}/_scan_{scan_time}.json")
            notify("IMA 巡查", f"IMA 更新清单 {len(entries)} 篇（管线A已导出，未下载）\n{detail}",
                   result=f"{len(entries)}篇清单", level="info")
            return

        # 5. 下载
        dl_count, failed_list = download_all(d, entries)
        
        # 6. 下载报告（补抓结果单独标注，不并入新下载统计）
        report = {
            "batch": BATCH_DATE,
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_scan": len(entries),
            "downloaded": dl_count,
            "failed": len(failed_list),
            "failed_list": failed_list,
            # 补抓（历史失败项）单独统计
            "retry_downloaded": retry_ok,
            "retry_still_failed": retry_still,
            "anchor": anchor or "",
            "by_date": {k: len(v) for k, v in groups.items()},
        }
        json.dump(report, open(os.path.join(INBOX, "_download_report.json"), "w"), ensure_ascii=False, indent=2)
        
        # 7. 保存锚点
        if anchor:
            save_snapshot({"anchor": anchor, "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "new_count": len(entries)})
            print(f"\n⚓ 锚点: {anchor[:50]}")
        
        retry_note = f"，补抓成功 {retry_ok} 篇" if retry_ok else ""
        print(f"\n✅ 完成: 下载 {dl_count}/{len(entries)}, 失败 {len(failed_list)}{retry_note}")
        
        # 通知（补抓单独一行标注）
        detail = ", ".join(f"{k}{len(v)}篇" for k, v in sorted(groups.items()))
        lines = [f"IMA 巡查：医美文献更新 {len(entries)} 篇", f"下载 {dl_count} 篇", detail]
        if retry_ok:
            lines.append(f"补抓成功 {retry_ok} 篇")
        if retry_still:
            lines.append(f"❗仍有 {len(retry_still)} 篇补不上（已转人工）")
        lines.append(f"→ {BATCH_DATE}/")
        msg = "\n".join(lines)
        result_parts = [f"{dl_count}/{len(entries)}篇, 失败{len(failed_list)}"]
        if retry_ok:
            result_parts.append(f"补抓{retry_ok}")
        if retry_still:
            result_parts.append(f"补不上{len(retry_still)}")
        notify("IMA 巡查", msg, result=", ".join(result_parts),
               level="error" if (failed_list or retry_still) else "info")
        print(msg)

        # 8. fail 条目 → 转人工清单（含元信息，供通知中心任务清单对照）
        manual = load_manual()
        if manual:
            for it in manual:
                item_msg = f"[人工下载] {it['title']}\n来源: {it.get('source','ima_patrol')} | 操作: {it.get('action','')} | 加入: {it.get('added_at','')}"
                notify("IMA 人工下载", item_msg, level="error", result=it['title'])

    finally:
        # 掉线重登：用户点「现在重新登录」后已改拉起带窗口模拟器供扫码，
        # 此时不能关模拟器，否则登录界面消失。跳过 stop 保持供用户扫码。
        if not KEEP_EMULATOR_BE:
            stop_emulator()

if __name__ == "__main__":
    main()
