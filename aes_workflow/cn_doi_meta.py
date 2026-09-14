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
    t = _wanfang_render_title(d)
    if t:
        return {
            "title": t,
            "source_url": f"https://doi.org/{d}",
            "source": "wanfang_render",
        }
    return None
