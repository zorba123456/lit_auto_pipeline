"""Gemini web RPA helpers: model, upload, prompt, share, brief extract."""

from __future__ import annotations

import re
import subprocess

from doubao_rpa_extract import extract_brief_from_main_text

GEMINI_CHAT_URL = "https://gemini.google.com/app"
DEFAULT_MODEL_LABEL = "3.5 Flash"
SHARE_URL_RE = re.compile(
    r"(https?://)?gemini\.google\.com/share/[a-zA-Z0-9]+",
    re.I,
)


async def start_new_chat(page) -> None:
    print("🆕 尝试开启新对话…")
    for label in ("New chat", "新对话", "New Chat"):
        try:
            btn = page.get_by_role("button", name=label)
            if await btn.count() > 0:
                await btn.first.click(timeout=4000)
                await page.wait_for_timeout(1500)
                return
        except Exception:
            pass
    try:
        await page.goto(GEMINI_CHAT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)
    except Exception:
        pass
    print("ℹ️ 使用当前 Gemini 会话页")


async def select_model(page, model_label: str = DEFAULT_MODEL_LABEL) -> None:
    print(f"🎛️ 选择模型: {model_label}")
    opened = False
    # 输入框右侧药丸（截图中为 Flash）
    for opener in (
        page.get_by_role("button", name=re.compile(r"^Flash$|^Fast$|^Pro$", re.I)),
        page.locator("button").filter(has_text=re.compile(r"^Flash$|^Fast$|^Pro$", re.I)),
        page.get_by_role("button", name=re.compile(r"Flash|Fast|Pro|Gemini", re.I)),
    ):
        try:
            if await opener.count() > 0:
                # 优先点输入栏上的 Flash（通常在页面下方）
                btn = opener.last if await opener.count() > 1 else opener.first
                await btn.click(timeout=3000)
                opened = True
                break
        except Exception:
            pass
    if not opened:
        print("⚠️ 未点到模型下拉，沿用当前模型")
        return

    await page.wait_for_timeout(800)
    for loc in (
        page.get_by_role("menuitem", name=re.compile(model_label, re.I)),
        page.get_by_role("option", name=re.compile(model_label, re.I)),
        page.get_by_text(model_label, exact=False),
    ):
        try:
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(1000)
                print(f"✅ 已选 {model_label}")
                return
        except Exception:
            pass
    print(f"⚠️ 未找到 {model_label!r}，沿用下拉当前项")


async def get_gemini_visible_model(page) -> str:
    """读取输入区药丸显示的模型（Flash / Pro 等）。"""
    try:
        label = await page.evaluate(
            """() => {
                const re = /^(Flash|Fast|Pro|Gemini[\\s\\d.]*Pro|Gemini[\\s\\d.]*Flash)$/i;
                const vh = window.innerHeight;
                const cands = [];
                for (const el of document.querySelectorAll('button, [role="button"], span')) {
                    const r = el.getBoundingClientRect();
                    if (r.top < vh * 0.45 || r.height > 48) continue;
                    const t = (el.innerText || '').trim();
                    if (re.test(t)) cands.push({ t, top: r.top });
                }
                cands.sort((a, b) => b.top - a.top);
                return cands.length ? cands[0].t : '';
            }"""
        )
        return label or "unknown"
    except Exception:
        return "unknown"


async def _click_compose_plus(page) -> bool:
    """输入框左侧 + 按钮，展开 Upload files 等菜单。"""
    textbox = page.get_by_role("textbox", name=re.compile(r"Ask Gemini|prompt|Gemini|问问", re.I))
    if await textbox.count() > 0:
        await textbox.first.click(timeout=8000)

    for loc in (
        page.get_by_role("button", name=re.compile(r"Open upload|Add files|Attach|Upload menu", re.I)),
        page.locator('button[aria-label*="Add" i], button[aria-label*="attach" i], button[aria-label*="upload" i]'),
    ):
        try:
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(600)
                return True
        except Exception:
            pass

    clicked = await page.evaluate(
        """() => {
            const tb = document.querySelector(
                'rich-textarea, [contenteditable="true"], textarea[placeholder*="Gemini" i], textarea'
            );
            if (!tb) return false;
            const tbRect = tb.getBoundingClientRect();
            const buttons = [...document.querySelectorAll('button')];
            const candidates = buttons.filter((b) => {
                const r = b.getBoundingClientRect();
                if (r.width < 20 || r.height < 20) return false;
                return r.left <= tbRect.left + 8 && Math.abs(r.top - tbRect.top) < 55;
            });
            candidates.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
            if (!candidates.length) return false;
            candidates[0].click();
            return true;
        }"""
    )
    if clicked:
        await page.wait_for_timeout(600)
    return bool(clicked)


