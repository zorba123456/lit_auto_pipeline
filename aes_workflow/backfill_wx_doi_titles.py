"""微信 DOI 条目标题离线回填（v2.54）。

用途：wx_doi_entry 条目里标题仍是推文标题（journal 为空）的行，
按 Crossref → yiigle(CMA) → chndoi/万方(cn_doi_meta) 逐级反查真实文献标题回填。

设计为**离线批处理**，不进实时扫描链路：
- chndoi 是纯 curl（快），万方路线走 headless chromium（~6s/条）；
- 幂等：只处理 journal 为空的行，已修复的自动跳过，重复跑无副作用；
- 全量跑一次 ~3 分钟（视 MISS 量）。DB 被 rss_aggregator/server 占用时自动等待重试。

用法：
    ./venv/bin/python3 -m aes_workflow.backfill_wx_doi_titles           # 全量
    ./venv/bin/python3 -m aes_workflow.backfill_wx_doi_titles --dry     # 只看会改什么
"""

import sys
import time

from .db import db_session
from .cn_doi_meta import cn_doi_search
from .wechat_prefilter import yiigle_doi_search


def backfill(*, dry: bool = False) -> tuple[int, int]:
    """返回 (fixed, miss)。"""
    with db_session() as conn:
        rows = conn.execute(
            """SELECT article_key, doi, title FROM entries
               WHERE discovery_type='wx_doi_entry' AND (journal='' OR journal IS NULL)"""
        ).fetchall()
    print(f"candidates: {len(rows)}", flush=True)
    fixed = miss = 0
    for row in rows:
        doi = (row["doi"] or "").strip().strip("。）(;,，")
        title = row["title"] or ""
        # 目次页标题本来就是「目次」，反查无意义；残缺 DOI（含空格）跳过
        if not doi or " " in doi or "目次" in title:
            miss += 1
            continue
        meta = None
        if doi.startswith("10.3760"):
            try:
                cma = yiigle_doi_search(doi)
                if cma and cma.get("title"):
                    meta = {"title": cma["title"], "publisher": cma.get("journal", "")}
            except Exception:
                pass
        if not meta:
            try:
                meta = cn_doi_search(doi)
            except Exception:
                meta = None
        if not (meta and meta.get("title") and meta["title"] != title):
            miss += 1
            continue
        if dry:
            print(f"DRY {doi} -> {meta['title'][:45]} | {meta.get('publisher', '') or meta.get('source', '')}", flush=True)
            fixed += 1
            continue
        for _ in range(10):  # DB 可能被 aggregator/server 占用，等待重试
            try:
                with db_session() as conn:
                    conn.execute("PRAGMA busy_timeout=20000")
                    conn.execute(
                        """UPDATE entries SET title=?,
                           journal=CASE WHEN journal='' OR journal IS NULL THEN ? ELSE journal END
                           WHERE article_key=? AND (journal='' OR journal IS NULL)""",
                        (meta["title"], meta.get("publisher", "") or meta.get("journal", ""), row["article_key"]),
                    )
                fixed += 1
                print(f"FIX {doi} -> {meta['title'][:45]} | {meta.get('publisher', '') or meta.get('source', '')}", flush=True)
                break
            except Exception:
                time.sleep(12)
        else:
            print(f"LOCKED-OUT {doi}", flush=True)
            miss += 1
    return fixed, miss


def main() -> None:
    dry = "--dry" in sys.argv
    fixed, miss = backfill(dry=dry)
    print(f"fixed={fixed} miss={miss}", flush=True)


if __name__ == "__main__":
    main()
