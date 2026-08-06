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


# 微信正文 DOI 后常紧跟杂质（无空格分隔，因 OCR/正文清洗删了空白）：
#   "10.1007/x.epub ahead of print.pmid:123" → 去空格后 "10.1007/x.epubaheadofprint.pmid:123"
# 这些语义词/锚点必须把 DOI 后缀截断，否则会造出垃圾 DOI 对象（§13.6 对象化暴露此 bug）。
# 只保留高信号锚点词——不能加 of/print/read 等泛词，会误命中 DOI 内部字母（如 asjof/ojag）。
# firstpublished 必须整体优先于 published，避免把 "10.1111/jocd.71063firstpublished" 截到 ...63first。
_DOI_IMPURITY = re.compile(
    r"(?i)(firstpublished|e?pub|published|pmid|pmcid|medline|doi:)",  # epub 在最前可截断 e.pubaheadofprint
)


def _truncate_doi(raw: str) -> str | None:
    """截断微信正文抽取的原始 DOI 串，去掉 epub/pmid/pmcid 等杂质，返回干净 DOI。"""
    if not raw:
        return None
    m = _DOI_IMPURITY.search(raw)
    if m:
        raw = raw[: m.start()].rstrip(".")
    norm: str | None = normalize_doi(raw)
    if not norm:
        return None
    # 二次防御：仍含明显杂质词则弃
    if re.search(r"(?i)epub|pmid|pmcid|published|medline", norm):
        return None
    return norm



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
        norm = _truncate_doi(doi)
        if norm and norm not in seen:
            seen.add(norm)
            result.append({"type": "doi", "value": norm})
    pmids = set(PMID_PATTERN.findall(text))
    for pmid in pmids:
        if pmid not in seen:
            seen.add(pmid)
            result.append({"type": "pmid", "value": pmid})
    return result


def _ensure_objects_layer(conn: sqlite3.Connection) -> None:
    """确保 objects / object_sources / entry_object_links 表存在（幂等）。

    微信正文扫描链路此前不接触对象层；此处按《测试阶段行动框架》§13.6 对象化补缺，
    把微信条目扫出的 DOI 升级为文献对象前，先保证三表就位（对齐 schema_stage0 增量迁移）。
    """
    for name in ("objects", "object_sources", "entry_object_links"):
        r = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        if r:
            continue
        if name == "objects":
            conn.execute(
                """CREATE TABLE objects (
                    object_id TEXT PRIMARY KEY,
                    id_type TEXT NOT NULL
                            CHECK (id_type IN ('doi','pmid','cmaid','cnki','title_hash')),
                    stage TEXT NOT NULL DEFAULT 'discovered'
                            CHECK (stage IN ('discovered','screened','fulltext','summarized','detailed')),
                    is_final_version TEXT NOT NULL DEFAULT 'unknown'
                            CHECK (is_final_version IN ('0','1','unknown')),
                    has_video        TEXT NOT NULL DEFAULT 'unknown'
                            CHECK (has_video IN ('0','1','unknown')),
                    video_available  TEXT NOT NULL DEFAULT 'unknown'
                            CHECK (video_available IN ('0','1','unknown')),
                    human_finalized  INTEGER NOT NULL DEFAULT 0 CHECK (human_finalized IN (0,1)),
                    normalize_status TEXT,
                    screen_status    TEXT,
                    tag_status       TEXT,
                    created_at     TEXT NOT NULL,
                    updated_at     TEXT NOT NULL
                )"""
            )
        elif name == "object_sources":
            conn.execute(
                """CREATE TABLE object_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_id TEXT NOT NULL REFERENCES objects(object_id) ON DELETE CASCADE,
                    channel TEXT NOT NULL CHECK (channel IN ('rss','wechat','ima','manual')),
                    source_detail TEXT,
                    link TEXT,
                    first_seen_at TEXT NOT NULL,
                    UNIQUE (object_id, channel, source_detail)
                )"""
            )
        else:
            conn.execute(
                """CREATE TABLE entry_object_links (
                    object_id    TEXT NOT NULL REFERENCES objects(object_id) ON DELETE CASCADE,
                    article_key  TEXT NOT NULL REFERENCES entries(article_key) ON DELETE CASCADE,
                    link_status  TEXT NOT NULL DEFAULT 'linked'
                                 CHECK (link_status IN ('linked','candidate','broken')),
                    PRIMARY KEY (object_id, article_key)
                )"""
            )