async def upload_pdf(page, pdf_path: str) -> None:
    print(f"📄 上传 PDF: {pdf_path}")
    uploaded = False

    # 优先：隐藏 file input（比菜单更稳）
    try:
        fi = page.locator('input[type="file"]')
        if await fi.count() > 0:
            await fi.first.set_input_files(pdf_path)
            uploaded = True
            await page.wait_for_timeout(800)
            print("👆 已通过 input[type=file] 上传")
    except Exception as e:
        print(f"   …file input 失败: {e}")

    # Gemini 首页/对话页：点 + → Upload files → 选文件
    if not uploaded and await _click_compose_plus(page):
        for label in ("Upload files", "Upload file", "上传文件"):
            try:
                item = page.get_by_role("menuitem", name=re.compile(label, re.I))
                if await item.count() == 0:
                    item = page.get_by_text(label, exact=True)
                if await item.count() > 0:
                    print(f"👆 菜单选择: {label}")
                    async with page.expect_file_chooser(timeout=12000) as fc_info:
                        await item.first.click(timeout=5000)
                    fc = await fc_info.value
                    await fc.set_files(pdf_path)
                    uploaded = True
                    await page.wait_for_timeout(500)
                    break
            except Exception as e:
                print(f"   …{label} 失败: {e}")

    # fallback：隐藏 file input
    if not uploaded:
        try:
            fi = page.locator('input[type="file"]')
            if await fi.count() > 0:
                await fi.first.set_input_files(pdf_path)
                uploaded = True
                await page.wait_for_timeout(800)
                print("👆 已通过 input[type=file] 上传")
        except Exception:
            pass

    if not uploaded and await _click_compose_plus(page):
        await page.wait_for_timeout(500)
        for label in ("Upload files", "Upload file", "上传文件"):
            try:
                item = page.get_by_role("menuitem", name=re.compile(label, re.I))
                if await item.count() == 0:
                    item = page.get_by_text(label, exact=True)
                if await item.count() > 0:
                    print(f"👆 菜单重试: {label}")
                    async with page.expect_file_chooser(timeout=12000) as fc_info:
                        await item.first.click(timeout=5000)
                    fc = await fc_info.value
                    await fc.set_files(pdf_path)
                    uploaded = True
                    await page.wait_for_timeout(500)
                    break
            except Exception as e:
                print(f"   …{label} 重试失败: {e}")

    if not uploaded:
        raise RuntimeError("未能打开 + 菜单并选择 Upload files")

    await wait_pdf_attached(page, pdf_path, uploaded_via_chooser=uploaded)


async def _compose_has_pdf(page, pdf_basename: str) -> bool:
    """附件 chip 在输入区即可，不必等对话区出现 PDF 或全文解析完成。"""
    return await page.evaluate(
        """(basename) => {
            const lower = basename.toLowerCase();
            const short = lower.replace(/\\.pdf$/i, '');
            const stem = short.slice(0, 24);
            const inLower = (t) => {
                const s = (t || '').toLowerCase();
                return s.includes(lower) || s.includes(short + '.pdf')
                    || (stem.length >= 8 && s.includes(stem));
            };
            const compose = document.querySelector(
                'rich-textarea, [contenteditable="true"], footer, form, [class*="input-area"]'
            );
            if (compose) {
                let el = compose;
                for (let i = 0; i < 8 && el; i++) {
                    if (inLower(el.innerText)) return true;
                    el = el.parentElement;
                }
            }
            const vh = window.innerHeight;
            for (const el of document.querySelectorAll('button, [role="button"], span, div, a')) {
                const r = el.getBoundingClientRect();
                if (r.top < vh * 0.38 || r.height > 96) continue;
                const t = (el.innerText || '').trim();
                if (!t || t.length > 160) continue;
                if (inLower(t) || /\\.pdf\\b/i.test(t)) return true;
            }
            return false;
        }""",
        pdf_basename,
    )


async def _page_has_pdf(page, pdf_basename: str) -> bool:
  """全文检索 PDF 文件名（输入区 chip 或对话区）。"""
  import os

  stem = os.path.splitext(pdf_basename)[0]
  short = stem[:20]
  return await page.evaluate(
      """({ basename, stem, short }) => {
          const body = document.body.innerText || '';
          const lower = body.toLowerCase();
          const b = basename.toLowerCase();
          if (lower.includes(b)) return true;
          if (stem.length >= 8 && lower.includes(stem.toLowerCase().slice(0, 24))) return true;
          if (short.length >= 8 && lower.includes(short.toLowerCase())) return true;
          return /\\.pdf/i.test(body);
      }""",
      {"basename": pdf_basename, "stem": stem, "short": short},
  )


