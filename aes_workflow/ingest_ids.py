"""Identifier normalization and article_key generation (§6.2)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\]\>\x22<&]+)", re.I)
PMID_RE = re.compile(r"\bpmid[:\s]*(\d{7,8})\b", re.I)
PUBMED_PMID_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{7,8})", re.I)
PMCID_RE = re.compile(r"\b(PMC\d+)\b", re.I)
PII_RE = re.compile(r"/pii/([A-Z0-9]+)", re.I)

ID_PRIORITY = ("doi", "pmid", "pii", "platform_id")


def normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    s = s.rstrip(".,;)")
    return s or None


def extract_doi_from_text(text: str | None) -> str | None:
    if not text:
        return None
    # OCR 可能在小字间插入空格，先匹配带空格的变形
    # 策略：先找 https://doi.org/ 格式
    url_doi = re.search(r'https?://doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9a-z\s]+)', text, re.I)
    if url_doi:
        raw = url_doi.group(1)
        # 去除空格后再尝试匹配标准 DOI
        clean = re.sub(r'\s+', '', raw)
        m = DOI_RE.search(clean)
        if m:
            return normalize_doi(m.group(1))
    m = DOI_RE.search(text)
    return normalize_doi(m.group(1)) if m else None


def extract_pmid_from_text(text: str | None) -> str | None:
    if not text:
        return None
    m = PMID_RE.search(text) or PUBMED_PMID_RE.search(text)
    return m.group(1) if m else None


def extract_pmcid_from_text(text: str | None) -> str | None:
    if not text:
        return None
    m = PMCID_RE.search(text)
    return m.group(1) if m else None


def extract_pii_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = PII_RE.search(url)
    return m.group(1).upper() if m else None


def extract_ids_from_item(*, link: str = "", guid: str = "", citation: str = "", title: str = "") -> dict[str, str]:
    blob = " ".join(x for x in (link, guid, citation, title) if x)
    ids: dict[str, str] = {}
    doi = extract_doi_from_text(blob)
    if doi:
        ids["doi"] = doi
    pmid = extract_pmid_from_text(blob)
    if pmid:
        ids["pmid"] = pmid
    pmcid = extract_pmcid_from_text(blob)
    if pmcid:
        ids["pmcid"] = pmcid
    pii = extract_pii_from_url(link or guid)
    if pii:
        ids["pii"] = pii
    return ids


def pick_canonical_guid(identifiers: dict[str, str]) -> str | None:
    for key in ID_PRIORITY:
        val = identifiers.get(key)
        if val:
            if key == "doi":
                return f"doi:{val}"
            if key == "pmid":
                return f"pmid:{val}"
            if key == "pii":
                return f"pii:{val}"
            if key == "platform_id":
                return f"platform:{val}"
    return None


def article_key_from_identifiers(identifiers: dict[str, str]) -> str | None:
    canonical = pick_canonical_guid(identifiers)
    if not canonical:
        return None
    digest = hashlib.sha256(f"aes|{canonical}".encode()).hexdigest()
    return digest


def merge_identifiers(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    out = dict(base)
    for k, v in extra.items():
        if v and k not in out:
            out[k] = v
    return out


def primary_id_for_log(identifiers: dict[str, str]) -> tuple[str, str]:
    for key in ID_PRIORITY:
        if identifiers.get(key):
            return key, identifiers[key]
    return "unknown", ""
