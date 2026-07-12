"""Local filesystem paths for PDF workflow (dev defaults)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# pdf-router / browser download target (watcher reads from here)
PDF_INBOX = ROOT / "data" / "pdf_inbox"

# Canonical on-disk fulltext after matching
PDF_STORE_DIR = ROOT / "data" / "pdf"

# Unmatched drops stay out of the inbox scan loop
PDF_UNMATCHED = ROOT / "data" / "pdf_unmatched"


def pdf_inbox_path() -> Path:
    return PDF_INBOX


def pdf_store_path(article_key: str) -> Path:
    return PDF_STORE_DIR / f"{article_key}.pdf"


def rel_pdf_path(article_key: str) -> str:
    return f"data/pdf/{article_key}.pdf"