async def wait_pdf_attached(
    page, pdf_path: str, max_sec: int = 20, *, uploaded_via_chooser: bool = False
) -> None:
    """PDF 出现在页面即继续；chooser 已成功则宽限等待。"""
    import os

    basename = os.path.basename(pdf_path)
    print(f"⏳ 等待 PDF 附件（最多 {max_sec}s，不等全文解析）…")
    for tick in range(max_sec * 3):
        await page.wait_for_timeout(333)
        if await _compose_has_pdf(page, basename) or await _page_has_pdf(page, basename):
            print(f"✅ PDF 已确认（约 {tick * 0.33:.1f}s）")
            await page.wait_for_timeout(1200)
            return
    if uploaded_via_chooser:
        print("⚠️ 未检测到文件名 chip，但文件已选入；额外等待 3s 后继续")
        await page.wait_for_timeout(3000)
        return
    raise RuntimeError(f"未在页面确认 PDF 附件: {basename}")


def _normalize_share_url(text: str) -> str | None:
    if not text:
        return None
    m = SHARE_URL_RE.search(text.strip())
    if not m:
        return None
    url = m.group(0)
    if not url.lower().startswith("http"):
        url = "https://" + url.lstrip("/")
    return url.rstrip("/")


async def _read_clipboard(page) -> str:
    try:
        return (await page.evaluate("async () => await navigator.clipboard.readText()")) or ""
    except Exception:
        pass
    try:
        res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
        return res.stdout or ""
    except Exception:
        return ""


async def _extract_share_from_modal(page) -> str | None:
    return _normalize_share_url(
        await page.evaluate(
            """() => {
                const dialogs = [...document.querySelectorAll('[role="dialog"], mat-dialog-container, .cdk-overlay-pane')];
                for (const d of dialogs) {
                    const t = d.innerText || '';
                    if (!/shareable public link|分享|public link/i.test(t)) continue;
                    const m = t.match(/gemini\\.google\\.com\\/share\\/[a-zA-Z0-9]+/i);
                    if (m) return m[0];
                }
                const body = document.body.innerText || '';
                const m = body.match(/gemini\\.google\\.com\\/share\\/[a-zA-Z0-9]+/i);
                return m ? m[0] : '';
            }"""
        )
    )


async def _click_submit_arrow(page) -> bool:
    """输入框右下角蓝色上箭头（Send）。"""
    for loc in (
        page.get_by_role("button", name=re.compile(r"^Send$|Send message|Submit|发送", re.I)),
        page.locator('button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="发送"]'),
        page.locator("button.send-button, button[data-test-id='send-button']"),
    ):
        try:
            n = await loc.count()
            if n > 0:
                await loc.nth(n - 1).click(timeout=4000)
                return True
        except Exception:
            pass

    clicked = await page.evaluate(
        """() => {
            const tb = document.querySelector(
                'rich-textarea, [contenteditable="true"], textarea[placeholder*="Gemini" i], textarea'
            );
            if (!tb) return false;
            const tbRect = tb.getBoundingClientRect();
            const buttons = [...document.querySelectorAll('button')];
            const inBar = buttons.filter((b) => {
                const r = b.getBoundingClientRect();
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                if (aria.includes('mic')) return false;
                return (
                    r.left >= tbRect.left &&
                    Math.abs(r.top - tbRect.bottom) < 70 &&
                    r.width <= 72 &&
                    r.height <= 72
                );
            });
            inBar.sort((a, b) => b.getBoundingClientRect().left - a.getBoundingClientRect().left);
            if (!inBar.length) return false;
            inBar[0].click();
            return true;
        }"""
    )
    return bool(clicked)


async def send_prompt(page, prompt: str) -> bool:
    print(f"✍️ 输入 prompt ({len(prompt)} 字)…")
    box = page.get_by_role("textbox", name=re.compile(r"Ask Gemini|prompt|Gemini|问问", re.I))
    if await box.count() == 0:
        box = page.locator("div[contenteditable=true], rich-textarea").last
    await box.first.click(timeout=10000)
    await page.wait_for_timeout(300)

    try:
        await box.first.fill(prompt)
    except Exception:
        await page.keyboard.press("Meta+A")
        await page.keyboard.type(prompt, delay=3)

    await page.wait_for_timeout(500)
    print("🚀 提交（上箭头 / Enter）…")
    if await _click_submit_arrow(page):
        await page.wait_for_timeout(1000)
        return True

    await page.keyboard.press("Enter")
    await page.wait_for_timeout(800)
    return True


