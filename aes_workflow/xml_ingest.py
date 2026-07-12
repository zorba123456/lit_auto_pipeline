#!/usr/bin/env python3
"""Ingest aes-feeds XML items into entries (Top3 #1)."""

from __future__ import annotations

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from aes_workflow.db import db_session, init_db, log_ingest, lookup_article_key, register_identifiers, utc_now
from aes_workflow.ingest_ids import (
    article_key_from_identifiers,
    extract_doi_from_text,
    extract_ids_from_item,
    merge_identifiers,
    normalize_doi,
    primary_id_for_log,
)

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "aes-feeds"

KTN_NOISE_TITLE = re.compile(r"^\[[^\]]+\]$")
SCHOLAR_HOST = re.compile(r"scholar\.google", re.I)
DOI_IN_CITATION = re.compile(r"doi:\s*(10\.\S+)", re.I)
ISSUE_AOP = re.compile(r"Ahead of Print", re.I)
ISSUE_ZH = re.compile(r"<b>所属期数：</b>\s*([^<]+)", re.I)
PUB_ZH = re.compile(r"<b>出版时间：</b>\s*([^<]+)", re.I)


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return html.unescape(el.text.strip())


def _child_text(item: ET.Element, tag: str) -> str:
    for child in item:
        if child.tag.split("}")[-1] == tag:
            return _text(child)
    return ""


def detect_platform(feed_path: Path, channel_title: str) -> str:
    name = feed_path.name.lower()
    if name.startswith("ktn_"):
        return "ktn"
    if name.startswith("cnki_"):
        return "cnki"
    if name.startswith("cma_"):
        return "cma"
    if any(
        name.startswith(p)
        for p in (
            "prs_",
            "aswc_",
            "annals_",
            "derm_",
            "j_craniofacial",
        )
    ):
        return "lww"
    title_l = channel_title.lower()
    if "cnki" in title_l:
        return "cnki"
    if "ktn" in title_l or "google scholar" in title_l:
        return "ktn"
    return "unknown"


def should_skip_item(platform: str, title: str, link: str) -> bool:
    if not title or not link:
        return True
    if SCHOLAR_HOST.search(link):
        return True
    if platform == "ktn" and KTN_NOISE_TITLE.match(title.strip()):
        return True
    return False


def parse_lww_issue(description: str, citation: str) -> tuple[str, str]:
    issue = ""
    pub = ""
    if description:
        m = ISSUE_ZH.search(description)
        if m:
            issue = m.group(1).strip()
        m2 = PUB_ZH.search(description)
        if m2:
            pub = m2.group(1).strip()
    if not issue and citation:
        if ISSUE_AOP.search(citation):
            issue = "Ahead of Print"
    return issue, pub


def parse_item(
    item: ET.Element,
    *,
    platform: str,
    feed_id: str,
    journal: str,
) -> dict | None:
    title = _child_text(item, "title")
    link = _child_text(item, "link")
    guid = _child_text(item, "guid")
    description = _child_text(item, "description")
    authors = _child_text(item, "author")
    pub_date = _child_text(item, "pubDate")
    citation = _child_text(item, "citation")

    if should_skip_item(platform, title, link):
        return None

    identifiers = extract_ids_from_item(link=link, guid=guid, citation=citation, title=title)
    if platform == "lww" and guid and "platform_id" not in identifiers:
        identifiers["platform_id"] = guid

    if not identifiers:
        return None

    issue, issue_pub = parse_lww_issue(description, citation)
    if issue_pub and not pub_date:
        pub_date = issue_pub

    abstract = ""
    if description and "No abstract available" not in description:
        abstract = re.sub(r"<[^>]+>", " ", description)
        abstract = html.unescape(re.sub(r"\s+", " ", abstract)).strip()[:4000]

    doi = identifiers.get("doi") or extract_doi_from_text(citation)
    if doi:
        doi = normalize_doi(doi)
        identifiers["doi"] = doi

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "journal": journal,
        "issue": issue,
        "pub_date": pub_date,
        "doi": doi,
        "pmid": identifiers.get("pmid"),
        "pmcid": identifiers.get("pmcid"),
        "pii": identifiers.get("pii"),
        "platform": platform,
        "platform_id": identifiers.get("platform_id"),
        "source_url": link,
        "publisher_url": link,
        "feed_id": feed_id,
        "identifiers": identifiers,
        "lang": "zh" if platform in ("cnki", "cma") else "en",
    }


