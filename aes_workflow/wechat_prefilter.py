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
# v2.11.7(bug 修复)：开头不用 \b —— CJK 在 Python \w 里算词字符，\b 在「汉字+10.」间失效，
#   导致紧贴中文的 DOI(无空格)漏抓。改 "前一位不是 ASCII 字母/数字" 的右边界判断，兼容 CJK 邻接。
DOI_PATTERN = re.compile(r'(?<![0-9A-Za-z])(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)', re.IGNORECASE)
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
# v2.11.7(bug): 正文里 DOI 与它自己的 https://doi.org/<doi> URL 常粘连(去空格后成一个串,
#   如 "10.1002/jum.70306https://doi.org/10.1002/jum.70306")。DOI 合法字符集含 / : .，
#   整串被贪心吞成一个"DOI"。真实 DOI 不含 :// 也不含 http，故在 URL 边界截断掉后半 URL。
_URL_BOUNDARY = re.compile(r"(?i)(https?://|ftp://|www\.)")


def _truncate_doi(raw: str) -> str | None:
    """截断微信正文抽取的原始 DOI 串，去掉 epub/pmid/pmcid 及粘连 URL 等杂质，返回干净 DOI。"""
    if not raw:
        return None
    # 1) 语义词杂质(epub/pmid/...)截断
    m = _DOI_IMPURITY.search(raw)
    if m:
        raw = raw[: m.start()].rstrip(".")
    # 2) 粘连 URL 截断：把 "10.../jum.70306https://doi.org/10.../jum.70306" 只留前一个干净 DOI
    u = _URL_BOUNDARY.search(raw)
    if u:
        raw = raw[: u.start()].rstrip(".")
    # 3) 真空格后多个裸 DOI 粘连(如 "10.1002/jum.7030610.1002/jum.70306")：只留第一个。
    #    真实 DOI 内不会紧接一个 "10.xxxxx/" 新前缀(4-9位数字)，故据此切成第一段。
    frags = list(re.finditer(r"10\.\d{4,9}/", raw))
    if len(frags) > 1 and frags[0].start() == 0:
        raw = raw[: frags[1].start()].rstrip(".")
    norm: str | None = normalize_doi(raw)
    if not norm:
        return None
    # 二次防御：仍含明显杂质词则弃
    if re.search(r"(?i)epub|pmid|pmcid|published|medline|https?://", norm):
        return None
    return norm