async def get_model_reply_text(page) -> str:
    """尽量只取 Gemini 助手回复，避免用户 prompt 干扰导读提取。"""
    try:
        text = await page.evaluate(
            """() => {
                const parts = [];
                const selectors = [
                    '[data-message-author-role="model"]',
                    'model-response',
                    '.model-response-text',
                    '.response-content',
                ];
                for (const sel of selectors) {
                    const nodes = document.querySelectorAll(sel);
                    if (!nodes.length) continue;
                    nodes.forEach((n) => {
                        if (!n) return;
                        const t = (n.innerText || '').trim();
                        if (t) parts.push(t);
                    });
                    if (parts.length) return parts.join('\\n\\n');
                }
                return '';
            }"""
        )
        return text or ""
    except Exception:
        return ""


async def get_conversation_text(page) -> str:
    try:
        model = await get_model_reply_text(page)
        if model and len(model) >= 120:
            return model
        return await page.evaluate(
            """() => {
                const conv = document.querySelector('infinite-scroller, .conversation-container, main');
                if (conv && conv.innerText) return conv.innerText;
                const main = document.querySelector('main');
                if (main && main.innerText) return main.innerText;
                const body = document.body;
                return body && body.innerText ? body.innerText : '';
            }"""
        )
    except Exception:
        return ""


def extract_gemini_brief(text: str, *, structured: bool = True) -> str:
    """Gemini 会话页抠导读：跳过用户 prompt，取助手回复段。"""
    if not structured:
        from prompts.open_brief_utils import extract_after_open_prompt

        return _strip_gemini_tail_ui(extract_after_open_prompt(text))

    got = extract_brief_from_main_text(text)
    if got:
        return got

    for marker in ("### 为什么值得读", "## 为什么值得读", "为什么值得读"):
        positions: list[int] = []
        start = 0
        while True:
            i = text.find(marker, start)
            if i == -1:
                break
            positions.append(i)
            start = i + len(marker)
        for pos in positions[1:] if len(positions) > 1 else positions:
            chunk = text[pos:]
            # 跳过仍属用户 prompt 的段落（节标题下接占位说明）
            after = chunk.split("\n", 1)[-1][:80]
            if "读者视角：临床问题" in after or "建议全文重点阅读的 2–4 处（如图表" in after:
                continue
            got = extract_brief_from_main_text(chunk)
            if got:
                return got
            cleaned = _strip_gemini_tail_ui(chunk)
            if _looks_like_gemini_brief(cleaned):
                return cleaned

    # 用户 prompt 结束于「深读提示」占位说明之后；其后为助手导读
    for anchor in (
        "建议全文重点阅读的 2–4 处（如图表、方法段），不列全文纲要。",
        "## AES 中文表述规范",
    ):
        if anchor not in text:
            continue
        tail = text.split(anchor, 1)[-1]
        if anchor.startswith("##"):
            # style guide 块后再找第一节
            for marker in ("为什么值得读", "研究概要"):
                idx = tail.find(marker)
                if idx != -1:
                    tail = tail[idx:]
                    break
        got = extract_brief_from_main_text(tail)
        if got:
            return got
        cleaned = _strip_gemini_tail_ui(tail)
        if _looks_like_gemini_brief(cleaned):
            return cleaned

    return ""


BRIEF_SECTION_TITLES = (
    "为什么值得读",
    "研究概要",
    "主要结果",
    "安全性与局限",
    "深读提示",
)
BRIEF_MIN_CHARS = 200


def _brief_section_count(text: str) -> int:
    return sum(1 for t in BRIEF_SECTION_TITLES if t in text)


def _has_deep_read_content(text: str) -> bool:
    idx = text.find("深读提示")
    if idx == -1:
        return False
    tail = text[idx + len("深读提示") :].strip().lstrip("：:").strip()
    return len(tail) >= 12


def _brief_is_ready(text: str) -> bool:
    """导读结构齐全且非 prompt 泄漏，才允许进入分享。"""
    if len(text) < BRIEF_MIN_CHARS:
        return False
    if "读者视角：临床问题、作者声称" in text[:500]:
        return False
    sections = _brief_section_count(text)
    if sections >= 5 and _has_deep_read_content(text):
        return True
    if sections >= 4 and _has_deep_read_content(text):
        return True
    return False


