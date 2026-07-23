#!/usr/bin/env python3
"""freshrss_bridge — 增量泵 FreshRSS entry → aes_workflow.db

用法:
  python3 -m aes_workflow.freshrss_bridge            # 全量一次（首次）
  python3 -m aes_workflow.freshrss_bridge --watch     # 持续轮询（增量）
  python3 -m aes_workflow.freshrss_bridge --dry-run   # 预览不写库
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

from aes_workflow.db import db_session, lookup_article_key, register_identifiers, log_ingest, utc_now
from aes_workflow.ingest_ids import (
    article_key_from_identifiers,
    extract_ids_from_item,
    extract_doi_from_text,
    normalize_doi,
    primary_id_for_log,
)

# ── 路径 ───────────────────────────────────────────────
FRESHRSS_DB = Path("/Users/meiyiwangluokeji/coding/freshrss/data/users/alnews/db.sqlite")
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "freshrss_bridge_state.json"
POLL_INTERVAL = 60  # 秒
BATCH_SIZE = 500

# ── 平台映射 ──────────────────────────────────────────
# 从 feed URL 判定平台
PLATFORM_RULES = [
    ("aes-feeds/main/ktn_", "ktn"),
    ("aes-feeds/main/cnki_", "cnki"),
    ("aes-feeds/main/cma_", "cma"),
    ("aes-feeds/main/prs_", "lww"),
    ("aes-feeds/main/aswc_", "lww"),
    ("aes-feeds/main/annals_", "lww"),
    ("aes-feeds/main/derm_", "lww"),
    ("aes-feeds/main/j_craniofacial", "lww"),
    ("aes-feeds/main/", "lww"),  # 其余 aes-feeds 默认 LWW
    ("pubmed.ncbi.nlm.nih.gov", "pubmed"),
    ("sciencedirect.com", "sciencedirect"),
    ("wechat-rss", "wechat"),
    ("ktn", "ktn"),
]

# 部分源有明确的 language 属性
LANG_BY_FEED_NAME_PREFIX = {
    "cnki": "zh",
    "cma": "zh",
    "中国": "zh",
    "中华": "zh",
}

# 清扫 title 中的 HTML 实体
TITLE_CLEAN = re.compile(r"&amp;|&lt;|&gt;|&quot;|&#\d+;")

# ────────────────────────────────────────────────────────


def load_state() -> dict:
    import json
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_seen_id": 0, "total_imported": 0, "last_run": None}


def save_state(state: dict) -> None:
    import json
    state["last_run"] = utc_now()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def detect_platform(feed_name: str, feed_url: str) -> str:
    url_lower = feed_url.lower()
    for pattern, platform in PLATFORM_RULES:
        if pattern in url_lower:
            return platform
    name_lower = feed_name.lower()
    if "cnki" in name_lower:
        return "cnki"
    if "pubmed" in url_lower:
        return "pubmed"
    return "other"


def detect_lang(platform: str, feed_name: str) -> str:
    if platform in ("cnki", "cma"):
        return "zh"
    for prefix, lang in LANG_BY_FEED_NAME_PREFIX.items():
        if feed_name.startswith(prefix):
            return lang
    return "en"


def clean_title(raw: str) -> str:
    return TITLE_CLEAN.sub("", raw).strip()


def bridge_once(*, dry_run: bool = False) -> dict:
    """全量/增量导入一次。返回统计。"""
    state = load_state()
    last_id = state["last_seen_id"]
    stats = {"read": 0, "inserted": 0, "duplicate": 0, "skipped_no_id": 0, "errors": 0}

    # 读 FreshRSS
    fr = sqlite3.connect(str(FRESHRSS_DB))
    fr.row_factory = sqlite3.Row
    fr.execute("PRAGMA busy_timeout = 5000")

    rows = fr.execute(
        """SELECT e.id, e.guid, e.title, e.author, e.content, e.link, e.date,
                  e.lastSeen, e.id_feed, f.name AS feed_name, f.url AS feed_url
           FROM entry e
           JOIN feed f ON f.id = e.id_feed
           WHERE e.id > ?
           ORDER BY e.id ASC
           LIMIT ?""",
        (last_id, BATCH_SIZE),
    ).fetchall()

    stats["read"] = len(rows)
    if not rows:
        fr.close()
        return stats

    # 找出这批最大 id（用于最后更新 state）
    max_id = max(r["id"] for r in rows)

    with db_session() as conn:
        for row in rows:
            try:
                feed_name = row["feed_name"] or ""
                feed_url = row["feed_url"] or ""
                platform = detect_platform(feed_name, feed_url)
                lang = detect_lang(platform, feed_name)
                title = clean_title(row["title"] or "")
                link = row["link"] or ""
                guid = row["guid"] or ""
                author = (row["author"] or "").strip()
                content = (row["content"] or "")[:2000]
                pub_ts = row["date"]
                pub_date = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if pub_ts else ""

                if not title or not link:
                    stats["skipped_no_id"] += 1
                    continue

                # ── 标识符提取（两次：先浅层后深层） ──
                identifiers = extract_ids_from_item(link=link, guid=guid, title=title)

                # 从正文补充 DOI
                if not identifiers.get("doi"):
                    doi = extract_doi_from_text(content[:2000])
                    if doi:
                        identifiers["doi"] = normalize_doi(doi)

                # 微信公众号：额外扫描 content 全文找 DOI
                wechat_source = None
                if platform == "wechat":
                    content_text = (row["content"] or "")[:5000]
                    deep_doi = extract_doi_from_text(content_text)
                    if deep_doi and not identifiers.get("doi"):
                        deep_doi = normalize_doi(deep_doi)
                        identifiers["doi"] = deep_doi

                    # 记录发现来源（无论是否找到 DOI）
                    wechat_source = json.dumps([{
                        "title": title,
                        "url": link,
                        "feed_name": feed_name,
                        "feed_id": row["id_feed"],
                        "discovered_at": utc_now(),
                    }], ensure_ascii=False)

                # 确定 discovery_type
                if platform == "wechat":
                    has_id = bool(identifiers.get("doi") or identifiers.get("pmid") or identifiers.get("pii"))
                    discovery_type = "wechat_discovery" if has_id else "wechat_news"
                else:
                    discovery_type = "rss_feed"

                # 没有标准标识符则用 platform_id 兜底
                if not identifiers:
                    fallback_key = f"fr:{row['id_feed']}:{guid or link}"
                    import hashlib
                    identifiers["platform_id"] = hashlib.sha256(fallback_key.encode()).hexdigest()[:32]

                # 计算 article_key
                article_key = article_key_from_identifiers(identifiers)
                if not article_key:
                    stats["skipped_no_id"] += 1
                    continue

                # 去重
                existing = lookup_article_key(conn, identifiers)
                if existing:
                    stats["duplicate"] += 1
                    log_ingest(conn, ingest_source="freshrss_bridge", feed_file=feed_name,
                               id_type="", id_value="", article_key=existing, duplicate=True)
                    continue

                if dry_run:
                    stats["inserted"] += 1
                    continue

                # INSERT（含新字段）
                now = utc_now()
                conn.execute(
                    """INSERT INTO entries (
                        article_key, feed_id, ingest_source, lang, title, journal, authors,
                        abstract, doi, pmid, pmcid, pii, platform, platform_id,
                        source_url, publisher_url, pub_date, meta_status,
                        discovery_type, wechat_discovery_sources,
                        ingest_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        article_key, str(row["id_feed"]), "freshrss_bridge", lang, title,
                        feed_name, author, "",
                        identifiers.get("doi", ""), identifiers.get("pmid", ""),
                        identifiers.get("pmcid", ""), identifiers.get("pii", ""),
                        platform, identifiers.get("platform_id", ""),
                        link, link, pub_date, "meta_pending",
                        discovery_type, wechat_source,
                        now, now,
                    ),
                )
                register_identifiers(conn, article_key, identifiers)
                id_type, id_value = primary_id_for_log(identifiers)
                log_ingest(conn, ingest_source="freshrss_bridge", feed_file=feed_name,
                           id_type=id_type, id_value=id_value, article_key=article_key, duplicate=False)
                stats["inserted"] += 1

            except Exception as e:
                stats["errors"] += 1
                import traceback
                traceback.print_exc()

    fr.close()

    # 更新 state
    state["last_seen_id"] = max_id
    state["total_imported"] = state.get("total_imported", 0) + stats["inserted"]
    if not dry_run:
        save_state(state)

    return stats