def extract_identifiers_from_text(text: str) -> list[dict]:
    """从纯文本中扫描 DOI/PMID。"""
    if not text:
        return []
    # v2.11.7(bug 修复)：不再对全文做 \s+ 去空白——那会把 DOI 与相邻词/URL 粘成串
    # (如 "10.1002/jum.70306https://doi.org/...") 且破坏 \b 边界(吞相邻 CJK/标签字母)。
    # 微信正文为 HTML 富文本提取(带真实空白/换行)，直接在原文上按边界匹配即可。
    # OCR 空格变形由独立 OCR 路径(use_ocr)处理，不走此处；_truncate_doi 仍做防御性截断。
    seen = set()
    result = []
    dois = set()
    dois |= set(DOI_PATTERN.findall(text))
    dois |= set(URL_DOI_PATTERN.findall(text))
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
        # v2.22 对象层清理后 objects 仅保留权威列；来源信息记 object_sources（来源表），不进 objects
        conn.execute(
            """INSERT OR IGNORE INTO objects
               (object_id, id_type, stage, is_final_version, has_video, video_available,
                normalize_status, screen_status, tag_status,
                created_at, updated_at)
               VALUES (?, 'doi', 'discovered', 'unknown', 'unknown', 'unknown',
                       'done', 'pending', NULL,
                       ?, ?)""",
            (doi, now, now),
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
    # 条目改挂真实 DOI 对象：v2.22 后 entries 无 object_id 列，挂接关系仅存 entry_object_links
    conn.execute(
        """UPDATE objects SET normalize_status='superseded', updated_at=?
           WHERE object_id=? AND id_type='title_hash'""",
        (now, article_key),
    )
    return action


# ── weekly_JC 专用：文末参考文献反查（正文无明文 DOI 时的补充算法）────────
# 仅适用于「微颗粒文献读书会Weekly JC」：该号推文正文从不嵌明文 DOI，
# 文献线索全在文末「参考文献」区（N. 编号，多为英文引文串）。
# 规则：refs 全部解析 → Crossref query.bibliographic 逐条反查 → 命中全部入库。
# 不做「主文献」判定（综述型推文多篇均有效，位置/日期信号经实测不可靠，2026-09-02 定稿）。

_REF_SECTION_SPLIT = re.compile(r"参考文献|References")
_REF_TAIL_CUT = re.compile(r"声明|往期推荐|撰稿|校审")
_REF_ITEM_SPLIT = re.compile(r"(?:^|\n|\s)\d{1,2}\.\s*")
_REF_MIN_LEN = 30          # 短于此的片段视为切分残渣
_LATIN = re.compile(r"[A-Za-z]{4}")  # 英文引文判定（中文教材类引用天然排除）


def parse_reference_section(text: str) -> list[str]:
    """从微信推文纯文本中切出文末参考文献条目列表。无 refs 区返回空表。"""
    m = _REF_SECTION_SPLIT.search(text)
    if not m:
        return []
    body = text[m.end():]
    cut = _REF_TAIL_CUT.search(body)
    if cut:
        body = body[: cut.start()]
    parts = _REF_ITEM_SPLIT.split(body)
    refs = []
    for p in parts:
        p = p.strip()
        if len(p) >= _REF_MIN_LEN and _LATIN.search(p):
            refs.append(p)
    return refs


def crossref_bibliographic_to_doi(ref: str, score_min: float = 80.0) -> str | None:
    """整条英文引文串 → Crossref query.bibliographic 反查 DOI（score 阈值拦截误匹配）。"""
    import requests
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={"query.bibliographic": ref[:500], "rows": 1},
            headers={"User-Agent": "aes-workbench/1.0 (mailto:workbench@example.com)"},
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
    except Exception:
        return None
    if not items:
        return None
    top = items[0]
    if float(top.get("score") or 0) < score_min:
        return None
    doi = (top.get("DOI") or "").lower()
    return doi or None


def scan_references_for_dois(text: str) -> list[dict]:
    """weekly_JC 补充算法入口：解析 refs 并逐条反查，返回去重后的 identifier 列表。"""
    refs = parse_reference_section(text)
    if not refs:
        return []
    seen: set[str] = set()
    result: list[dict] = []
    for ref in refs:
        doi = crossref_bibliographic_to_doi(ref)
        if doi and doi not in seen:
            seen.add(doi)
            result.append({"type": "doi", "value": doi, "via": "ref_backquery"})
    return result


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
        # v2.39 微信 DOI 汇总列表：每个 DOI 一条独立条目（discovery_type='wx_doi_entry'），
        # 供 C 模块侧栏「微信 DOI」类目展示。首命中建条，再命中加注提及+前置入库时间。
        try:
            _upsert_wx_doi_entry(conn, article_key, updates["doi"], wechat_url, feed_name, now)
        except Exception as e:
            print(f"[wx-doi-entry] ⚠️ 汇总条目写入失败(不阻塞主流程): {e}", flush=True)
    elif updates.get("pmid"):
        conn.execute(
            "UPDATE entries SET pmid = ?, discovery_type = 'wechat_discovery', "
            "meta_status = 'meta_partial', updated_at = ? WHERE article_key = ?",
            (updates["pmid"], now, article_key),
        )
    else:
        return  # 没有有效标识符，不升级

    # v2.22 后 entry_identifiers 表已随旧对象层清除，标识符只存 entries 主表列


def _norm_wechat_url(url: str) -> str:
    """微信文章 URL 归一化：截断 tempkey（会话级参数，同文不同值）及其后所有 query。
    chksm 同值即同文——保留 __biz/mid/idx/sn 即可稳定判同。"""
    if not url:
        return ""
    i = url.find("tempkey=")
    return url[:i] if i != -1 else url


def _upsert_wx_doi_entry(
    conn: sqlite3.Connection,
    src_article_key: str,
    doi: str,
    wechat_url: str,
    feed_name: str,
    now: str,
) -> str:
    """v2.39 微信 DOI 汇总条目（C 模块侧栏「微信 DOI」类目）。

    每个 DOI 恒一条独立条目：
      - article_key = sha256('wx_doi|'+doi.lower())，与源条目键空间隔离
      - discovery_type = 'wx_doi_entry'，不参与期刊/微信源常规视图
      - 标题取源文章标题（本条 DOI 最初被扫出的那篇）；feed_id 记 'wx_doi'
      - 摘要 = wx_doi_mentions JSON：每次命中的源文章（标题/链接/公号/该篇发布时间/该篇入库时间）
      - 再次命中：mentions 追加（按源 URL 去重）+ ingest_at 更新为最新命中时间（列表前置）
    幂等：同源文章重复扫描按 URL 去重不膨胀。返回 create|update|noop。
    """
    import hashlib
    import json as _json

    doi = (doi or "").strip().lower()
    if not doi:
        return "noop"

    src = conn.execute(
        "SELECT title, pub_date, ingest_at, journal FROM entries WHERE article_key=?",
        (src_article_key,),
    ).fetchone()
    if not src:
        return "noop"

    mention = {
        "title": src["title"] or "",
        "url": wechat_url or "",
        "feed": feed_name or "",
        "pub_date": src["pub_date"] or "",
        "ingest_at": src["ingest_at"] or now,
    }

    entry_key = hashlib.sha256(f"wx_doi|{doi}".encode()).hexdigest()
    row = conn.execute(
        "SELECT article_key, abstract, title FROM entries WHERE article_key=?",
        (entry_key,),
    ).fetchone()

    # v2.47 标题改为 DOI 对应文献标题（Crossref），来源微信推文信息只留在 mentions 摘要里。
    #   查询失败/无标题 → 回退源推文标题，不阻塞主扫描。
    lit_title = ""
    _meta = None
    try:
        from aes_workflow.meta_enrich import enrich_from_crossref
        _meta = enrich_from_crossref(doi, timeout=10.0)
        if _meta and _meta.get("title"):
            lit_title = _meta["title"].strip()
    except Exception:
        lit_title = ""
    if not lit_title:
        lit_title = mention["title"]

    if not row:
        mentions = [mention]
        # v2.47 条目卡片规范仿期刊源：标题/期刊/出版日期/作者取文献元数据，
        #   source_url = 文献原文链接（doi.org），推文信息只在 mentions 摘要。
        meta_fields = _meta or {}
        lit_url = meta_fields.get("source_url") or (f"https://doi.org/{doi}" if doi else (wechat_url or ""))
        conn.execute(
            """INSERT INTO entries
               (article_key, feed_id, ingest_source, title, journal, authors, doi,
                source_url, abstract, pub_date, meta_status, discovery_type,
                is_read, ingest_at, updated_at)
               VALUES (?, 'wx_doi', 'wechat_prefilter', ?, ?, ?, ?,
                       ?, ?, ?, 'meta_partial', 'wx_doi_entry',
                       0, ?, ?)""",
            (entry_key, lit_title, meta_fields.get("journal", ""),
             meta_fields.get("authors", ""), doi, lit_url,
             _json.dumps(mentions, ensure_ascii=False),
             meta_fields.get("pub_date", ""), now, now),
        )
        return "create"

    # 已有：卡片元数据一次性升级为文献元数据（旧条目仍是推文标题/空期刊时空日期）；
    #   mentions 追加。source_url 保留推文链接不动（提及溯源）。
    if _meta and (row["title"] != lit_title):
        conn.execute(
            """UPDATE entries SET title=?, journal=CASE WHEN journal='' OR journal IS NULL THEN ? ELSE journal END,
                   authors=CASE WHEN authors='' OR authors IS NULL THEN ? ELSE authors END,
                   pub_date=CASE WHEN pub_date='' OR pub_date IS NULL THEN ? ELSE pub_date END,
                   source_url=CASE WHEN source_url='' OR source_url IS NULL THEN ? ELSE source_url END
               WHERE article_key=?""",
            (lit_title, _meta.get("journal", ""), _meta.get("authors", ""),
             _meta.get("pub_date", ""), _meta.get("source_url", ""), entry_key),
        )

    # 已有：mentions 追加（按归一化 URL 去重）；重复命中仅前置时间不加注。
    # v2.40：微信链接 tempkey 是会话级参数，同文两次推送 URL 不同——归一化(去 tempkey
    #   及其后的 query/锚点)后再比对，防同文多 URL 重复加注。
    try:
        mentions = _json.loads(row["abstract"] or "[]")
        if not isinstance(mentions, list):
            mentions = []
    except Exception:
        mentions = []
    norm = _norm_wechat_url(mention["url"])
    if norm and any(_norm_wechat_url(m.get("url", "")) == norm for m in mentions):
        conn.execute(
            "UPDATE entries SET ingest_at=?, updated_at=? WHERE article_key=?",
            (now, now, entry_key),
        )
        return "noop"
    mentions.append(mention)
    conn.execute(
        "UPDATE entries SET abstract=?, ingest_at=?, updated_at=? WHERE article_key=?",
        (_json.dumps(mentions, ensure_ascii=False), now, now, entry_key),
    )
    return "update"


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

    # Tier 3: 文末参考文献反查（仅 微颗粒文献读书会Weekly JC——该号正文无明文 DOI，
    #   文献全在文末 refs 区；refs 全部 Crossref 反查，命中全部入库，不做主文献判定）
    ref_query_used = False
    if not ids and feed_name and (
        "weekly_jc" in feed_name.lower() or "微颗粒文献读书会" in feed_name
    ):
        ids = scan_references_for_dois(text)
        ref_query_used = bool(ids)

    if ids:
        update_entry_with_identifiers(conn, article_key, ids, source_url, feed_name)

    return {
        "status": "found" if ids else "no_id",
        "identifiers": ids,
        "ocr_used": ocr_used,
        "ref_query_used": ref_query_used,
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