def _looks_like_gemini_brief(chunk: str) -> bool:
    if len(chunk) < 80:
        return False
    if "读者视角：临床问题、作者声称" in chunk[:500]:
        return False
    hits = sum(1 for t in BRIEF_SECTION_TITLES if t in chunk)
    return hits >= 2


def _strip_gemini_tail_ui(chunk: str) -> str:
    for stop in (
        "Share conversation",
        "Link copied",
        "Shareable public link",
        "Ask Gemini",
        "Google Terms",
    ):
        if stop in chunk:
            chunk = chunk.split(stop)[0]
    return chunk.strip()


async def _gemini_still_generating(page) -> bool:
    """Gemini 仍在流式输出：仅认「停止回答」类按钮（豆包「停止生成」同款，避免误判）。"""
    try:
        return bool(
            await page.evaluate(
                """() => {
                    const stopExact = /^(Stop response|Stop generating|停止回答|停止生成)$/i;
                    for (const b of document.querySelectorAll('button, [role="button"]')) {
                        const aria = (b.getAttribute('aria-label') || '').trim();
                        const t = (b.innerText || '').trim();
                        if (!stopExact.test(aria) && !stopExact.test(t)) continue;
                        const r = b.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0 && r.width < 120) return true;
                    }
                    return false;
                }"""
            )
        )
    except Exception:
        return False


# Gemini 主对话区固定 chrome（⋮ 在 conversation panel 右上，非全局 title bar）
_SIDEBAR_MIN_X = 72
_PANEL_CHROME_Y_MIN = 8   # getBoundingClientRect 已含 automation banner 下移（实测 y≈14）
_PANEL_CHROME_Y_MAX = 240
_RIGHT_EDGE_MARGIN = 40


async def _conversation_overflow_locator(page):
    """Gemini conversation panel 固定右上 ⋮（DOM: button[aria-label*='conversation actions']）。"""
    for loc in (
        page.locator('button[aria-label*="conversation actions" i]'),
        page.locator('mat-icon-button[aria-label*="conversation actions" i]'),
        page.get_by_role("button", name=re.compile(r"Open menu for conversation actions", re.I)),
        page.get_by_label(re.compile(r"Open menu for conversation actions", re.I)),
        page.locator('[role="button"][aria-label*="conversation actions" i]'),
    ):
        try:
            n = await loc.count()
            for i in range(n):
                btn = loc.nth(i)
                box = await btn.bounding_box()
                if not box:
                    continue
                if box["x"] < _SIDEBAR_MIN_X:
                    continue
                if box["y"] < _PANEL_CHROME_Y_MIN or box["y"] > _PANEL_CHROME_Y_MAX:
                    continue
                vw, _ = await _viewport_size(page)
                if box["x"] + box["width"] < vw - _RIGHT_EDGE_MARGIN:
                    continue
                return btn
        except Exception:
            pass
    return None


async def _viewport_size(page) -> tuple[int, int]:
    try:
        vp = page.viewport_size
        if vp:
            return vp["width"], vp["height"]
    except Exception:
        pass
    try:
        wh = await page.evaluate("() => ({ w: window.innerWidth, h: window.innerHeight })")
        return int(wh["w"]), int(wh["h"])
    except Exception:
        return 1280, 900


async def _list_header_overflow_candidates(page) -> list[dict]:
    """固定视口右上 ⋮；用 Playwright locator 穿透 shadow DOM。"""
    candidates: list[dict] = []
    seen: set[str] = set()
    vw, vh = await _viewport_size(page)
    skip_re = re.compile(
        r"helpful|thumb|\bcopy\b|regenerate|share export|good response|bad response|"
        r"modify|listen|\bmic\b|send|\bupload\b|\bflash\b|\bpro\b|new chat|settings|\bhelp\b|\bsearch\b",
        re.I,
    )

    for loc in (
        page.locator("button"),
        page.locator('[role="button"]'),
        page.locator("mat-icon-button"),
    ):
        try:
            n = await loc.count()
        except Exception:
            continue
        for i in range(min(n, 80)):
            btn = loc.nth(i)
            try:
                box = await btn.bounding_box()
                if not box or box["width"] < 8 or box["height"] < 8:
                    continue
                if box["width"] > 72 or box["height"] > 72:
                    continue
                if box["y"] < _PANEL_CHROME_Y_MIN or box["y"] > _PANEL_CHROME_Y_MAX:
                    continue
                if box["y"] > vh * 0.82:
                    continue
                if box["x"] < _SIDEBAR_MIN_X:
                    continue
                if box["x"] + box["width"] < vw - _RIGHT_EDGE_MARGIN:
                    continue
                aria = (await btn.get_attribute("aria-label") or "").strip()
                if skip_re.search(aria):
                    continue
                text = (await btn.inner_text() or "").strip()
                aria_ok = bool(
                    re.search(r"more|menu|options|conversation|overflow", aria, re.I)
                    or "conversation actions" in aria.lower()
                )
                icon_ok = "more_vert" in text or text in ("⋮", "more_horiz")
                small_icon = not text and box["width"] <= 56 and box["height"] <= 56
                if not (aria_ok or icon_ok or (small_icon and aria_ok)):
                    continue
                key = f"{round(box['x'])},{round(box['y'])},{aria}"
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "aria": aria,
                        "iconText": text,
                        "text": text,
                        "x": round(box["x"]),
                        "y": round(box["y"]),
                        "w": round(box["width"]),
                        "h": round(box["height"]),
                        "right": round(box["x"] + box["width"]),
                    }
                )
            except Exception:
                continue

    candidates.sort(key=lambda c: (-c["right"], c["y"]))
    return candidates


