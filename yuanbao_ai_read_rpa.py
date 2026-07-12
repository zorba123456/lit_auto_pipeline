#!/usr/bin/env python3
"""元宝 AI 阅读 RPA：上传 PDF → 逐 tab 验收 → 分享复制 deep-reading-detail 链。

产物格式（非 yb.tencent.com/s/ 对话卡）：
  https://yuanbao.tencent.com/bot/app/share/deep-reading-detail/{id}?convIndex=…&mediaId=…

策略：逐 tab 点击检查；见「读取失败/重试」立即 DOM click「重试」（不用 pyautogui）；
点不中或仍失败则刷新。账号冻结时整条链暂停。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import time
from urllib.parse import parse_qs, urlparse

import pyautogui
import pyperclip
from playwright.async_api import Page, async_playwright

YUANBAO_HOME = "https://yuanbao.tencent.com/"
DEEP_READING_SHARE_RE = re.compile(
    r"https?://yuanbao\.tencent\.com/bot/app/share/deep-reading-detail/\S+"
)
CHAT_SHARE_RE = re.compile(r"https?://yb\.tencent\.com/s/\S+")
# 五个 tab：英/中标签；Original 在部分 UI 仅为左侧 PDF 区，无顶栏 tab
TAB_SPECS: list[tuple[str, ...]] = [
    ("总结", "Summarization"),
    ("精读", "Intensive Reading"),
    ("翻译", "Translate", "Translation"),
    ("脑图", "Mind Map"),
]
OPTIONAL_TAB_LABELS = ("原文", "Original")
LOAD_ERROR_RE = re.compile(
    r"Failed to load|Tap to retry|加载失败|请重试|读取失败|点击重试",
    re.I,
)
SHARE_BLOCK_RE = re.compile(
    r"无法分享|正在生成中|cannot be shared|being generated",
    re.I,
)
MINDMAP_BUSY_RE = re.compile(
    r"Mind Map is being generated|being generated and cannot be shared|"
    r"脑图.*生成|正在生成.*脑图|精读.*脑图.*生成",
    re.I,
)
MAX_TAB_REFRESH = 5
# 上传/解析阶段拦截到的 mediaId（分享 API 常需此字段）
_session_media_id: str = ""


class _RetryOutcome:
    FIXED = "fixed"
    NEED_REFRESH = "need_refresh"
    NO_ERROR = "no_error"


def _ensure_profile_available(profile: str) -> None:
    profile_abs = os.path.abspath(profile)
    try:
        subprocess.run(
            ["pkill", "-f", f"user-data-dir={profile_abs}"],
            check=False,
            capture_output=True,
        )
        time.sleep(1.5)
    except Exception:
        pass


async def _install_page_hooks(page: Page) -> None:
    """剪贴板 hook + 全程 mediaId 嗅探。"""

    async def on_response(response):
        global _session_media_id
        try:
            url = response.url.lower()
            if not any(k in url for k in ("media", "share", "deep-reading", "upload", "file")):
                return
            body = await response.text()
            for pat in (
                r'"mediaId"\s*:\s*"([^"]+)"',
                r'"media_id"\s*:\s*"([^"]+)"',
                r"mediaId=([a-f0-9]{20,}[_\w]*)",
            ):
                m = re.search(pat, body, re.I)
                if m and m.group(1):
                    _session_media_id = m.group(1)
                    return
        except Exception:
            pass

    page.on("response", on_response)
    await page.add_init_script(
        """
        window.__aes_clipboard_link = "";
        const orig = navigator.clipboard.writeText;
        navigator.clipboard.writeText = async function(text) {
            window.__aes_clipboard_link = text;
            return orig.apply(this, arguments);
        };
        try {
            localStorage.setItem("hyc-client-lang", "zh-CN");
            localStorage.setItem("clientLang", "zh-CN");
            localStorage.setItem("yb-lang", "zh-CN");
            document.documentElement.lang = "zh-CN";
        } catch (e) {}
        """
    )


async def _apply_zh_locale(page: Page) -> None:
    """Playwright locale + 页面内语言偏好（英文 UI 时侧栏无 AI 阅读）。"""
    await page.evaluate(
        """() => {
            try {
                localStorage.setItem("hyc-client-lang", "zh-CN");
                localStorage.setItem("clientLang", "zh-CN");
                localStorage.setItem("yb-lang", "zh-CN");
                document.documentElement.lang = "zh-CN";
            } catch (e) {}
        }"""
    )


def _is_valid_share_link(link: str) -> bool:
    return bool(DEEP_READING_SHARE_RE.search(link))


YUANBAO_MAIN_AGENT = "naQivTmsDa"
YUANBAO_AI_READ_AGENT = "ddk4eQR3ap"
MAX_NAV_RETRIES = 5
# 直达书签（不依赖侧栏）；英文 UI 侧栏常无 AI Reading
YUANBAO_AI_READ_ENTRIES = (
    "https://yuanbao.tencent.com/chat/ddk4eQR3ap/"
    "e6831558-5e4d-4fa0-9ac6-7de084b1b6aa?from=chat&lang=zh-CN",
    f"https://yuanbao.tencent.com/chat/{YUANBAO_AI_READ_AGENT}?from=chat&lang=zh-CN",
    "https://yuanbao.tencent.com/tool/deep-reading?lang=zh-CN",
)
# 兼容旧名
YUANBAO_AI_READ_ENTRY = YUANBAO_AI_READ_ENTRIES[0]


async def _is_ai_read_upload_page(page: Page) -> bool:
    """严格判断：须见上传区或 file input。"""
    if await page.locator('input[type="file"]').count() > 0:
        return True
    body = await page.evaluate("() => document.body.innerText || ''")
    if any(
        x in body
        for x in (
            "拖拽文件",
            "Drag and drop",
            "Drag file",
            "drop file",
            "Upload local",
            "上传本地",
        )
    ):
        return True
    if ("本地文件" in body or "Local Files" in body or "Local files" in body) and (
        "上传" in body or "Upload" in body
    ):
        return True
    url = page.url
    if YUANBAO_AI_READ_AGENT in url and "e6831558" in url:
        return True
    return False


def _is_wrong_main_chat(url: str) -> bool:
    """英文主对话页 naQivTmsDa — 不是 AI 阅读。"""
    return YUANBAO_MAIN_AGENT in url and YUANBAO_AI_READ_AGENT not in url


def _is_yuanbao_home(url: str) -> bool:
    path = urlparse(url).path.rstrip("/") or "/"
    if _is_wrong_main_chat(url):
        return True
    return path in ("/", "/chat") and YUANBAO_AI_READ_AGENT not in url


async def _click_sidebar_ai_read(page: Page) -> bool:
    for label in ("AI 阅读", "AI阅读", "AI Reading"):
        loc = page.get_by_text(label, exact=True)
        if await loc.count() > 0:
            print(f"   👆 侧栏点击「{label}」…")
            await loc.first.click(timeout=10000)
            await page.wait_for_timeout(3000)
            return True
    return False


async def _open_via_all_agents(page: Page) -> bool:
    """英文 UI：侧栏无 AI 阅读 → All Agents 里找。"""
    for nav in ("All Agents", "全部智能体", "所有智能体"):
        btn = page.get_by_text(nav, exact=True)
        if await btn.count() > 0:
            print(f"   👆 打开「{nav}」…")
            await btn.first.click(timeout=8000)
            await page.wait_for_timeout(2500)
            break
    else:
        return False

    for label in ("AI Reading", "AI 阅读", "AI阅读", "Deep Reading"):
        card = page.get_by_text(label, exact=False)
        if await card.count() > 0:
            print(f"   👆 选择 agent「{label}」…")
            await card.first.click(timeout=10000)
            await page.wait_for_timeout(3000)
            return True
    return False


async def _open_via_tool_menu(page: Page) -> bool:
    """英文主对话页：Tool 下拉里可能有 AI Reading。"""
    tool = page.get_by_text(re.compile(r"^Tool$", re.I))
    if await tool.count() == 0:
        tool = page.get_by_role("button", name=re.compile(r"Tool", re.I))
    if await tool.count() == 0:
        return False
    print("   👆 打开 Tool 菜单…")
    await tool.first.click(timeout=8000)
    await page.wait_for_timeout(1500)
    for label in ("AI Reading", "AI 阅读", "Document", "Read"):
        item = page.get_by_text(label, exact=False)
        if await item.count() > 0:
            await item.first.click(timeout=8000)
            await page.wait_for_timeout(3000)
            return True
    return False


async def _goto_ai_read_entry(page: Page, url: str) -> None:
    sep = "&" if "?" in url else "?"
    if "lang=" not in url:
        url = f"{url}{sep}lang=zh-CN"
    print(f"   → {url[:90]}…")
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await _apply_zh_locale(page)
    await page.wait_for_timeout(3000)
    if _is_wrong_main_chat(page.url):
        print(f"   ⚠️ 被重定向到主对话: {page.url[:80]}")


async def navigate_to_ai_read(page: Page, *, entry: str = "direct") -> None:
    """进入 AI 阅读上传页。英文 UI 不靠侧栏，优先直达 agent URL。"""
    print("📖 进入 AI 阅读（直达 agent，不依赖侧栏）…")

    if entry == "home":
        await page.goto(YUANBAO_HOME, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(2000)

    for attempt in range(1, MAX_NAV_RETRIES + 1):
        entry_url = YUANBAO_AI_READ_ENTRIES[(attempt - 1) % len(YUANBAO_AI_READ_ENTRIES)]
        await _goto_ai_read_entry(page, entry_url)

        if await _is_ai_read_upload_page(page):
            print(f"✅ 已进入 AI 阅读上传页 ({page.url[:80]})")
            return

        url = page.url
        print(f"⚠️ [{attempt}/{MAX_NAV_RETRIES}] 未在上传页: {url[:90]}")

        if await _click_sidebar_ai_read(page) and await _is_ai_read_upload_page(page):
            print(f"✅ 侧栏进入上传页 ({page.url[:80]})")
            return
        if await _open_via_all_agents(page) and await _is_ai_read_upload_page(page):
            print(f"✅ All Agents 进入上传页 ({page.url[:80]})")
            return
        if await _open_via_tool_menu(page) and await _is_ai_read_upload_page(page):
            print(f"✅ Tool 菜单进入上传页 ({page.url[:80]})")
            return

        # 再试一次直达（有时需二次 goto）
        await _goto_ai_read_entry(page, YUANBAO_AI_READ_ENTRIES[0])
        if await _is_ai_read_upload_page(page):
            print(f"✅ 已进入 AI 阅读上传页 ({page.url[:80]})")
            return

    body_snip = (await page.evaluate("() => document.body.innerText.slice(0, 200)")) or ""
    raise RuntimeError(
        f"未进入 AI 阅读上传页（当前 {page.url[:80]}）。"
        f"英文 UI 请确认 profile 已登录；或手动打开书签 URL 后再跑。body={body_snip!r}"
    )


async def upload_pdf(page: Page, pdf_path: str) -> None:
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)
    basename = os.path.basename(pdf_path)
    print(f"📄 上传 PDF: {basename}")

    fi = page.locator('input[type="file"]')
    if await fi.count() > 0:
        await fi.first.set_input_files(pdf_path)
        print("⏳ 等待 deep-reading 页加载…")
        return

    async with page.expect_file_chooser(timeout=25000) as fc_info:
        clicked = False
        for label in (
            "本地文件",
            "Local Files",
            "Local files",
            "上传本地文件",
            "上传本地",
            "Local file",
        ):
            item = page.get_by_text(label, exact=True)
            if await item.count() > 0:
                await item.first.click(timeout=5000)
                clicked = True
                break
        if not clicked:
            for label in ("本地文件", "Local Files", "上传"):
                item = page.get_by_text(label, exact=False)
                if await item.count() > 0:
                    await item.first.click(timeout=5000)
                    clicked = True
                    break
        if not clicked:
            zone = page.get_by_text(re.compile(r"拖拽文件|Drag and drop|Drag file", re.I))
            if await zone.count() > 0:
                await zone.first.click(timeout=5000)
                clicked = True
        if not clicked:
            body = (await page.evaluate("() => document.body.innerText.slice(0, 300)")) or ""
            raise RuntimeError(f"未找到上传入口; body={body!r}")
        fc = await fc_info.value
        await fc.set_files(pdf_path)

    print("⏳ 等待 deep-reading 页加载…")


async def _on_deep_reading_page(page: Page) -> bool:
    return "tool/deep-reading/detail" in page.url


async def _safe_refresh_deep_reading(page: Page) -> None:
    """刷新但保留 deep-reading URL（避免跳回 chat 首页）。"""
    url = page.url
    if "tool/deep-reading/detail" in url and "cid=" in url:
        print(f"🔄 刷新 deep-reading 页…")
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    else:
        print("🔄 reload 当前页…")
        await page.reload(wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(6000)


async def wait_for_deep_reading_page(page: Page, *, timeout_sec: int = 180) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if await _on_deep_reading_page(page):
            return True
        await page.wait_for_timeout(3000)
    return False


async def _any_content_tab_visible(page: Page) -> bool:
    for labels in TAB_SPECS:
        if await _find_tab(page, labels):
            return True
    return False


async def _find_tab(page: Page, labels: tuple[str, ...]):
    """仅在顶栏 tab 区域查找，避免点到正文里的同名文字。"""
    for label in labels:
        by_role = page.get_by_role("tab", name=label, exact=True)
        if await by_role.count() > 0:
            return by_role.first

        tablist = page.locator("[role='tablist']")
        if await tablist.count() > 0:
            in_list = tablist.first.get_by_text(label, exact=True)
            if await in_list.count() > 0:
                return in_list.first

        # 右栏分析区顶部的 tab 行（常见 class 片段）
        bar = page.locator(
            "[class*='deep-reading'] [class*='tab'], "
            "[class*='reading-detail'] [class*='tab'], "
            "[class*='TabBar'], [class*='tab-bar'], [class*='tabBar']"
        )
        if await bar.count() > 0:
            hit = bar.filter(has_text=re.compile(f"^{re.escape(label)}$", re.I))
            if await hit.count() > 0:
                return hit.first

        # 兜底：可见 tab，排除分享条等同名按钮
        loc = page.get_by_text(label, exact=True)
        n = await loc.count()
        for i in range(n):
            el = loc.nth(i)
            try:
                if not await el.is_visible():
                    continue
                bad = await el.evaluate(
                    """el => {
                        let n = el;
                        for (let i = 0; i < 10 && n; i++) {
                            const c = (n.className || '') + '';
                            if (c.includes('share-bar') || c.includes('tool-selection__bar')
                                || c.includes('share_bar')) return true;
                            n = n.parentElement;
                        }
                        return false;
                    }"""
                )
                if bad:
                    continue
                box = await el.bounding_box()
                if box and box["y"] < 220 and box["x"] > 300:
                    return el
            except Exception:
                continue
    return None


async def _read_tab_panel_text(page: Page) -> str:
    return await page.evaluate(
        """() => {
            const w = window.innerWidth;
            const pick = document.elementFromPoint(Math.floor(w * 0.75), Math.floor(window.innerHeight * 0.5));
            let node = pick;
            for (let i = 0; i < 15 && node; i++) {
                const r = node.getBoundingClientRect?.();
                const t = (node.innerText || "").trim();
                if (r && r.left > w * 0.4 && t.length > 30) return t.slice(0, 3500);
                node = node.parentElement;
            }
            return (document.body.innerText || "").slice(0, 3500);
        }"""
    )


async def _top_banner_text(page: Page) -> str:
    return await page.evaluate(
        """() => {
            let parts = [];
            for (const sel of ['[class*="toast"]', '[class*="message"]', '[class*="notice"]', '[class*="banner"]', '[class*="Tips"]']) {
                document.querySelectorAll(sel).forEach(el => {
                    const t = (el.innerText || "").trim();
                    if (t) parts.push(t);
                });
            }
            parts.push((document.body.innerText || "").slice(0, 500));
            return parts.join(" ");
        }"""
    )


async def _share_blocked_reason(page: Page) -> str | None:
    text = await _top_banner_text(page)
    m = SHARE_BLOCK_RE.search(text) or MINDMAP_BUSY_RE.search(text)
    return m.group(0) if m else None


async def _extract_media_id(page: Page) -> str:
    return await page.evaluate(
        """() => {
            const u = new URL(location.href);
            const q = u.searchParams.get('mediaId');
            if (q) return q;
            const html = document.documentElement.innerHTML;
            const patterns = [
                /mediaId[=:]["']?([a-f0-9]{20,}[_\\w]*)/i,
                /"mediaId"\\s*:\\s*"([^"]+)"/,
                /media_id['":\\s]+([a-f0-9]{20,}[_\\w]*)/i,
            ];
            for (const p of patterns) {
                const m = html.match(p);
                if (m && m[1]) return m[1];
            }
            return '';
        }"""
    )


async def _mindmap_tab_ok(page: Page) -> tuple[bool, str]:
    tab = await _find_tab(page, ("脑图", "Mind Map"))
    if tab is None:
        return False, "脑图 tab 未出现"
    try:
        await tab.click(timeout=8000, force=True)
        await page.wait_for_timeout(3000)
    except Exception as exc:
        return False, f"脑图点击失败: {exc}"
    text = await _read_tab_panel_text(page)
    if "读取失败" in text or LOAD_ERROR_RE.search(text):
        return False, f"脑图: {LOAD_ERROR_RE.search(text).group(0) if LOAD_ERROR_RE.search(text) else '读取失败'}"
    if len(text.strip()) < 40:
        return False, "脑图: 内容未加载"
    return True, "ok"


async def _find_retry_in_panel(page: Page):
    """右栏「读取失败 点击重试」— 可点的是「重试」（DOM link/button）。"""
    vw = await page.evaluate("() => window.innerWidth") or 1200
    min_x = vw * 0.38

    async def _in_right_panel(locator) -> bool:
        try:
            if await locator.count() == 0:
                return False
            el = locator.first
            if not await el.is_visible():
                return False
            box = await el.bounding_box()
            return bool(box and box["x"] >= min_x)
        except Exception:
            return False

    candidates = (
        page.get_by_role("link", name="重试"),
        page.get_by_role("button", name=re.compile(r"^(重试|Retry)$", re.I)),
        page.get_by_text("重试", exact=True),
        page.get_by_text(re.compile(r"^Tap to retry$", re.I)),
        page.locator("a:has-text('重试')"),
        page.locator("button:has-text('重试')"),
    )
    for loc in candidates:
        if not await _in_right_panel(loc):
            continue
        return loc.first

    # 「读取失败 … 重试」同一行
    fail = page.get_by_text(re.compile(r"读取失败"))
    if await fail.count() > 0:
        row = fail.first.locator("xpath=..")
        retry = row.get_by_text("重试", exact=True)
        if await _in_right_panel(retry):
            return retry.first
    return None


async def _click_retry_in_panel(page: Page, tab_name: str) -> bool:
    """Playwright DOM click「重试」；不用鼠标/pyautogui。"""
    btn = await _find_retry_in_panel(page)
    if btn is None:
        print(f"   ❌ {tab_name} 未找到「重试」")
        return False
    print(f"   🔁 {tab_name} 读取失败 → DOM click「重试」…")
    try:
        await btn.scroll_into_view_if_needed()
        await btn.click(timeout=5000, force=True)
        return True
    except Exception as exc:
        print(f"   ❌ DOM click 重试失败: {exc}")
        return False


async def _try_retry_failed_tab(page: Page, tab_name: str) -> str:
    """脑图/精读读取失败：点「重试」；点不中或仍失败 → NEED_REFRESH。"""
    if tab_name not in ("脑图", "Mind Map", "精读", "Intensive Reading"):
        return _RetryOutcome.NO_ERROR

    text = await _read_tab_panel_text(page)
    if "读取失败" not in text and not LOAD_ERROR_RE.search(text):
        return _RetryOutcome.NO_ERROR

    if not await _click_retry_in_panel(page, tab_name):
        return _RetryOutcome.NEED_REFRESH

    await page.wait_for_timeout(8000)
    text2 = await _read_tab_panel_text(page)
    if "读取失败" in text2 or LOAD_ERROR_RE.search(text2):
        print(f"   ❌ {tab_name} 重试后仍失败 → 刷新")
        return _RetryOutcome.NEED_REFRESH
    print(f"   ✅ {tab_name} 重试后恢复")
    return _RetryOutcome.FIXED


async def _tab_body_error(page: Page, tab_name: str) -> str | None:
    text = await _read_tab_panel_text(page)
    m = LOAD_ERROR_RE.search(text)
    if m:
        return m.group(0)
    if tab_name in ("脑图", "Mind Map") and MINDMAP_BUSY_RE.search(text):
        return MINDMAP_BUSY_RE.search(text).group(0)
    return None


async def verify_all_tabs(page: Page) -> tuple[bool, str]:
    """逐 tab 点击验收；必须点完 4 个 tab，不因前一个误报提前停。"""
    for label in OPTIONAL_TAB_LABELS:
        tab = await _find_tab(page, (label,))
        if tab:
            try:
                print(f"   📑 tab → {label}")
                await tab.click(timeout=5000)
                await page.wait_for_timeout(1200)
            except Exception:
                pass
            break

    errors: list[str] = []
    for labels in TAB_SPECS:
        name = labels[0]
        tab = await _find_tab(page, labels)
        if tab is None:
            visible = []
            for ls in TAB_SPECS:
                t = await _find_tab(page, ls)
                if t:
                    visible.append(ls[0])
            return False, f"tab 未出现: {name}（已见: {visible or '无'}）"
        try:
            print(f"   📑 tab → {name}")
            await tab.scroll_into_view_if_needed()
            await tab.click(timeout=8000, force=True)
            await page.wait_for_timeout(2200)
        except Exception as exc:
            return False, f"{name} 点击失败: {exc}"

        # 一切到 tab 若已见读取失败，立即点重试（不等后续轮询）
        panel = await _read_tab_panel_text(page)
        if "读取失败" in panel or LOAD_ERROR_RE.search(panel or ""):
            outcome = await _try_retry_failed_tab(page, name)
            if outcome == _RetryOutcome.NEED_REFRESH:
                return False, f"{name}: 读取失败|immediate_refresh"
            if outcome == _RetryOutcome.FIXED:
                panel = await _read_tab_panel_text(page)

        err = await _tab_body_error(page, name)
        if err:
            outcome = await _try_retry_failed_tab(page, name)
            if outcome == _RetryOutcome.NEED_REFRESH:
                return False, f"{name}: 读取失败|immediate_refresh"
            if outcome == _RetryOutcome.FIXED:
                err = await _tab_body_error(page, name)
                if not err:
                    continue
            errors.append(f"{name}: {err}")

    if errors:
        return False, "; ".join(errors)
    return True, "ok"


async def _find_share_control(page: Page):
    for loc in (
        page.get_by_role("button", name=re.compile(r"^(分享|Share)$", re.I)),
        page.get_by_text(re.compile(r"^(分享|Share)$"), exact=True),
        page.locator("[aria-label='分享'], [aria-label='Share']"),
    ):
        if await loc.count() > 0:
            return loc.last
    return None


async def _share_button_enabled(page: Page) -> bool:
    if not await _on_deep_reading_page(page):
        return False

    blocked = await _share_blocked_reason(page)
    if blocked:
        return False

    btn = await _find_share_control(page)
    if btn is None:
        return False
    try:
        if await btn.is_disabled():
            return False
    except Exception:
        pass
    try:
        grey = await btn.evaluate(
            """el => {
                const s = getComputedStyle(el);
                return el.disabled || el.getAttribute('aria-disabled') === 'true'
                    || s.pointerEvents === 'none' || parseFloat(s.opacity) < 0.55;
            }"""
        )
        if grey:
            return False
    except Exception:
        pass
    return True


async def wait_for_ai_read_ready(
    page: Page,
    pdf_basename: str,
    *,
    pdf_path: str | None = None,
    entry: str = "direct",
    timeout_sec: int = 600,
    debug: bool = False,
) -> None:
    """逐 tab 验收；tab 异常则刷新；全通过且 Share 可点才继续。"""
    deadline = time.monotonic() + timeout_sec
    refresh_count = 0
    poll = 0
    home_stuck = 0

    if not await wait_for_deep_reading_page(page, timeout_sec=min(180, timeout_sec)):
        raise TimeoutError("上传后 180s 内未进入 tool/deep-reading/detail")

    while time.monotonic() < deadline:
        poll += 1

        if not await _on_deep_reading_page(page):
            if _is_yuanbao_home(page.url) or _is_wrong_main_chat(page.url):
                home_stuck += 1
            else:
                home_stuck = 0

            if home_stuck >= 3 and pdf_path:
                print("🔄 落在首页/非阅读页 → 重新进入 AI 阅读并上传…")
                await navigate_to_ai_read(page, entry=entry)
                await upload_pdf(page, pdf_path)
                home_stuck = 0
                poll = 0
                if not await wait_for_deep_reading_page(page, timeout_sec=120):
                    continue
                continue

            if poll % 5 == 1:
                print(f"   …poll {poll}: 等待 deep-reading 页… url={page.url[:70]}")
            await page.wait_for_timeout(4000)
            continue

        if not await _any_content_tab_visible(page):
            if poll % 5 == 1:
                print(f"   …poll {poll}: 等待 tab 栏…")
            await page.wait_for_timeout(4000)
            continue

        tabs_ok, tab_reason = await verify_all_tabs(page)
        share_ok = await _share_button_enabled(page)
        blocked = await _share_blocked_reason(page)

        if poll % 3 == 1:
            print(
                f"   …poll {poll}: tabs_ok={tabs_ok} share={share_ok} "
                f"banner={blocked or '-'} refresh={refresh_count}/{MAX_TAB_REFRESH} "
                f"reason={tab_reason if not tabs_ok else 'ok'}"
            )

        if not tabs_ok:
            immediate = "immediate_refresh" in tab_reason
            is_content_error = ":" in tab_reason and "tab 未出现" not in tab_reason
            if (immediate or is_content_error) and refresh_count < MAX_TAB_REFRESH:
                refresh_count += 1
                why = "点不中重试" if immediate else tab_reason
                print(f"🔄 tab 异常 ({why}) → 立即刷新 ({refresh_count}/{MAX_TAB_REFRESH})…")
                await _safe_refresh_deep_reading(page)
            else:
                await page.wait_for_timeout(5000)
            continue

        if blocked or not share_ok:
            if poll % 6 == 0 and refresh_count < MAX_TAB_REFRESH:
                refresh_count += 1
                why = blocked or "Share 仍灰"
                print(f"🔄 {why} → 刷新 ({refresh_count}/{MAX_TAB_REFRESH})…")
                await _safe_refresh_deep_reading(page)
            else:
                await page.wait_for_timeout(5000)
            continue

        if tabs_ok and share_ok:
            mm_ok, mm_reason = await _mindmap_tab_ok(page)
            if not mm_ok:
                print(f"   …脑图复检未过: {mm_reason}")
                outcome = await _try_retry_failed_tab(page, "脑图")
                if outcome == _RetryOutcome.FIXED:
                    mm_ok, mm_reason = await _mindmap_tab_ok(page)
                elif outcome == _RetryOutcome.NEED_REFRESH:
                    mm_ok = False
                if not mm_ok:
                    if refresh_count < MAX_TAB_REFRESH:
                        refresh_count += 1
                        print(f"🔄 脑图未就绪 ({mm_reason}) → 立即刷新…")
                        await _safe_refresh_deep_reading(page)
                    await page.wait_for_timeout(3000)
                    continue

            await page.wait_for_timeout(2000)
            tabs_ok2, tab_reason2 = await verify_all_tabs(page)
            mm_ok2, _ = await _mindmap_tab_ok(page)
            if tabs_ok2 and mm_ok2 and await _share_button_enabled(page) and not await _share_blocked_reason(page):
                print("✅ 全 tab + 脑图通过 + Share 可点")
                return

        await page.wait_for_timeout(5000)

    if debug:
        os.makedirs("logs", exist_ok=True)
        await page.screenshot(path="logs/yuanbao_ai_read_timeout.png", full_page=True)
        print("📸 超时截图: logs/yuanbao_ai_read_timeout.png")

    tabs_ok, _ = await verify_all_tabs(page)
    if await _share_button_enabled(page):
        print("⚠️ 超时但 Share 可点，尝试分享")
        return
    raise TimeoutError(f"AI 阅读超时（>{timeout_sec}s）：全 tab 未就绪或 Share 不可点")


def _parse_deep_reading_page(url: str) -> dict[str, str]:
    qs = parse_qs(urlparse(url).query)
    return {
        "cid": (qs.get("cid") or [""])[0],
        "agent_id": (qs.get("agentId") or ["ddk4eQR3ap"])[0],
        "conv_index": (qs.get("convIndex") or ["2"])[0],
        "speech_index": (qs.get("speechIndex") or ["0"])[0],
    }


def _build_deep_reading_share_url(
    share_id: str, *, conv_index: str, speech_index: str, media_id: str
) -> str:
    base = f"https://yuanbao.tencent.com/bot/app/share/deep-reading-detail/{share_id}"
    qs = f"convIndex={conv_index}&speechIndex={speech_index}"
    if media_id:
        qs += f"&mediaId={media_id}"
    return f"{base}?{qs}"


async def _click_element_pyautogui(page: Page, locator) -> None:
    coords = await locator.evaluate(
        """el => {
            const r = el.getBoundingClientRect();
            return {
                x: window.screenX + r.left + r.width / 2,
                y: window.screenY + (window.outerHeight - window.innerHeight) + r.top + r.height / 2
            };
        }"""
    )
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
    await asyncio.sleep(0.6)
    ox, oy = pyautogui.position()
    pyautogui.moveTo(coords["x"], coords["y"], duration=0.2)
    pyautogui.click()
    pyautogui.moveTo(ox, oy, duration=0.2)


async def _click_copy_with_pyautogui(page: Page, locator) -> str:
    coords = await locator.evaluate(
        """el => {
            const r = el.getBoundingClientRect();
            return {
                x: window.screenX + r.left + r.width / 2,
                y: window.screenY + (window.outerHeight - window.innerHeight) + r.top + r.height / 2
            };
        }"""
    )
    pyperclip.copy("")
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
    await asyncio.sleep(0.8)
    ox, oy = pyautogui.position()
    pyautogui.moveTo(coords["x"], coords["y"], duration=0.2)
    pyautogui.click()
    pyautogui.moveTo(ox, oy, duration=0.2)
    await asyncio.sleep(1.5)
    hook = await page.evaluate("() => window.__aes_clipboard_link || ''")
    clip = pyperclip.paste()
    for link in (hook, clip):
        if link and _is_valid_share_link(link):
            return link.strip()
        if link and CHAT_SHARE_RE.search(link):
            print(f"⚠️ 剪贴板是对话短链，忽略: {link[:55]}…")
    return ""


async def _resolve_media_id(page: Page) -> str:
    global _session_media_id
    if _session_media_id:
        return _session_media_id
    mid = await _extract_media_id(page)
    if mid:
        _session_media_id = mid
    return mid or ""


def _link_from_share_payload(data: dict, page_url: str, *, fallback_media: str = "") -> str | None:
    target = (data.get("targetUrl") or "").strip()
    if target and "deep-reading-detail" in target:
        return target
    meta = _parse_deep_reading_page(page_url)
    sid = data.get("shareId") or ""
    media_id = data.get("mediaId") or fallback_media or ""
    if sid and media_id:
        return _build_deep_reading_share_url(
            sid,
            conv_index=meta["conv_index"],
            speech_index=meta["speech_index"],
            media_id=media_id,
        )
    return None


async def _scrape_link_from_dom(page: Page) -> str:
    found = await page.evaluate(
        """() => {
            for (const inp of document.querySelectorAll('input')) {
                const v = inp.value || '';
                if (v.includes('deep-reading-detail')) return v;
            }
            for (const a of document.querySelectorAll('a[href*="deep-reading-detail"]')) {
                if (a.href) return a.href;
            }
            const html = document.documentElement.innerHTML;
            const m = html.match(/https:\\/\\/yuanbao\\.tencent\\.com\\/bot\\/app\\/share\\/deep-reading-detail\\/[^"'\\s<>]+/);
            return m ? m[0] : '';
        }"""
    )
    return found.strip() if found and _is_valid_share_link(found) else ""


async def _js_click_copy_link(page: Page) -> str:
    clicked = await page.evaluate(
        """() => {
            const ok = (t) => /^(复制链接|Copy link|Copy Link|复制)$/i.test((t || '').trim());
            for (const n of document.querySelectorAll('button, div, span, a, li')) {
                if (!ok(n.innerText)) continue;
                const r = n.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) continue;
                n.click();
                return n.innerText.trim();
            }
            return '';
        }"""
    )
    if clicked:
        await page.wait_for_timeout(1200)
        hook = await page.evaluate("() => window.__aes_clipboard_link || ''")
        if hook and _is_valid_share_link(hook):
            return hook.strip()
        clip = pyperclip.paste()
        if clip and _is_valid_share_link(clip):
            return clip.strip()
    return ""


async def _link_from_captured(captured: list[dict], page: Page) -> str | None:
    fallback = await _resolve_media_id(page)
    for item in captured:
        try:
            data = json.loads(item["body"])
            link = _link_from_share_payload(data, page.url, fallback_media=fallback)
            if link:
                return link
        except (json.JSONDecodeError, TypeError):
            continue
    return None


async def _click_tool_selection_copy(page: Page) -> str:
    """AI 阅读 Share 弹层：agent-tool-selection__bar-item（非 chat share-bar）。"""
    items = page.locator(
        ".agent-tool-selection__bar-item, [class*='tool-selection__bar-item']"
    )
    n = await items.count()
    for i in range(n):
        el = items.nth(i)
        try:
            label = (await el.inner_text()).strip()
        except Exception:
            label = ""
        if label and not re.search(r"复制|copy|链接|link", label, re.I):
            continue
        print(f"   👆 tool-selection 复制项: {label!r}")
        link = await _click_copy_with_pyautogui(page, el)
        if link:
            return link
    if n > 0:
        print(f"   👆 tool-selection 首项 (共{n}个)…")
        link = await _click_copy_with_pyautogui(page, items.first)
        if link:
            return link
    return ""


async def _wait_share_link_after_click(page: Page, captured: list[dict], *, wait_sec: int = 30) -> str:
    """Share 点击后：轮询拦截响应 + DOM + UI 复制（不重复打 API）。"""
    deadline = time.monotonic() + wait_sec
    while time.monotonic() < deadline:
        link = await _link_from_captured(captured, page)
        if link:
            print(f"✅ 拦截 share 响应: {link[:75]}…")
            return link

        link = await _scrape_link_from_dom(page)
        if link:
            print(f"✅ DOM 刮取: {link[:75]}…")
            return link

        link = await _click_tool_selection_copy(page)
        if link:
            print(f"✅ tool-selection 复制: {link[:75]}…")
            return link

        copy_bar = page.locator(".agent-chat__share-bar__item")
        if await copy_bar.count() > 0:
            link = await _click_copy_with_pyautogui(page, copy_bar.first)
            if link:
                return link

        link = await _js_click_copy_link(page)
        if link:
            print(f"✅ JS 复制: {link[:75]}…")
            return link

        await page.wait_for_timeout(800)
    return ""


async def _wait_copy_link_from_ui(page: Page, *, wait_sec: int = 20) -> str:
    """优先 UI 复制 deep-reading-detail（分享条 / 复制链接）。"""
    deadline = time.monotonic() + wait_sec
    while time.monotonic() < deadline:
        copy_bar = page.locator(".agent-chat__share-bar__item")
        if await copy_bar.count() > 0:
            link = await _click_copy_with_pyautogui(page, copy_bar.first)
            if link:
                return link

        for pattern in (
            r"复制链接",
            r"Copy link",
            r"Copy Link",
            r"^Copy$",
            r"^复制$",
        ):
            item = page.get_by_text(re.compile(pattern, re.I))
            if await item.count() > 0:
                for i in range(await item.count()):
                    link = await _click_copy_with_pyautogui(page, item.nth(i))
                    if link:
                        return link

        await page.wait_for_timeout(1000)
    return ""


async def _try_share_api_once(page: Page, captured: list[dict]) -> str | None:
    """单次 share API（仅剪贴板失败时兜底，且须有 mediaId）。"""
    meta = _parse_deep_reading_page(page.url)
    conv_index = meta["conv_index"]
    speech_index = meta["speech_index"]

    for item in captured:
        try:
            data = json.loads(item["body"])
            target = data.get("targetUrl") or ""
            if target and "deep-reading-detail" in target:
                print(f"✅ 拦截 targetUrl: {target[:75]}…")
                return target.strip()
            sid = data.get("shareId") or ""
            media_id = data.get("mediaId") or ""
            if sid and not media_id:
                media_id = await _resolve_media_id(page)
            if sid and media_id:
                link = _build_deep_reading_share_url(
                    sid,
                    conv_index=conv_index,
                    speech_index=speech_index,
                    media_id=media_id,
                )
                print(f"✅ 拦截 share 响应: {link[:75]}…")
                return link
        except (json.JSONDecodeError, TypeError):
            continue

    cid = meta["cid"]
    if not cid:
        return None

    page_media = await _resolve_media_id(page)
    if page_media:
        print(f"   mediaId: {page_media[:24]}…")

    nickname = await page.evaluate(
        """() => localStorage.getItem('hyc-login-nonce') || localStorage.getItem('guid') || ''"""
    )
    payload: dict = {
        "conversationId": cid,
        "agentId": meta["agent_id"],
        "conversations": [
            {"index": max(1, int(conv_index) - 1)},
            {"index": int(conv_index), "showedRepeatIndex": int(speech_index)},
        ],
        "platform": "WEB",
    }
    if nickname:
        payload["nickname"] = nickname

    result = await page.evaluate(
        """async (body) => {
            const r = await fetch("https://yuanbao.tencent.com/api/conversations/v2/share", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify(body)
            });
            return await r.json();
        }""",
        payload,
    )
    if not isinstance(result, dict):
        return None
    sid = result.get("shareId") or ""
    media_id = result.get("mediaId") or page_media or ""
    target = result.get("targetUrl") or ""
    if target and "deep-reading-detail" in target:
        print(f"✅ share API targetUrl: {target[:75]}…")
        return target.strip()
    if sid and media_id:
        link = _build_deep_reading_share_url(
            sid,
            conv_index=conv_index,
            speech_index=speech_index,
            media_id=media_id,
        )
        print(f"✅ share API 兜底: {link[:75]}…")
        return link
    if sid and not media_id:
        print("⚠️ share API 无 mediaId，跳过 API 兜底")
    return None


async def click_share_and_copy(page: Page) -> str | None:
    print("🔗 点击分享 → UI 复制 deep-reading-detail…")
    captured: list[dict] = []

    async def on_response(response):
        try:
            url = response.url.lower()
            if "share" not in url and "deep-reading" not in url:
                return
            body = await response.text()
            if any(k in body for k in ("shareId", "mediaId", "deep-reading-detail", "targetUrl")):
                captured.append({"url": response.url, "body": body[:8000]})
        except Exception:
            pass

    page.on("response", on_response)

    for attempt in range(3):
        if attempt > 0:
            print(f"🔄 分享重试 ({attempt + 1}/3)：刷新 + 重新验收 tab…")
            await _safe_refresh_deep_reading(page)
            tabs_ok, reason = await verify_all_tabs(page)
            if not tabs_ok and not await _share_button_enabled(page):
                print(f"   …tab 仍未就绪: {reason}")
                continue

        if not await _share_button_enabled(page):
            print("   …Share 不可点，跳过本轮")
            continue

        btn = await _find_share_control(page)
        if btn is None:
            continue

        captured.clear()
        page_media = await _resolve_media_id(page)
        if page_media:
            print(f"   📎 mediaId: {page_media[:28]}…")
        await btn.scroll_into_view_if_needed()
        try:
            await btn.click(timeout=8000)
        except Exception:
            print("   …Playwright 点 Share 失败，改 pyautogui…")
            await _click_element_pyautogui(page, btn)
        await page.wait_for_timeout(2500)

        link = await _wait_share_link_after_click(page, captured, wait_sec=45)
        if link:
            print(f"✅ 分享链: {link[:75]}…")
            return link

        link = await _try_share_api_once(page, captured)
        if link:
            return link

    os.makedirs("logs", exist_ok=True)
    with open("logs/yuanbao_share_captured.json", "w", encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    await page.screenshot(path="logs/yuanbao_ai_read_share_fail.png", full_page=True)
    print("📸 分享失败截图: logs/yuanbao_ai_read_share_fail.png")
    return None


async def process_pdf_ai_read(
    pdf_path: str,
    *,
    profile: str = "./yuanbao_profile",
    entry: str = "direct",
    timeout_sec: int = 600,
    debug: bool = False,
) -> str | None:
    global _session_media_id
    _session_media_id = ""
    pdf_path = os.path.abspath(pdf_path)
    basename = os.path.basename(pdf_path)
    profile = os.path.abspath(profile)
    _ensure_profile_available(profile)

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile,
            headless=False,
            channel="chrome",
            locale="zh-CN",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--lang=zh-CN",
            ],
            permissions=["clipboard-read", "clipboard-write"],
        )
        await browser.set_extra_http_headers(
            {"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5"}
        )
        page = await browser.new_page()
        await _install_page_hooks(page)
        await _apply_zh_locale(page)
        await page.evaluate("window.moveTo(0,0); window.resizeTo(1400, 900);")

        link: str | None = None
        try:
            await navigate_to_ai_read(page, entry=entry)
            await upload_pdf(page, pdf_path)
            await wait_for_ai_read_ready(
                page,
                basename,
                pdf_path=pdf_path,
                entry=entry,
                timeout_sec=timeout_sec,
                debug=debug,
            )
            link = await click_share_and_copy(page)
        finally:
            try:
                if link and _is_valid_share_link(link):
                    print("✅ 分享链已确认，3s 后关闭浏览器…")
                    await page.wait_for_timeout(3000)
                else:
                    print("⏸ 未拿到有效链，窗口保留 30s 供检查…")
                    await page.wait_for_timeout(30000)
            except Exception as exc:
                print(f"⚠️ 关闭前等待跳过: {exc}")
            try:
                await browser.close()
            except Exception:
                pass

        return link


def main() -> None:
    parser = argparse.ArgumentParser(description="元宝 AI 阅读 → deep-reading-detail 分享链")
    parser.add_argument("--pdf", required=True, help="PDF 路径")
    parser.add_argument("--profile", default="./yuanbao_profile")
    parser.add_argument(
        "--entry",
        choices=("direct", "home"),
        default="direct",
        help="direct=AI阅读入口URL; home=首页点侧栏",
    )
    parser.add_argument("--timeout", type=int, default=600, help="解析等待秒数（含脑图）")
    parser.add_argument("--debug", action="store_true", help="超时时保存截图")
    args = parser.parse_args()

    link = asyncio.run(
        process_pdf_ai_read(
            args.pdf,
            profile=args.profile,
            entry=args.entry,
            timeout_sec=args.timeout,
            debug=args.debug,
        )
    )
    if link and _is_valid_share_link(link):
        print(f"\n✅ AI 阅读分享链:\n{link}\n")
    else:
        print(f"\n❌ 未拿到 deep-reading-detail 链接: {link!r}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
