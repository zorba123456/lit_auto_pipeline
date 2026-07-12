"""Minimal metadata enrich via public APIs (§16 / §17)."""

from __future__ import annotations

import re
from typing import Any

import requests

from aes_workflow.ingest_ids import normalize_doi

CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
USER_AGENT = "AES-Intel/1.0 (mailto:dev@aes-intel.local; blind-pdf-ingest)"


def _strip_jats(text: str) -> str:
    if not text:
        return ""
    plain = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", plain).strip()


def _format_authors(authors: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for author in authors:
        given = (author.get("given") or "").strip()
        family = (author.get("family") or "").strip()
        name = f"{given} {family}".strip() if given or family else (author.get("name") or "").strip()
        if name:
            names.append(name)
    return "; ".join(names)


def _format_date(parts: list[list[int]] | None) -> str:
    if not parts or not parts[0]:
        return ""
    p = parts[0]
    if len(p) >= 3:
        return f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
    if len(p) == 1:
        return str(p[0])
    if len(p) == 2:
        return f"{p[0]:04d}-{p[1]:02d}"
    return ""


def parse_crossref_message(message: dict[str, Any]) -> dict[str, str]:
    title = (message.get("title") or [""])[0].strip()
    journal = (message.get("container-title") or [""])[0].strip()
    authors = _format_authors(message.get("author") or [])
    abstract = _strip_jats(message.get("abstract") or "")
    doi = normalize_doi(message.get("DOI")) or ""
    pub_date = ""
    for key in ("published-print", "published-online", "created", "issued"):
        block = message.get(key) or {}
        pub_date = _format_date(block.get("date-parts"))
        if pub_date:
            break
    pages = (message.get("page") or "").strip()
    publisher_url = (message.get("URL") or "").strip()
    if not publisher_url and doi:
        publisher_url = f"https://doi.org/{doi}"
    return {
        "title": title,
        "journal": journal,
        "authors": authors,
        "abstract": abstract[:4000],
        "doi": doi,
        "pub_date": pub_date,
        "pages": pages,
        "publisher_url": publisher_url,
        "source_url": publisher_url,
    }


def enrich_from_crossref(doi: str, *, timeout: float = 30.0) -> dict[str, str] | None:
    norm = normalize_doi(doi)
    if not norm:
        return None
    url = CROSSREF_WORKS.format(doi=requests.utils.quote(norm, safe=""))
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    payload = resp.json()
    message = payload.get("message") or {}
    if not message:
        return None
    return parse_crossref_message(message)


def enrich_identifiers(identifiers: dict[str, str]) -> tuple[dict[str, str], str]:
    """Return (enriched_fields, enrich_source)."""
    if identifiers.get("doi"):
        data = enrich_from_crossref(identifiers["doi"])
        if data:
            return data, "crossref"
    return {}, "none"