async def _overflow_button_is_fixed(page, cand: dict) -> bool:
    """滚动对话区后，固定 ⋮ 的 viewport y 应基本不变。"""
    y0 = cand["y"]
    await page.evaluate(
        """() => {
            const sc = document.querySelector('infinite-scroller, .conversation-container');
            if (sc) sc.scrollTop = sc.scrollHeight;
            window.scrollBy(0, 500);
        }"""
    )
    await page.wait_for_timeout(350)
    after = await _list_header_overflow_candidates(page)
    await page.evaluate("window.scrollTo(0, 0)")
    await page.keyboard.press("Home")
    if not after:
        return False
    return abs(after[0]["y"] - y0) <= 10


async def wait_for_header_overflow_menu(page, timeout_sec: int = 30) -> bool:
    """等待 conversation panel 固定右上 ⋮（流式开始后即有；≠ 回复完成）。"""
    print(f"⏳ 等待固定右上 ⋮（最多 {timeout_sec}s）…")
    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        loc = await _conversation_overflow_locator(page)
        if loc:
            try:
                box = await loc.bounding_box()
                if box and box.get("width", 0) > 0:
                    print(
                        f"✅ ⋮ 已出现 @ right={round(box['x'] + box['width'])} "
                        f"y={round(box['y'])} aria=conversation actions"
                    )
                    return True
            except Exception:
                pass
        candidates = await _list_header_overflow_candidates(page)
        if candidates:
            c0 = candidates[0]
            print(
                f"✅ ⋮ 已出现 @ right={c0.get('right')} y={c0.get('y')} "
                f"aria={c0.get('aria')!r} icon={c0.get('iconText')!r}"
            )
            return True
        if tick % 6 == 0:
            print("   …⋮ 尚未出现，继续等待…")
    print("⚠️ 超时仍未见到固定右上 ⋮")
    # Playwright 诊断
    debug: list[dict] = []
    try:
        for i in range(min(await page.locator("button").count(), 30)):
            btn = page.locator("button").nth(i)
            box = await btn.bounding_box()
            if not box:
                continue
            debug.append(
                {
                    "aria": ((await btn.get_attribute("aria-label")) or "")[:40],
                    "text": (await btn.inner_text() or "")[:20],
                    "x": round(box["x"]),
                    "y": round(box["y"]),
                    "right": round(box["x"] + box["width"]),
                }
            )
    except Exception:
        pass
    debug.sort(key=lambda b: -b.get("right", 0))
    print(f"   诊断按钮(前12): {debug[:12]}")
    return False


