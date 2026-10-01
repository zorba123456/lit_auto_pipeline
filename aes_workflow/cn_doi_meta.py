"""中文 DOI（万方/chndoi 系）元数据反查（v2.54）。

背景：微信 DOI 条目里大量中文 DOI（10.3969/10.15909/10.19593 等）既不在
Crossref 也不在 yiigle(CMA)，标题只能回退推文标题。本模块补第三条查询链：

路线 A（纯 curl，首选）：doi.org → chndoi.org Resolution/Handler 页面，
HTML 内嵌「题名：」「作者：」「出版机构：」等字段，直接正则提取。
覆盖 chndoi 注册的 DOI（如 10.15909 中国美容医学）。

路线 B（headless chromium，兜底）：doi.org 302 → doi.wanfangdata.com.cn →
万方详情页（CSR），playwright 渲染后读 document.title
（格式「文章标题-期刊-万方数据知识服务平台」）。
覆盖万方自有注册的 DOI（如 10.3969）。速度慢（~6s/条），仅离线回填用，
不进实时扫描链路。

2026-09-14 实测：
- 10.3969/j.issn.1674-8468.2017.01.007 → 慢性光化性皮炎95例临床、光试验和光斑贴试验结果分析
- 10.15909/j.cnki.cn61-1347/r.007552 → CBCT评估隐形矫治器矫治骨性Ⅱ类错(牙合)畸形对颞下颌关节相关指标的影响
"""

import re
import subprocess
import urllib.parse

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)


def _chndoi_lookup(doi: str) -> dict | None:
    """路线 A：chndoi Handler 页面正则提取。纯 curl。"""
    url = f"https://www.chndoi.org/Resolution/Handler?doi={doi}"
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "15", "-A", _USER_AGENT, url],
            capture_output=True, text=True, timeout=20,
        )
        html = proc.stdout or ""
    except Exception:
        return None
    if "题名" not in html:
        return None

    def _field(label: str) -> str:
        m = re.search(rf"{label}：</label>\s*([^<\n]+)", html)
        return m.group(1).strip() if m else ""

    title = _field("题名")
    if not title:
        return None
    return {
        "title": title,
        "authors": _field("作者"),
        "publisher": _field("出版机构"),
        "source": "chndoi",
    }


def _wanfang_render_title(doi: str) -> str | None:
    """路线 B：doi.org → 万方详情页，headless 渲染读 title。慢（~6s），离线用。"""
    try:
        redir = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{redirect_url}",
             "--max-time", "15", f"https://doi.org/{doi}"],
            capture_output=True, text=True, timeout=20,
        ).stdout or ""
    except Exception:
        return None
    if "wanfangdata" not in redir:
        return None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page(user_agent=_USER_AGENT)
            pg.goto(redir, timeout=40000, wait_until="networkidle")
            pg.wait_for_timeout(2500)
            t = pg.title()
            b.close()
    except Exception:
        return None
    for sep in ("-期刊-万方数据", "-万方数据"):
        t = t.split(sep)[0]
    t = t.strip()
    if not t or "没有找到" in t or "出错" in t:
        return None
    # v2.86 万方反爬壳标题过滤：人机校验页/SPA 壳页 title 都是平台名，不是文献标题。
    #   不过滤会把「万方数据知识服务平台-科研学习全流程支持服务平台」当标题写进条目。
    if "万方" in t and ("知识服务平台" in t or "人机校验" in t or "科研学习" in t):
        return None
    return t


def cn_doi_search(doi: str) -> dict | None:
    """中文 DOI 反查入口：chndoi(纯curl) 优先，万方 headless 兜底。

    返回 {title, authors?, publisher?, source_url?, source}，未命中 None。
    """
    d = (doi or "").strip().strip("。）(;,，")
    if not d or " " in d:
        return None
    meta = _chndoi_lookup(d)
    if meta:
        meta["source_url"] = f"https://doi.org/{d}"
        return meta
    # v2.86 EBSCO 直构（gcd 库收录中国美容整形外科杂志等中文刊，全字段结构化）
    eb = ebsco_doi_search(d)
    if eb:
        return eb
    t = _wanfang_render_title(d)
    if t:
        return {
            "title": t,
            "source_url": f"https://doi.org/{d}",
            "source": "wanfang_render",
        }
    return None


# ── v2.86 第四链：引文反查（EBSCO 直构 + 引文页解析）──────────────
# 背景：万方 2026 上人机校验后，10.3969 系四条旧链全灭。实测两条免费新路：
#   A) EBSCO openurl contentitem 页按 DOI 直构 URL，免登录，__NEXT_DATA__
#      JSON 里 title/authors/jtitle/pubInfo 全字段结构化（gcd 数据库收录
#      中国美容整形外科杂志等）；标题弯引号有 mojibake（â€œ→“）需清洗。
#   B) Google 命中的引文页（期刊官网/PMC 等）参考文献行
#      「作者. 标题[J]. 期刊, 年, 卷(期): 页码. doi: <DOI>」正则解析。
# 搜索环节不入本模块（CLI 无代理连不上 googleapis）：调用方把
# web_search 命中的候选 URL 列表传给 citation_page_search。


