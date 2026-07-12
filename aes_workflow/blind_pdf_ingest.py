"""Create entries from blind PDF downloads (no prior XML ingest)."""

from __future__ import annotations

import re
from pathlib import Path

from aes_workflow.db import log_ingest, register_identifiers, utc_now
from aes_workflow.ingest_ids import article_key_from_identifiers, normalize_doi, primary_id_for_log
from aes_workflow.meta_enrich import enrich_identifiers
from aes_workflow.pdf_extract import extract_ids_from_pdf

TITLE_FROM_TEXT = re.compile(r"^(.{12,200})$", re.M)


def _title_from_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if reader.metadata:
            for key in ("/Title", "title", "/Subject"):
                val = reader.metadata.get(key)
                if val and len(str(val).strip()) >= 12:
                    return str(val).strip()[:500]
        if reader.pages:
            text = (reader.pages[0].extract_text() or "").strip()
            for line in text.splitlines():
                line = line.strip()
                if len(line) >= 12 and not line.lower().startswith("http"):
                    return line[:500]
    except Exception:
        pass
    return ""


def _fallback_title(identifiers: dict[str, str]) -> str:
    if identifiers.get("doi"):
        return f"Blind PDF · {identifiers['doi']}"
    if identifiers.get("pmid"):
        return f"Blind PDF · PMID {identifiers['pmid']}"
    if identifiers.get("pii"):
        return f"Blind PDF · PII {identifiers['pii']}"
    return "Blind PDF · unknown"


def build_blind_pdf_row(path: Path, identifiers: dict[str, str]) -> dict:
    enriched, enrich_source = enrich_identifiers(identifiers)
    ids = dict(identifiers)
    if enriched.get("doi"):
        ids["doi"] = normalize_doi(enriched["doi"]) or ids.get("doi", "")

    title = enriched.get("title") or _title_from_pdf_text(path) or _fallback_title(ids)
    abstract = enriched.get("abstract") or ""
    meta_status = "meta_complete" if enriched.get("title") and abstract else (
        "meta_partial" if enriched.get("title") else "meta_pending"
    )

    return {
        "identifiers": ids,
        "title": title,
        "authors": enriched.get("authors") or "",
        "abstract": abstract,
        "journal": enriched.get("journal") or "",
        "doi": ids.get("doi"),
        "pmid": ids.get("pmid"),
        "pmcid": ids.get("pmcid"),
        "pii": ids.get("pii"),
        "platform": "blind_pdf",
        "platform_id": None,
        "source_url": enriched.get("source_url") or "",
        "publisher_url": enriched.get("publisher_url") or "",
        "issue": "",
        "pages": enriched.get("pages") or "",
        "pub_date": enriched.get("pub_date") or "",
        "lang": "en",
        "feed_id": "blind_pdf",
        "meta_status": meta_status,
        "screening_status": "screening_pending",
        "enrich_source": enrich_source,
    }


def insert_blind_pdf_entry(conn, row: dict, *, pdf_name: str) -> str:
    article_key = article_key_from_identifiers(row["identifiers"])
    if not article_key:
        raise ValueError("cannot derive article_key from PDF identifiers")

    now = utc_now()
    conn.execute(
        """
        INSERT INTO entries (
          article_key, feed_id, ingest_source, lang, title, journal, authors, abstract,
          doi, pmid, pmcid, pii, platform, platform_id, source_url, publisher_url,
          issue, pages, pub_date, meta_status, screening_status, ingest_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article_key,
            row["feed_id"],
            "blind_pdf",
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
            row["pages"],
            row["pub_date"],
            row["meta_status"],
            row["screening_status"],
            now,
            now,
        ),
    )
    register_identifiers(conn, article_key, row["identifiers"])
    id_type, id_value = primary_id_for_log(row["identifiers"])
    log_ingest(
        conn,
        ingest_source="blind_pdf",
        feed_file=pdf_name,
        id_type=id_type,
        id_value=id_value,
        article_key=article_key,
        duplicate=False,
    )
    return article_key


def try_ingest_blind_pdf(conn, path: Path) -> tuple[str | None, dict[str, str], str]:
    """Return (article_key, ids, reason). reason: ingested|no_ids|exists."""
    ids = extract_ids_from_pdf(path)
    if not ids:
        return None, {}, "no_ids"

    from aes_workflow.db import lookup_article_key

    existing = lookup_article_key(conn, ids)
    if existing:
        return existing, ids, "exists"

    row = build_blind_pdf_row(path, ids)
    article_key = insert_blind_pdf_entry(conn, row, pdf_name=path.name)
    return article_key, ids, "ingested"