async def wait_for_brief_reply(
    page, min_chars: int = 200, timeout_sec: int = 240, *, structured: bool = True
) -> str:
    """等待导读完成。移植 doubao wait_for_assistant_reply：只看页面字数是否还在增长。

    ⋮ 在流式开始时即出现，不能作为完成信号；完成 = 导读 extract 达标 + 页面字数 stable≥8（≈4s）。
    """
    from prompts.open_brief_utils import OPEN_MIN_CHARS, open_brief_is_ready

    print(f"⏳ 等待 Gemini 导读（最长 {timeout_sec}s，豆包同款：页面字数稳定）…")
    last_page_len = 0
    stable = 0
    best = ""

    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        text = await get_conversation_text(page)
        extracted = extract_gemini_brief(text, structured=structured)
        ready_fn = _brief_is_ready if structured else open_brief_is_ready
        min_len = min_chars if structured else OPEN_MIN_CHARS

        if extracted and len(extracted) >= min_len:
            best = extracted
            if tick % 4 == 0:
                if structured:
                    print(
                        f"   …已捕获导读 {len(extracted)} 字 / {_brief_section_count(extracted)} 节"
                    )
                else:
                    print(f"   …已捕获导读 {len(extracted)} 字")

        cur_len = len(text)
        if cur_len > last_page_len:
            last_page_len = cur_len
            stable = 0
        elif best and ready_fn(best):
            still_gen = await _gemini_still_generating(page)
            if still_gen:
                stable = 0
                if tick % 10 == 0:
                    print("   …Stop 按钮仍在，继续等待")
            else:
                stable += 1
                if stable >= 8 and tick > 10:
                    if structured:
                        print(
                            f"✅ 导读完成（{len(best)} 字，{_brief_section_count(best)} 节，"
                            f"页面 {cur_len} 字稳定 {stable * 0.5:.0f}s）"
                        )
                    else:
                        print(f"✅ 开放导读完成（{len(best)} 字）")
                    return best

        if (
            tick > 20
            and extracted
            and ready_fn(extracted)
            and stable >= 4
            and not await _gemini_still_generating(page)
        ):
            if structured:
                print(f"✅ 导读已就绪（{len(extracted)} 字，{_brief_section_count(extracted)} 节）")
            else:
                print(f"✅ 开放导读已就绪（{len(extracted)} 字）")
            return extracted

    if best:
        if structured and _brief_section_count(best) >= 2:
            print(
                f"⚠️ 超时，使用最佳导读（{len(best)} 字，{_brief_section_count(best)} 节）"
            )
        elif not structured and len(best) >= OPEN_MIN_CHARS:
            print(f"⚠️ 超时，使用最佳开放导读（{len(best)} 字）")
    return best


async def _wait_for_gemini_reply_stable(
    page, *, min_chars: int = 150, timeout_sec: int = 60
) -> str:
    """移植 doubao wait_for_reply_stable：任意长回复结束（fallback 抠导读用）。"""
    print(f"⏳ 等待页面回复稳定（最长 {timeout_sec}s）…")
    last_len = 0
    stable = 0
    best = ""

    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        text = await get_conversation_text(page)
        if len(text) > len(best):
            best = text
        still_gen = await _gemini_still_generating(page)
        cur_len = len(text)
        if cur_len > last_len or still_gen:
            last_len = max(last_len, cur_len)
            stable = 0
        else:
            stable += 1
            if stable >= 8 and len(best) >= min_chars and tick > 10 and not still_gen:
                print(f"✅ 回复稳定（约 {len(best)} 字页面文本）")
                return best
        if tick > 30 and stable >= 6 and len(best) >= min_chars and not still_gen:
            return best

    return best if len(best) >= min_chars else ""


async def _menu_is_open(page) -> bool:
    try:
        n = await page.locator(
            '.cdk-overlay-container [role="menu"], mat-menu-panel, .mat-mdc-menu-panel'
        ).count()
        return n > 0
    except Exception:
        return False


