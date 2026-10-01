#!/usr/bin/env python3
"""v2.86 一次性回填：wx_doi_entry 中文 DOI 元数据（EBSCO + 引文页链）。

用法：python3 backfill_wxdoi_v286.py [--dry]
搜索候选 URL 由会话侧 web_search 生成，存 /tmp/cit_urls.json。
"""
import json
import sqlite3
import sys

sys.path.insert(0, "/Users/meiyiwangluokeji/coding/lit_auto_pipeline")
from aes_workflow.cn_doi_meta import cn_doi_search, citation_page_search

DB = "/Users/meiyiwangluokeji/coding/lit_auto_pipeline/data/aes_workflow.db"
BAD_TITLES = ("万方数据知识服务平台", "人机校验", "万方医学网")


def main(dry: bool):
    cit_urls = {}
    try:
        cit_urls = json.load(open("/tmp/cit_urls.json"))
    except Exception:
        pass
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT article_key, doi, title, journal, authors, pub_date
           FROM entries WHERE discovery_type='wx_doi_entry'
             AND (doi LIKE '10.3969%' OR title LIKE '%万方%')
           ORDER BY ingest_at DESC"""
    ).fetchall()
    print(f"{len(rows)} rows")
    fixed = miss = 0
    for r in rows:
        doi = (r["doi"] or "").strip()
        cur_title = r["title"] or ""
        # 已是像样文献标题（非推文/非壳页）且期刊已有 → 跳过
        if doi and not any(b in cur_title for b in BAD_TITLES) and r["journal"]:
            continue
        meta = cn_doi_search(doi) if doi else None
        if not meta:
            meta = citation_page_search(cit_urls.get(doi, []), doi)
        if not meta or not meta.get("title"):
            print(f"MISS {doi} | {cur_title[:30]}")
            miss += 1
            continue
        new_title = meta["title"].strip()
        if new_title == cur_title:
            continue
        print(f"FIX  {doi}\n     {cur_title[:40]}\n  -> {new_title} | {meta.get('journal','')} | {meta.get('pub_date','')} [{meta.get('source')}]")
        if not dry:
            conn.execute(
                """UPDATE entries SET title=?, journal=CASE WHEN journal='' OR journal IS NULL THEN ? ELSE journal END,
                       authors=CASE WHEN authors='' OR authors IS NULL THEN ? ELSE authors END,
                       pub_date=CASE WHEN pub_date='' OR pub_date IS NULL THEN ? ELSE pub_date END,
                       updated_at=datetime('now')
                   WHERE article_key=?""",
                (new_title, meta.get("journal", ""), meta.get("authors", ""),
                 meta.get("pub_date", ""), r["article_key"]),
            )
        fixed += 1
    if not dry:
        conn.commit()
    conn.close()
    print(f"\nfixed={fixed} miss={miss} dry={dry}")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