def bridge_watch() -> None:
    """持续轮询模式。"""
    print(f"[bridge] 启动轮询模式，每 {POLL_INTERVAL}s 一次")
    while True:
        try:
            stats = bridge_once()
            if stats["read"] > 0 or stats["inserted"] > 0:
                print(f"[bridge] {stats}")
            elif stats.get("errors", 0) > 0:
                print(f"[bridge] ⚠️ {stats}")
        except Exception as e:
            print(f"[bridge] ❌ {e}")
        time.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRSS → aes_workflow.db 桥接层")
    parser.add_argument("--watch", action="store_true", help="持续轮询模式")
    parser.add_argument("--dry-run", action="store_true", help="预览不写库")
    parser.add_argument("--reset", action="store_true", help="重置 state（从头全量）")
    args = parser.parse_args()

    if args.reset:
        STATE_FILE.unlink(missing_ok=True)
        print("[bridge] state 已重置，下次运行从头全量导入")

    if args.watch:
        # 先跑一次全量
        print("[bridge] 首次全量...")
        stats = bridge_once(dry_run=args.dry_run)
        print(f"[bridge] {stats}")
        bridge_watch()
    else:
        stats = bridge_once(dry_run=args.dry_run)
        print(f"[bridge] {stats}")


if __name__ == "__main__":
    main()