def insert_entry(conn, row: dict, *, ingest_source: str) -> str:
    now = utc_now()
    article_key = article_key_from_identifiers(row["identifiers"])
    if not article_key:
        raise ValueError("missing canonical id")

    conn.execute(
        """
        INSERT INTO entries (
          article_key, feed_id, ingest_source, lang, title, journal, authors, abstract,
          doi, pmid, pmcid, pii, platform, platform_id, source_url, publisher_url,
          issue, pub_date, meta_status, ingest_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article_key,
            row["feed_id"],
            ingest_source,
            row["lang"],
            row["title"],
            row["journal"],
            row["authors"],
            row["abstract"],
            row["doi"],
            row["pmid"],
            row["pmcid"],
            row["pii"],
            row["platform"],
            row["platform_id"],
            row["source_url"],
            row["publisher_url"],
            row["issue"],
            row["pub_date"],
            "meta_partial" if row["platform"] in ("ktn", "lww") and not row["abstract"] else "meta_complete",
            now,
            now,
        ),
    )
    register_identifiers(conn, article_key, row["identifiers"])
    return article_key


def merge_entry(conn, article_key: str, row: dict) -> None:
    now = utc_now()
    conn.execute(
        """
        UPDATE entries SET
          abstract = COALESCE(NULLIF(abstract, ''), ?),
          authors = COALESCE(NULLIF(authors, ''), ?),
          issue = COALESCE(NULLIF(issue, ''), ?),
          pub_date = COALESCE(NULLIF(pub_date, ''), ?),
          updated_at = ?
        WHERE article_key = ?
        """,
        (row["abstract"], row["authors"], row["issue"], row["pub_date"], now, article_key),
    )
    register_identifiers(conn, article_key, row["identifiers"])


def load_feed_tree(feed_path: Path) -> ET.ElementTree:
    raw = feed_path.read_text(encoding="utf-8", errors="replace")
    # KTN items often have bare & in scholar.google URLs
    raw = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\w+;)", "&amp;", raw)
    return ET.ElementTree(ET.fromstring(raw))


def ingest_feed(
    feed_path: Path,
    *,
    db_path: Path | str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    tree = load_feed_tree(feed_path)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise ValueError(f"no channel in {feed_path}")

    channel_title = _child_text(channel, "title")
    platform = detect_platform(feed_path, channel_title)
    feed_id = feed_path.stem
    ingest_source = f"xml_{platform}"
    journal = channel_title.replace(" - CNKI Feeds", "").strip()

    stats = {"inserted": 0, "duplicate": 0, "skipped": 0, "errors": 0}

    items = channel.findall("item")
    if limit:
        items = items[:limit]

    with db_session(db_path) as conn:
        for item in items:
            try:
                row = parse_item(item, platform=platform, feed_id=feed_id, journal=journal)
                if not row:
                    stats["skipped"] += 1
                    continue

                existing = lookup_article_key(conn, row["identifiers"])
                id_type, id_value = primary_id_for_log(row["identifiers"])

                if existing:
                    if not dry_run:
                        merge_entry(conn, existing, row)
                        log_ingest(
                            conn,
                            ingest_source=ingest_source,
                            feed_file=feed_path.name,
                            id_type=id_type,
                            id_value=id_value,
                            article_key=existing,
                            duplicate=True,
                        )
                    stats["duplicate"] += 1
                    continue

                if dry_run:
                    stats["inserted"] += 1
                    continue

                article_key = insert_entry(conn, row, ingest_source=ingest_source)
                log_ingest(
                    conn,
                    ingest_source=ingest_source,
                    feed_file=feed_path.name,
                    id_type=id_type,
                    id_value=id_value,
                    article_key=article_key,
                    duplicate=False,
                )
                stats["inserted"] += 1
            except Exception:
                stats["errors"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest RSS/XML into aes_workflow.db")
    parser.add_argument("--feed", action="append", help="XML path (repeatable)")
    parser.add_argument("--glob", default="", help="Under aes-feeds/, e.g. ktn_*.xml")
    parser.add_argument("--db", default=str(ROOT / "data" / "aes_workflow.db"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--init-db", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.init_db:
        init_db(args.db)

    feeds: list[Path] = []
    if args.feed:
        feeds.extend(Path(p).expanduser().resolve() for p in args.feed)
    if args.glob:
        feeds.extend(sorted(FEEDS.glob(args.glob)))
    if not feeds:
        parser.error("specify --feed or --glob")

    limit = args.limit or None
    total = {"inserted": 0, "duplicate": 0, "skipped": 0, "errors": 0}

    for feed in feeds:
        if not feed.is_file():
            print(f"⚠️ skip missing {feed}", file=sys.stderr)
            continue
        stats = ingest_feed(feed, db_path=args.db, limit=limit, dry_run=args.dry_run)
        print(f"{feed.name}: {stats}")
        for k in total:
            total[k] += stats[k]

    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()