def _upgrade_to_object(
    conn: sqlite3.Connection,
    article_key: str,
    doi: str,
    source_url: str,
    feed_name: str,
) -> str:
    """§13.6 对象化补缺：把微信扫出的真实 DOI 建为文献对象并挂条目。

    - 建/复用 real DOI 对象（跨渠道归并：同 DOI 多渠道 → 挂同一对象）
    - entry_object_links 关联条目
    - object_sources 记 wechat 渠道（公众号/群名可回溯）
    - entries.object_id 改写为 DOI

    返回 action: create_doi | reuse_existing。
    """
    now = utc_now()
    doi = doi.lower()

    obj_row = conn.execute(
        "SELECT object_id FROM objects WHERE object_id=? AND id_type='doi'", (doi,)
    ).fetchone()
    if obj_row:
        target_obj = obj_row["object_id"]
        action = "reuse_existing"
    else:
        target_obj = doi
        conn.execute(
            """INSERT OR IGNORE INTO objects
               (object_id, id_type, stage, is_final_version, has_video, video_available,
                normalize_status, screen_status, tag_status,
                source_group, origin_channel, origin_detail, origin_url,
                created_at, updated_at)
               VALUES (?, 'doi', 'discovered', 'unknown', 'unknown', 'unknown',
                       'done', 'pending', NULL,
                       'wechat_scan', 'wechat', ?, ?,
                       ?, ?)""",
            (doi, feed_name or "未知", source_url, now, now),
        )
        action = "create_doi"

    conn.execute(
        """INSERT OR IGNORE INTO entry_object_links (object_id, article_key, link_status)
           VALUES (?, ?, 'linked')""",
        (target_obj, article_key),
    )
    # 来源记录：微信渠道并入该对象（object_sources UNIQUE(object_id,channel,source_detail)）
    conn.execute(
        """INSERT OR IGNORE INTO object_sources (object_id, channel, source_detail, link, first_seen_at)
           SELECT ?, 'wechat', ?, ?, ?
           WHERE NOT EXISTS (SELECT 1 FROM object_sources WHERE object_id=? AND channel='wechat' AND source_detail=?)""",
        (target_obj, feed_name or "未知", source_url, now, target_obj, feed_name or "未知"),
    )
    # 条目改挂真实 DOI 对象（微信条目此前无 title_hash 占位，若无占位则跳过 superseded）
    conn.execute(
        "UPDATE entries SET object_id=?, updated_at=? WHERE article_key=?",
        (target_obj, now, article_key),
    )
    conn.execute(
        """UPDATE objects SET normalize_status='superseded', updated_at=?
           WHERE object_id=? AND id_type='title_hash'""",
        (now, article_key),
    )
    return action


