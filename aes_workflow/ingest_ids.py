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
# citation 形态：明写 "doi:10.x/yyy"（推文/引文里作者亲手写的，可信度最高）
CITATION_DOI_RE = re.compile(r"(?<![0-9A-Za-z])doi\s*[:：]\s*(10\.\d{4,9}/[^\s\]\>\x22<&]+)", re.I)

ID_PRIORITY = ("doi", "pmid", "pii", "platform_id")

# ── DOI 候选分级 + 前缀包含去重（2026-09 定稿）────────────────────────────
# 背景：同一条内容里同一文献会以多种形态出现（citation 明写 / 裸文本 / URL 路径），
# URL 形态常带出版社站内尾巴（如 OUP /doi/<doi>/<site_id>）导致构造出假 DOI，
# 且假串覆盖真串后 Crossref 404 → 标题解析失败。规则：
#   1. 前缀包含去重：cand 以更高优先级候选为前缀（多出 /segment）→ 判同一文献，
#      保留高优先级形态。与出版商无关，通用。
#   2. URL 抽取剥站内尾段：仅当 URL 非 doi.org（doi.org 是规范短链永不带装饰）、
#      DOI 后缀有 ≥2 段、最后一段纯数字、且其余段存在含字母的段 → 剥掉最后一段。
#      Hindawi(10.1155/2021/6634677) 全段纯数字不误伤；AIP(1.xxxxx) 含点不误伤。
_CAND_PRIORITY = {"citation": 0, "text": 1, "url": 2}


def _cut_embedded_url(doi: str) -> str:
    """DOI 尾段吞并了紧贴的下一个 URL（推文常见「DOIhttps://doi.org/DOI」零空格拼接）：
    在 tail 内截断于 http(s):// 或 doi.org/ 处。"""
    cut = len(doi)
    for pat in ("https://", "http://", "doi.org/"):
        j = doi.find(pat)
        if j != -1:
            cut = min(cut, j)
    return doi[:cut] if cut < len(doi) else doi


def _strip_url_site_tail(doi: str, src: str, raw_url: str | None) -> str:
    """URL 路径抽取的 DOI 剥出版社站内尾段（见上规则 2）。citation/text 形态不动。"""
    if src != "url":
        return doi
    u = (raw_url or "").lower()
    if "doi.org/" in u:
        return doi
    segs = doi.split("/")
    prefix_len = 2  # 10.xxxxx → 前 2 段是注册局/前缀
    tail = segs[prefix_len:]
    if len(tail) < 2:
        return doi
    if not tail[-1].isdigit():
        # 增强(2026-09)：PDF 下载链接整段误当 DOI（10.1093/asj/sjag170/70729992/sjag170.pdf）
        if tail[-1].lower().endswith(".pdf"):
            stripped = "/".join(segs[:-1])
            return _strip_url_site_tail(stripped, src, raw_url)  # 递归再剥 OUP 型纯数字尾段
        return doi
    if not any(any(ch.isalpha() for ch in s) for s in tail[:-1]):
        return doi
    return "/".join(segs[:-1])


def extract_doi_candidates(*, link: str = "", guid: str = "", citation: str = "",
                           title: str = "") -> list[dict]:
    """收集全部 DOI 候选并分级（citation>text>url）、剥 URL 尾段、前缀包含去重。

    返回按优先级排序的 [{"value", "src"}]，index 0 为最佳候选。
    """
    sources = [("citation", citation), ("text", title), ("url", link), ("url", guid)]
    cands: list[dict] = []
    seen_raw: set[str] = set()
    for src, blob in sources:
        if not blob:
            continue
        hits: list[str] = []
        if src == "citation":
            hits += CITATION_DOI_RE.findall(blob)
        # citation/title 文本里也可能有裸 DOI；link/guid 全按 url 级
        if src in ("citation", "text"):
            hits += [d for d in DOI_RE.findall(blob) if d not in hits]
        else:
            hits += [d for d in DOI_RE.findall(blob) if d not in hits]
        for raw in hits:
            norm = normalize_doi(_strip_url_site_tail(_cut_embedded_url(raw), src, blob if src == "url" else None))
            if norm and norm not in seen_raw:
                seen_raw.add(norm)
                cands.append({"value": norm, "src": src})
    # 前缀包含去重：低优先级候选若以高优先级候选为前缀 → 丢弃
    cands.sort(key=lambda c: (_CAND_PRIORITY.get(c["src"], 9), c["value"]))
    kept: list[dict] = []
    for c in cands:
        if any(c["value"] == k["value"] or c["value"].startswith(k["value"] + "/")
               for k in kept):
            continue
        kept.append(c)
    return kept


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
