#!/usr/bin/env python3
"""Match pdf_inbox PDFs to entries and promote to data/pdf/{article_key}.pdf."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from aes_workflow.blind_pdf_ingest import try_ingest_blind_pdf
from aes_workflow.db import db_session, lookup_article_key, migrate_schema, utc_now
from aes_workflow.paths import PDF_UNMATCHED, ROOT
from aes_workflow.pdf_extract import article_key_from_filename, extract_ids_from_pdf, is_incomplete_download
from aes_workflow.pdf_store import LocalPdfStore


def entry_exists(conn, article_key: str) -> bool:
    row = conn.execute("SELECT 1 FROM entries WHERE article_key = ?", (article_key,)).fetchone()
    return row is not None


def update_entry_fulltext(conn, article_key: str, pdf_rel_path: str) -> None:
    conn.execute(
        """
        UPDATE entries
        SET fulltext_status = 'PDF_HAS_FILE', pdf_path = ?, updated_at = ?
        WHERE article_key = ?
        """,
        (pdf_rel_path, utc_now(), article_key),
    )


def resolve_article_key(conn, path: Path) -> tuple[str | None, dict[str, str], str]:
    """Return (article_key, identifiers_used, match_method)."""
    key = article_key_from_filename(path)
    if key and entry_exists(conn, key):
        return key, {"article_key": key}, "filename"

    ids = extract_ids_from_pdf(path)
    if ids:
        found = lookup_article_key(conn, ids)
        if found:
            method = "doi" if ids.get("doi") else next(iter(ids))
            return found, ids, method

    return None, ids, "none"


def quarantine_unmatched(path: Path, unmatched_dir: Path) -> Path:
    unmatched_dir.mkdir(parents=True, exist_ok=True)
    dest = unmatched_dir / path.name
    if dest.exists():
        dest.unlink()
    shutil.move(str(path), str(dest))
    return dest


def process_inbox_once(
    *,
    store: LocalPdfStore,
    db_path: Path | str | None = None,
    quarantine: bool = True,
    unmatched_dir: Path | None = None,
    blind_ingest: bool = True,
) -> dict[str, int]:
    store.ensure_dirs()
    unmatched_dir = unmatched_dir or PDF_UNMATCHED
    stats = {"matched": 0, "ingested": 0, "unmatched": 0, "skipped": 0, "errors": 0}

    pdfs = sorted(p for p in store.inbox.glob("*.pdf") if p.is_file())
    if not pdfs:
        return stats

    with db_session(db_path) as conn:
        migrate_schema(conn)
        for path in pdfs:
            try:
                if is_incomplete_download(path):
                    stats["skipped"] += 1
                    continue

                article_key, ids, method = resolve_article_key(conn, path)
                if not article_key and blind_ingest and ids:
                    article_key, ids, blind_reason = try_ingest_blind_pdf(conn, path)
                    if article_key and blind_reason == "ingested":
                        method = "blind_ingest"
                    elif article_key and blind_reason == "exists":
                        method = "doi" if ids.get("doi") else next(iter(ids), "id")

                if not article_key:
                    stats["unmatched"] += 1
                    if quarantine:
                        dest = quarantine_unmatched(path, unmatched_dir)
                        print(f"unmatched → {dest.name} (ids={ids or 'none'})", file=sys.stderr)
                    else:
                        print(f"unmatched: {path.name} (ids={ids or 'none'})", file=sys.stderr)
                    continue

                dest = store.commit(path, article_key)
                rel = store.rel_path(article_key)
                update_entry_fulltext(conn, article_key, rel)
                if method == "blind_ingest":
                    stats["ingested"] += 1
                    print(
                        f"ingested [blind] {article_key[:12]}… "
                        f"doi={ids.get('doi', '-')} → {rel} ({dest.stat().st_size} bytes)"
                    )
                else:
                    stats["matched"] += 1
                    print(f"matched [{method}] {article_key[:12]}… → {rel} ({dest.stat().st_size} bytes)")
            except Exception as exc:
                stats["errors"] += 1
                print(f"error {path.name}: {exc}", file=sys.stderr)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote pdf_inbox files into data/pdf/")
    parser.add_argument("--db", default=str(ROOT / "data" / "aes_workflow.db"))
    parser.add_argument("--inbox", default="", help="Override inbox dir (default: data/pdf_inbox)")
    parser.add_argument("--store", default="", help="Override pdf store dir (default: data/pdf)")
    parser.add_argument("--once", action="store_true", help="Single scan (default)")
    parser.add_argument("--watch", action="store_true", help="Poll inbox every N seconds")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--no-blind-ingest", action="store_true", help="Do not auto-create entries from PDF DOI")
    parser.add_argument("--no-quarantine", action="store_true", help="Leave unmatched files in inbox")
    args = parser.parse_args()

    store = LocalPdfStore(
        inbox=args.inbox or None,
        store_dir=args.store or None,
    )
    store.ensure_dirs()

    inbox_abs = store.inbox.resolve()
    print(f"pdf_inbox: {inbox_abs}")
    print(f"pdf_store: {store.store_dir.resolve()}")

    if args.watch:
        while True:
            stats = process_inbox_once(
                store=store,
                db_path=args.db,
                quarantine=not args.no_quarantine,
                blind_ingest=not args.no_blind_ingest,
            )
            if any(stats.values()):
                print(f"scan: {stats}")
            time.sleep(args.interval)
    else:
        stats = process_inbox_once(
            store=store,
            db_path=args.db,
            quarantine=not args.no_quarantine,
            blind_ingest=not args.no_blind_ingest,
        )
        print(f"done: {stats}")


if __name__ == "__main__":
    main()