def update_entry_with_identifiers(
    conn: sqlite3.Connection,
    article_key: str,
    identifiers: list[dict],
    wechat_url: str,
    feed_name: str,
) -> None:
    """将提取到的标识符更新到 entries 表和 entry_identifiers。

    §13.6 对象化补缺：扫出 DOI 后将微信条目升级为文献对象
    （建/复用 real DOI 对象 + 挂 entry_object_links + 记 wechat 来源）。
    """
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
        # 对象化补缺：把真实 DOI 升级为文献对象
        _ensure_objects_layer(conn)
        _upgrade_to_object(
            conn, article_key, updates["doi"], wechat_url, feed_name
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


def scan_batch(*, use_ocr: bool = False, cursor: tuple | None = None, full: bool = False,
               min_ingest_at: str | None = None) -> dict:
    """扫描一批 discovery_type=wechat_news 的条目。

    keyset 游标（cursor = 上一批最后一条的 (ingest_at, article_key)）实现翻页：
    每次取「队列中比游标更旧」的 BATCH_SIZE 条，扫过即跳前，不回扫已处理的，
    从而覆盖全部白名单条目。缺省 cursor=None 从最新开始。返回 stats 含
    next_cursor（本批末条的元组，供下一批推进）。

    full=True（每周全量）：不限 journal 白名单，扫全部 wechat_news（DOI 为空）——
    这样 36 号之外的新号也能被扫到，命中 DOI 后由 cron 层增补进命中池（§10.2b）。
    full=False（默认/每日增量）：限定 doi_scan_accounts 命中池期刊，省抓取。

    min_ingest_at（每日增量水位）：只扫 ingest_at > 该值 的新入库条目（增量位点由
    cron 层存状态文件推进），不重扫历史已处理条目。
    """
    stats: dict = {"scanned": 0, "found": 0, "no_id": 0, "fetch_failed": 0, "ocr_used": 0}

    from aes_workflow.doi_scan_config import get_doi_scan_accounts
    doi_accounts = get_doi_scan_accounts()
    if not full and not doi_accounts:
        print("[prefilter] ⚠️ DOI 扫描白名单为空（config.json 中未配置 doi_scan_accounts）")
        return stats

    cursor_sql = ""
    cursor_params: list = []
    if cursor:
        cursor_sql = "AND (ingest_at, article_key) < (?, ?)"
        cursor_params = [cursor[0], cursor[1]]

    # 白名单期刊条件（仅增量模式套用；全量模式不限 journal）
    journal_sql = ""
    journal_params: list = []
    if not full:
        placeholders = ", ".join("?" for _ in doi_accounts)
        journal_sql = f"AND journal IN ({placeholders})"
        journal_params = doi_accounts

    # 增量水位条件：只扫最近一次扫描之后新入库的条目
    water_sql = ""
    water_params: list = []
    if min_ingest_at:
        water_sql = "AND ingest_at > ?"
        water_params = [min_ingest_at]

    with db_session() as conn:
        rows = conn.execute(
            f"""SELECT article_key, source_url, journal AS feed_name, ingest_at
               FROM entries
               WHERE discovery_type = 'wechat_news'
                 AND source_url LIKE '%mp.weixin.qq.com%'
                 {journal_sql}
                 {water_sql}
                 AND (doi IS NULL OR doi = '')
                 AND (pmid IS NULL OR pmid = '')
                 {cursor_sql}
               ORDER BY ingest_at DESC, article_key DESC
               LIMIT ?""",
            (*journal_params, *water_params, *cursor_params, BATCH_SIZE),
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

        # 游标推进：记录本批最后一条（队列位置，与 fetch 成败无关）
        last = rows[-1]
        stats["next_cursor"] = (last["ingest_at"], last["article_key"])

    return stats



def main():
    parser = argparse.ArgumentParser(description="微信文章预筛选：提取 DOI/PMID")
    parser.add_argument("--ocr", action="store_true", help="启用 OCR 截图提取")
    parser.add_argument("--limit", type=int, default=BATCH_SIZE, help="扫描条数")
    parser.add_argument("--article-key", type=str, help="单条 article_key")
    parser.add_argument("--url", type=str, help="指定 URL 测试")
    parser.add_argument("--scan-all", action="store_true",
                        help="翻页扫描全部白名单微信条目（默认只扫最新一批 BATCH_SIZE 条）")
    parser.add_argument("--full", action="store_true",
                        help="全量扫描：不限 journal 白名单，扫全部 wechat_news（每周全量用，配合 --scan-all 增补命中池）")
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
        if args.scan_all:
            cursor = None
            grand = {"scanned": 0, "found": 0, "no_id": 0, "fetch_failed": 0, "ocr_used": 0}
            n = 0
            while True:
                stats = scan_batch(use_ocr=args.ocr, cursor=cursor, full=args.full)
                for k in grand:
                    kk = k
                    grand[kk] += int(stats.get(kk, 0))
                print(f"  [batch {n+1}] { {k: stats.get(k) for k in ('scanned','found','no_id','fetch_failed')} }", flush=True)
                n += 1
                if not stats.get("next_cursor") or stats.get("scanned", 0) == 0:
                    break
                cursor = stats["next_cursor"]
            print(f"[prefilter] 全量扫描完成（{n} 批）: {grand}")
        else:
            stats = scan_batch(use_ocr=args.ocr)
            print(f"[prefilter] {stats}")


if __name__ == "__main__":
    main()
