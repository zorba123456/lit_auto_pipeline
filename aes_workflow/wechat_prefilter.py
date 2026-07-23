#!/usr/bin/env python3
"""wechat_prefilter — 微信公众号预筛选：扫描 wechat_news 条目，
拉取文章正文，正则提取 DOI/PMID，可选 OCR 截图提取 DOI。

用法:
  python3 -m aes_workflow.wechat_prefilter              # 扫描一批 wechat_news
  python3 -m aes_workflow.wechat_prefilter --ocr         # 开启 OCR 截图提取
  python3 -m aes_workflow.wechat_prefilter --limit 20    # 只扫 20 条
  python3 -m aes_workflow.wechat_prefilter --article-key <key>  # 只扫单条
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import argparse
from pathlib import Path
from datetime import datetime, timezone

from aes_workflow.db import db_session, utc_now
from aes_workflow.ingest_ids import normalize_doi

# ── 路径 ───────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
BATCH_SIZE = 50
FETCH_DELAY = 0.3  # 微信拉取间隔，礼貌减速

# ── 正则 ──────────────────────────────────────────────
# DOI 合法字符集：字母数字 + -._;()/:，不包含中文
DOI_PATTERN = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)', re.IGNORECASE)
PMID_PATTERN = re.compile(r'\bPMID\s*[:-]?\s*(\d{7,8})\b', re.IGNORECASE)
URL_DOI_PATTERN = re.compile(
    r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+)',
    re.IGNORECASE,
)

# 已知以截图为主的文献解读号
IMAGE_ACCOUNTS = {"取名太麻烦"}

WECHAT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 "
    "MicroMessenger/6.8.0(0x16080000) NetType/WIFI MiniProgramEnv/Mac "
    "MacWechat/WMPF MacWechat/3.8.7(0x13080710) XWEB/1191"
)

# ── 微信数据库路径 ──
WX_CACHE_DB = ROOT / "data" / "wechat_fetch_cache.db"


def init_cache_db():
    WX_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(WX_CACHE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wechat_fetch_cache (
            url TEXT PRIMARY KEY,
            text TEXT,
            html TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_cached(url: str) -> dict | None:
    conn = sqlite3.connect(str(WX_CACHE_DB))
    row = conn.execute(
        "SELECT text, html FROM wechat_fetch_cache WHERE url = ?",
        (url,),
    ).fetchone()
    conn.close()
    if row:
        return {"text": row[0] or "", "html": row[1] or ""}
    return None


def set_cached(url: str, text: str, html: str):
    conn = sqlite3.connect(str(WX_CACHE_DB))
    conn.execute(
        """INSERT OR REPLACE INTO wechat_fetch_cache (url, text, html, fetched_at)
           VALUES (?, ?, ?, ?)""",
        (url, text, html, utc_now()),
    )
    conn.commit()
    conn.close()


def clean_wechat_url(url: str) -> str:
    """归一化微信文章 URL。"""
    if not url:
        return ""
    url = url.replace("\\/", "/").replace("\\", "")
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    if "mp.weixin.qq.com" in parsed.netloc and parsed.path == "/s":
        qs = parse_qs(parsed.query)
        biz = qs.get("__biz", [""])[0]
        mid = qs.get("mid", [""])[0]
        idx = qs.get("idx", [""])[0]
        sn = qs.get("sn", [""])[0]
        if biz and mid and idx:
            clean = f"__biz={biz}&mid={mid}&idx={idx}"
            if sn:
                clean += f"&sn={sn}"
            return f"https://mp.weixin.qq.com/s?{clean}"
    if "#" in url:
        url = url.split("#", 1)[0]
    return url.strip()


def fetch_article_text(url: str) -> tuple[str | None, str | None]:
    """拉取微信文章正文（纯文本）。使用多指纹 UA 模拟微信桌面版内置浏览器。
    返回 (text, html) 元组。"""
    url = clean_wechat_url(url)
    if not url:
        return None, None

    # 先查缓存
    cached = get_cached(url)
    if cached and cached["text"]:
        return cached["text"], cached.get("html")

    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": WECHAT_UA,
                "Referer": "https://mp.weixin.qq.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        charset = "utf-8"
        m = re.search(rb"charset=['\"]?([\w-]+)", raw[:2000], re.I)
        if m:
            charset = m.group(1).decode("ascii", errors="ignore") or "utf-8"
        html_text = raw.decode(charset, errors="replace")
    except Exception:
        return None, None

    # 提取正文
    text = ""
    js_match = re.search(
        r'<div[^>]+id="js_content"[^>]*>(.*?)</div>\s*<',
        html_text, re.S | re.I,
    )
    if js_match:
        text = re.sub(r"<[^>]+>", " ", js_match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
    else:
        # 退化：取 meta description
        m = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"', html_text, re.I,
        )
        if m:
            text = m.group(1).strip()

    # 写缓存
    set_cached(url, text, html_text)
    return text, html_text


def extract_images_from_html(html_text: str) -> list[str]:
    """从 HTML 中提取图片 URL。"""
    if not html_text:
        return []
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    urls = []
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if src and str(src).startswith("http"):
            urls.append(str(src))
    return urls


def ocr_image_url(img_url: str) -> list[str]:
    """单图 Tesseract OCR → 提取 DOI/PMID。"""
    try:
        from curl_cffi import requests as curl_requests
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        )
        resp = curl_requests.get(
            img_url,
            headers={"User-Agent": ua, "Referer": "https://mp.weixin.qq.com/"},
            impersonate="chrome116",
            timeout=15,
        )
        resp.raise_for_status()
        img_data = resp.content
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_data)
            tmp = f.name
        res = subprocess.run(
            ["tesseract", tmp, "stdout", "-l", "eng"],
            capture_output=True, text=True, timeout=15,
        )
        os.remove(tmp)
        if res.returncode == 0:
            return extract_identifiers_from_text(res.stdout)
    except Exception:
        pass
    return []


def extract_identifiers_from_text(text: str) -> list[dict]:
    """从纯文本中扫描 DOI/PMID。先清洗 OCR 产生的空格。"""
    if not text:
        return []
    # OCR 可能在小字间插入空格，先压缩
    clean = re.sub(r'\s+', '', text)
    seen = set()
    result = []
    dois = set(DOI_PATTERN.findall(clean) + URL_DOI_PATTERN.findall(clean))
    for doi in dois:
        norm = normalize_doi(doi)
        if norm and norm not in seen:
            seen.add(norm)
            result.append({"type": "doi", "value": norm})
    pmids = set(PMID_PATTERN.findall(text))
    for pmid in pmids:
        if pmid not in seen:
            seen.add(pmid)
            result.append({"type": "pmid", "value": pmid})
    return result


def update_entry_with_identifiers(
    conn: sqlite3.Connection,
    article_key: str,
    identifiers: list[dict],
    wechat_url: str,
    feed_name: str,
) -> None:
    """将提取到的标识符更新到 entries 表和 entry_identifiers。"""
    now = utc_now()

    # 收集标识符写入主表
    updates = {}
    for idf in identifiers:
        t, v = idf["type"], idf["value"]
        if t == "doi" and not updates.get("doi"):
            updates["doi"] = v
        elif t == "pmid" and not updates.get("pmid"):
            updates["pmid"] = v

    if updates.get("doi"):
        conn.execute(
            "UPDATE entries SET doi = ?, discovery_type = 'wechat_discovery', "
            "meta_status = 'meta_partial', updated_at = ? WHERE article_key = ?",
            (updates["doi"], now, article_key),
        )
    elif updates.get("pmid"):
        conn.execute(
            "UPDATE entries SET pmid = ?, discovery_type = 'wechat_discovery', "
            "meta_status = 'meta_partial', updated_at = ? WHERE article_key = ?",
            (updates["pmid"], now, article_key),
        )
    else:
        return  # 没有有效标识符，不升级

    # 写 entry_identifiers
    for idf in identifiers:
        conn.execute(
            """INSERT OR IGNORE INTO entry_identifiers (id_type, id_value, article_key)
               VALUES (?, ?, ?)""",
            (idf["type"], idf["value"], article_key),
        )


def scan_one(
    conn: sqlite3.Connection,
    article_key: str,
    source_url: str,
    feed_name: str,
    *,
    use_ocr: bool = False,
) -> dict:
    """扫描一篇微信文章。返回结果统计。"""
    try:
        text, html = fetch_article_text(source_url)
    except TypeError:
        return {"status": "fetch_failed", "identifiers": []}
    if not text:
        return {"status": "fetch_failed", "identifiers": []}

    # Tier 1: 文本正则
    ids = extract_identifiers_from_text(text)
    ocr_used = False

    # Tier 2: OCR 截图提取
    if not ids and use_ocr and html:
        img_urls = extract_images_from_html(html)
        if img_urls:
            for img_url in img_urls[-3:]:  # 只扫最后 3 张图
                ocr_ids = ocr_image_url(img_url)
                if ocr_ids:
                    ids.extend(ocr_ids)
                    ocr_used = True
                    break

    if ids:
        update_entry_with_identifiers(conn, article_key, ids, source_url, feed_name)

    return {
        "status": "found" if ids else "no_id",
        "identifiers": ids,
        "ocr_used": ocr_used,
        "text_len": len(text),
    }


def scan_batch(*, use_ocr: bool = False) -> dict:
    """扫描一批 discovery_type=wechat_news 的条目（限 DOI 扫描白名单）。"""
    stats = {"scanned": 0, "found": 0, "no_id": 0, "fetch_failed": 0, "ocr_used": 0}

    from aes_workflow.doi_scan_config import get_doi_scan_accounts
    doi_accounts = get_doi_scan_accounts()
    if not doi_accounts:
        print("[prefilter] ⚠️ DOI 扫描白名单为空（config.json 中未配置 doi_scan_accounts）")
        return stats

    placeholders = ",".join("?" for _ in doi_accounts)
    with db_session() as conn:
        rows = conn.execute(
            f"""SELECT article_key, source_url, journal AS feed_name
               FROM entries
               WHERE discovery_type = 'wechat_news'
                 AND source_url LIKE '%mp.weixin.qq.com%'
                 AND journal IN ({placeholders})
                 AND (doi IS NULL OR doi = '')
                 AND (pmid IS NULL OR pmid = '')
               LIMIT ?""",
            (*doi_accounts, BATCH_SIZE),
        ).fetchall()

        if not rows:
            return stats

        stats["scanned"] = len(rows)
        for row in rows:
            feed_name = row["feed_name"] or "未知"
            url = row["source_url"]
            if not url or not url.strip():
                stats["fetch_failed"] += 1
                continue
            result = scan_one(
                conn,
                row["article_key"],
                url,
                feed_name,
                use_ocr=use_ocr,
            )
            if result["status"] == "found":
                stats["found"] += 1
                if result["ocr_used"]:
                    stats["ocr_used"] += 1
            elif result["status"] == "no_id":
                stats["no_id"] += 1
            elif result["status"] == "fetch_failed":
                stats["fetch_failed"] += 1
            time.sleep(FETCH_DELAY)

    return stats


def main():
    parser = argparse.ArgumentParser(description="微信文章预筛选：提取 DOI/PMID")
    parser.add_argument("--ocr", action="store_true", help="启用 OCR 截图提取")
    parser.add_argument("--limit", type=int, default=BATCH_SIZE, help="扫描条数")
    parser.add_argument("--article-key", type=str, help="单条 article_key")
    parser.add_argument("--url", type=str, help="指定 URL 测试")
    args = parser.parse_args()

    init_cache_db()

    if args.article_key:
        with db_session() as conn:
            row = conn.execute(
                "SELECT article_key, source_url, journal FROM entries WHERE article_key = ?",
                (args.article_key,),
            ).fetchone()
        if not row:
            print(f"❌ 无此 article_key: {args.article_key}")
            return
        result = scan_one(conn, row["article_key"], row["source_url"],
                          row["journal"] or "未知", use_ocr=args.ocr)
        print(f"[single] {result}")

    elif args.url:
        text, html = fetch_article_text(args.url)
        if text:
            ids = extract_identifiers_from_text(text)
            print(f"[url] text_len={len(text)}, ids={ids}")
            if not ids and args.ocr and html:
                imgs = extract_images_from_html(html)
                print(f"[url] images={len(imgs)}")
                # 对最后 5 张图执行 OCR
                for img_url in imgs[-5:]:
                    ocr_ids = ocr_image_url(img_url)
                    if ocr_ids:
                        print(f"[url] OCR found: {ocr_ids}")
                if not any(ocr_image_url(u) for u in imgs[-5:]):
                    print("[url] OCR scanned but no DOI found")
        else:
            print("[url] fetch_failed")

    else:
        print(f"[prefilter] 开始扫描（OCR={'开' if args.ocr else '关'}）")
        stats = scan_batch(use_ocr=args.ocr)
        print(f"[prefilter] {stats}")


if __name__ == "__main__":
    main()
