#!/usr/bin/env python3
"""全量扫描过去一周微信文章，统计哪些号有 DOI。"""
import sqlite3, json, re, time, html as html_lib, urllib.request, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "aes_workflow.db"

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT article_key, journal, source_url, pub_date
    FROM entries
    WHERE discovery_type='wechat_news'
      AND source_url LIKE '%mp.weixin.qq.com%'
      AND pub_date >= datetime('now', '-7 days')
      AND journal != '0-医美器械新规新批播报群2'
    ORDER BY journal, pub_date
""").fetchall()
conn.close()

print(f"总计 {len(rows)} 条，来自 {len(set(r['journal'] for r in rows))} 个号")
sys.stdout.flush()

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36 "
      "MicroMessenger/6.8.0 MiniProgramEnv/Mac MacWechat/WMPF XWEB/1191")

results = {}
fetched = failed = 0

for i, r in enumerate(rows):
    journal = r["journal"] or "未知"
    if journal not in results:
        results[journal] = {"total": 0, "found": 0, "dois": []}
    results[journal]["total"] += 1

    if i > 0 and i % 50 == 0:
        print(f"  进度: {i}/{len(rows)}...")
        sys.stdout.flush()

    try:
        url = r["source_url"].split("#")[0]
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": "https://mp.weixin.qq.com/",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")

        m = re.search(r'<div[^>]+id="js_content"[^>]*>(.*?)</div>', body, re.S | re.I)
        text = ""
        if m:
            chunk = m.group(1)
            chunk = re.sub(r"<script[\s\S]*?</script>", " ", chunk, flags=re.I)
            chunk = re.sub(r"<[^>]+>", " ", chunk)
            text = html_lib.unescape(chunk)
            text = re.sub(r"\s+", " ", text).strip()

        if text and len(text) > 100:
            dois = set(re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text))
            if dois:
                results[journal]["found"] += 1
                results[journal]["dois"].extend(list(dois)[:3])
        fetched += 1
    except Exception:
        failed += 1

    time.sleep(0.3)

# 输出
print(f"\n完成: fetched={fetched}, failed={failed}")
print()
print(f"{'公众号':28s} {'总量':>5s} {'命中':>5s} {'命中率':>7s} {'样例DOI'}")
print("-" * 80)

hit_accounts = [(j, s) for j, s in results.items() if s["found"] > 0]
hit_accounts.sort(key=lambda x: -x[1]["found"])
for j, s in hit_accounts:
    rate = s["found"] / s["total"] * 100
    sample = s["dois"][0][:35] if s["dois"] else ""
    print(f'{j[:26]:28s} {s["total"]:5d} {s["found"]:5d} {rate:6.1f}% {sample}')

print()
zero_accounts = [(j, s) for j, s in results.items() if s["found"] == 0]
print(f"零命中的号: {len(zero_accounts)} 个")
for j, s in sorted(zero_accounts, key=lambda x: -x[1]["total"])[:15]:
    print(f'  {j[:26]:28s} {s["total"]:5d} 条')

# 存结果
out = ROOT / "data" / "wechat_doi_scan_result.json"
out.write_text(json.dumps({
    "total": len(rows),
    "fetched": fetched,
    "failed": failed,
    "hit_accounts": {j: {"total": s["total"], "found": s["found"], "sample_dois": s["dois"][:5]} for j, s in hit_accounts},
    "zero_accounts": {j: s["total"] for j, s in zero_accounts},
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n结果已保存: {out}")