async def _click_conversation_overflow_menu(page) -> bool:
    """点击 conversation panel 固定右上 ⋮（aria=Open menu for conversation actions）。"""
    print("👆 点击固定右上 ⋮ …")
    try:
        await page.evaluate("window.scrollTo(0, 0)")
        await page.keyboard.press("Home")
        await page.wait_for_timeout(400)
    except Exception:
        pass

    # 首选：Gemini 实测 aria（诊断 run_155340 确认）
    loc = await _conversation_overflow_locator(page)
    if loc:
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            await loc.click(timeout=5000)
            await page.wait_for_timeout(700)
            if await _menu_is_open(page):
                print("✅ ⋮ 菜单已打开（conversation actions）")
                return True
            # 菜单可能无标准 overlay；检查 Share conversation 是否出现在 DOM
            if await page.get_by_text(re.compile(r"Share conversation|分享对话", re.I)).count() > 0:
                print("✅ ⋮ 菜单已打开（Share conversation 可见）")
                return True
        except Exception as exc:
            print(f"   ⋮ 首选点击失败: {exc}")

    candidates = await _list_header_overflow_candidates(page)
    if not candidates:
        print("⚠️ 未找到固定右上 ⋮ 候选")
        return False

    target = candidates[0]
    for cand in candidates[:3]:
        if await _overflow_button_is_fixed(page, cand):
            target = cand
            print(f"   固定 ⋮: right={target['right']} y={target['y']} aria={target.get('aria')!r}")
            break
    else:
        print(f"   用最右候选: right={target['right']} y={target['y']} aria={target.get('aria')!r}")

    clicked = False
    for pattern in (
        r"Open menu for conversation actions",
        r"More options",
        r"Conversation menu",
        r"Conversation options",
    ):
        loc = page.get_by_role("button", name=re.compile(pattern, re.I))
        try:
            cnt = await loc.count()
            for i in range(cnt):
                btn = loc.nth(i)
                box = await btn.bounding_box()
                if box and _PANEL_CHROME_Y_MIN <= box["y"] <= _PANEL_CHROME_Y_MAX and box["x"] >= _SIDEBAR_MIN_X:
                    await btn.click(timeout=3000)
                    clicked = True
                    print(f"   点到 aria≈{pattern}")
                    break
            if clicked:
                break
        except Exception:
            pass

    if not clicked:
        try:
            await page.mouse.click(target["x"] + target["w"] / 2, target["y"] + target["h"] / 2)
            clicked = True
        except Exception:
            pass

    await page.wait_for_timeout(700)
    if await _menu_is_open(page):
        print("✅ ⋮ 菜单已打开")
        return True

    print(f"⚠️ ⋮ 点击后菜单未打开；候选: {candidates[:5]}")
    return False


async def _click_share_conversation_menu_item(page) -> bool:
    for tick in range(12):
        await page.wait_for_timeout(250)
        for loc in (
            page.locator(".cdk-overlay-container").get_by_text(
                re.compile(r"^Share conversation$|^分享对话$", re.I)
            ),
            page.locator('[role="menuitem"]').filter(
                has_text=re.compile(r"^Share conversation$|^分享对话$", re.I)
            ),
            page.get_by_role("menuitem", name=re.compile(r"Share conversation|分享对话", re.I)),
        ):
            try:
                if await loc.count() > 0:
                    await loc.first.click(timeout=5000)
                    await page.wait_for_timeout(400)
                    return True
            except Exception:
                pass

    clicked = await page.evaluate(
        """() => {
            const labels = ['Share conversation', '分享对话'];
            const roots = [
                ...document.querySelectorAll('.cdk-overlay-container *'),
                ...document.querySelectorAll('[role="menuitem"], mat-menu-item, .mat-mdc-menu-item'),
            ];
            for (const n of roots) {
                const t = (n.innerText || '').trim();
                if (!labels.includes(t)) continue;
                const r = n.getBoundingClientRect();
                if (r.width < 4 || r.height < 4) continue;
                (n.closest('[role="menuitem"], mat-menu-item, button') || n).click();
                return true;
            }
            return false;
        }"""
    )
    if not clicked:
        items = await page.evaluate(
            """() => {
                const sel = '.cdk-overlay-container [role="menuitem"], mat-menu-item, .mat-mdc-menu-item';
                return [...document.querySelectorAll(sel)].map((e) => (e.innerText || '').trim()).filter(Boolean);
            }"""
        )
        print(f"   可见菜单项: {items[:8]}")
    return bool(clicked)


async def get_share_link(page) -> str | None:
    """导读稳定后：固定右上 ⋮ → Share conversation → 弹窗/剪贴板。

    ⋮ 在流式开始即出现，此处假定调用方已 wait_for_brief_reply；不再用 ⋮ 判断完成。
    """
    print("📤 获取 Gemini 分享链接（conversation panel 右上 ⋮）…")

    loc = await _conversation_overflow_locator(page)
    if not loc:
        if not await wait_for_header_overflow_menu(page, timeout_sec=15):
            return None
    else:
        print("✅ ⋮ 已定位（conversation actions）")

    if not await _click_conversation_overflow_menu(page):
        print("⚠️ 未点到固定右上 ⋮")
        return None

    if not await _click_share_conversation_menu_item(page):
        print("⚠️ 未点到 Share conversation 菜单项")
        return None

    # 弹窗出现后约 1s 自动复制到剪贴板（按钮会显示 Link copied）
    for _ in range(16):
        await page.wait_for_timeout(500)
        share_url = await _extract_share_from_modal(page)
        if share_url:
            print(f"🔗 {share_url}")
            return share_url
        clip = await _read_clipboard(page)
        share_url = _normalize_share_url(clip)
        if share_url:
            print(f"🔗 {share_url}（剪贴板）")
            return share_url

    print("⚠️ 未从弹窗或剪贴板拿到分享 URL")
    return None
