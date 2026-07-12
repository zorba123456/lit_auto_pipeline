"""Extract identifiers from PDF files for inbox matching."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from aes_workflow.ingest_ids import extract_doi_from_text, extract_pii_from_url, normalize_doi

ARTICLE_KEY_STEM = re.compile(r"^[a-f0-9]{64}$", re.I)
INCOMPLETE_SUFFIXES = (".crdownload", ".part", ".download", ".tmp")


def is_incomplete_download(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(s) for s in INCOMPLETE_SUFFIXES)


def article_key_from_filename(path: Path) -> str | None:
    stem = path.stem
    if ARTICLE_KEY_STEM.fullmatch(stem):
        return stem.lower()
    return None


def extract_ids_from_pdf(path: Path, *, max_pages: int = 2) -> dict[str, str]:
    ids: dict[str, str] = {}
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ids

    meta_parts: list[str] = []
    if reader.metadata:
        for val in reader.metadata.values():
            if val:
                meta_parts.append(str(val))
    blob = " ".join(meta_parts)
    doi = extract_doi_from_text(blob)
    if doi:
        ids["doi"] = doi

    for i in range(min(max_pages, len(reader.pages))):
        if ids.get("doi"):
            break
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            continue
        doi = extract_doi_from_text(text)
        if doi:
            ids["doi"] = doi

    # Some publishers embed PII in /URI metadata (rare); filename fallback handled elsewhere.
    for part in meta_parts:
        pii = extract_pii_from_url(part)
        if pii:
            ids["pii"] = pii
            break

    if ids.get("doi"):
        ids["doi"] = normalize_doi(ids["doi"]) or ids["doi"]
    return ids