def _fix_mojibake(s: str) -> str:
    """EBSCO 标题里 UTF-8 弯引号被二次编码成 â€œ/â€ 段，还原。"""
    for bad, good in (("â€œ", "“"), ("â€\x9d", "”"), ("â€˜", "‘"),
                      ("â€™", "’"), ("â€“", "–"), ("â€”", "—")):
        s = s.replace(bad, good)
    return s


def _curl_text(url: str, timeout: int = 15) -> str:
    try:
        # ⚠️ EBSCO 对完整 Chrome UA 返回壳页、对裸 "Mozilla/5.0" 返回真页（2026-10 实测），故用短 UA。
        proc = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout),
             "-A", "Mozilla/5.0", url],
            capture_output=True, timeout=timeout + 5,
        )
        return (proc.stdout or b"").decode("utf-8", errors="ignore")
    except Exception:
        return ""


def ebsco_doi_search(doi: str) -> dict | None:
    """路线 C：EBSCO openurl contentitem 按 DOI 直构，__NEXT_DATA__ 结构化元数据。

    URL 形态（2026-10 实测，编码错了拿到的是壳页）：
      path = contentitem/doi%3A<doi 双重 %编码>
      query = id=ebsco%3Adoi%3A<doi 单层 %编码>
    """
    d = (doi or "").strip()
    path = "doi%3A" + urllib.parse.quote(urllib.parse.quote(d, safe=""), safe="")
    query = "id=ebsco%3Adoi%3A" + urllib.parse.quote(d, safe="")
    html = _curl_text(f"https://openurl.ebsco.com/contentitem/{path}?{query}")
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        html, re.S,
    )
    if not m:
        return None
    try:
        import json
        item = (json.loads(m.group(1))
                .get("props", {}).get("pageProps", {}).get("data", {})
                .get("item") or {})
        info = item.get("itemInfo") or {}
        title = (info.get("title") or "").strip().rstrip(".")
        if not title or len(title) < 4:
            return None
        authors = item.get("authors") or []
        pub = item.get("pubInfo") or {}
        vol = pub.get("volume", "")
        iss = pub.get("issue", "")
        year = pub.get("year", "")
        return {
            "title": _fix_mojibake(title),
            "authors": "; ".join(str(a) for a in authors),
            "journal": info.get("jtitle", ""),
            "pub_date": f"{year}({vol}){iss}期" if year else "",
            "source": "ebsco",
        }
    except Exception:
        return None


# 引文行两形态（2026-10 实测）：
#   [J] 型（期刊官网/博客）：作者. 标题[J]. 期刊, 年, 卷(期): 页
#   PMC 型（pmc.ncbi.nlm.nih.gov）：编号. 作者, et al. 标题. 期刊. 年;卷(期):页
_CIT_J_RE = re.compile(
    r"(.{4,200}?)\[J\]\.?\s*"
    r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z&\s]{1,50}?)[,，]\s*(20\d{2})"
)
_CIT_PMC_RE = re.compile(
    r"(?:\d+\.\s*)?(.{4,200}?)\.\s*"
    r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z&\s]{1,50}?)\.\s*(20\d{2})\s*;"
)


def _clean_cit_title(t: str) -> str:
    t = t.strip().strip(" .。")
    m = re.search(r"(?:et al\.?|等)\.?\s*(.+)$", t)
    if m:
        t = m.group(1)
    # 编号前缀
    t = re.sub(r"^\[?\d+\]?\s*", "", t)
    return t.strip()


def citation_page_search(urls: list[str], doi: str) -> dict | None:
    """路线 D：抓引文页，在参考文献区找含该 DOI 的行，解析标题/期刊/年。

    urls：调用方（搜索环节）给的候选页；逐页抓取，命中即返。
    """
    d = (doi or "").strip()
    for u in urls:
        html = _curl_text(u, timeout=12)
        if not html or d not in html:
            continue
        # 该页本身即文章页（canonical=DOI 或 URL 含 DOI）：<title> 就是文献标题
        canon = re.search(r'<link rel="canonical" href="[^"]*%s[^"]*"' % re.escape(d), html)
        if canon or u.rstrip("/").endswith(d):
            tm = re.search(r"<title>([^<]+)</title>", html)
            if tm and len(tm.group(1).strip()) >= 4:
                return {
                    "title": tm.group(1).strip(),
                    "journal": "",
                    "source": "article_page",
                }
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        i = text.find(d)
        seg = text[max(0, i - 450):i]
        # ⚠️ 窗口内可能含多条引文，倒序取最后一条（紧邻目标 DOI 的才是它的引文行）
        for m in list(_CIT_J_RE.finditer(seg))[::-1]:
            title = _clean_cit_title(m.group(1).split(".")[-1])
            if len(title) >= 4:
                return {
                    "title": title,
                    "journal": m.group(2).strip(),
                    "pub_date": m.group(3),
                    "source": "citation_page",
                }
        for m in list(_CIT_PMC_RE.finditer(seg))[::-1]:
            title = _clean_cit_title(m.group(1))
            if len(title) >= 4:
                return {
                    "title": title,
                    "journal": m.group(2).strip(),
                    "pub_date": m.group(3),
                    "source": "citation_page",
                }
    return None
