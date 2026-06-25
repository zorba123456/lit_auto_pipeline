import asyncio
import os
import re
import subprocess
import argparse

from playwright.async_api import async_playwright
import pyautogui
import pyperclip

from rpa_tier import make_tier_meta

YUANBAO_CHAT_URL = "https://yuanbao.tencent.com/chat"


def get_idle_time():
    """Returns macOS system idle time in seconds."""
    try:
        res = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True,
            text=True,
        )
        for line in res.stdout.splitlines():
            if "HIDIdleTime" in line:
                return int(line.split("=")[-1].strip()) / 1000000000.0
    except Exception as e:
        print(f"Error getting idle time: {e}")
    return 0.0


async def wait_for_idle(target_idle_sec=60):
    """Wait until the system is idle for target_idle_sec."""
    print(f"Waiting for system to be idle for {target_idle_sec} seconds...")
    while True:
        idle_time = get_idle_time()
        if idle_time >= target_idle_sec:
            print(f"System has been idle for {idle_time:.1f}s. Proceeding!")
            break

        remaining = target_idle_sec - idle_time
        sleep_time = min(remaining, 5.0)
        if sleep_time < 0.5:
            sleep_time = 0.5
        print(f"Current idle time: {idle_time:.1f}s. Waiting...")
        await asyncio.sleep(sleep_time)


def _is_green_color_js() -> str:
    """选中态：元宝 Deep Thinking 文字/图标变绿（用户标定）。"""
    return """(el) => {
        const nodes = el ? [el, ...el.querySelectorAll('*')] : [];
        for (const n of nodes) {
            const c = getComputedStyle(n).color || '';
            const m = c.match(/\\d+/g);
            if (!m || m.length < 3) continue;
            const [r, g, b] = m.map(Number);
            if (g >= 90 && g > r + 25 && g > b + 15) return true;
        }
        return false;
    }"""


async def _deep_thinking_target_coords(page) -> tuple[float, float] | None:
    """定位输入区左下角 Deep Thinking 可点击区域中心。"""
    pt = await page.evaluate(
        """() => {
            const vh = window.innerHeight;
            const labels = ['Deep Thinking', '深度思考'];
            const cands = [];
            for (const el of document.querySelectorAll('div, button, span, a, [role="button"]')) {
                const r = el.getBoundingClientRect();
                if (r.top < vh * 0.52 || r.height < 12 || r.height > 80 || r.width < 30) continue;
                const t = (el.innerText || '').trim();
                if (!labels.some((l) => t === l || (t.startsWith(l) && t.length <= 24))) continue;
                cands.push({ el, top: r.top, area: r.width * r.height });
            }
            if (!cands.length) return null;
            cands.sort((a, b) => b.top - a.top || a.area - b.area);
            const pick = cands[0].el.closest('button, [role="button"]') || cands[0].el;
            const box = pick.getBoundingClientRect();
            return { x: box.x + box.width / 2, y: box.y + box.height / 2, tag: pick.tagName };
        }"""
    )
    if not pt:
        return None
    print(f"   …定位 Deep Thinking 控件 <{pt.get('tag', '?')}>")
    return pt["x"], pt["y"]


async def is_deep_thinking_active(page) -> bool:
    """选中 = 绿色字/图标（非悬停临时态）。"""
    try:
        return bool(
            await page.evaluate(
                f"""() => {{
                    const vh = window.innerHeight;
                    const labels = ['Deep Thinking', '深度思考'];
                    const isGreen = {_is_green_color_js()};
                    for (const el of document.querySelectorAll('div, button, span, [role="button"]')) {{
                        const r = el.getBoundingClientRect();
                        if (r.top < vh * 0.52) continue;
                        const t = (el.innerText || '').trim();
                        if (!labels.some((l) => t === l || (t.startsWith(l) && t.length <= 24))) continue;
                        const root = el.closest('button, [role="button"]') || el;
                        if (isGreen(root)) return true;
                    }}
                    return false;
                }}"""
            )
        )
    except Exception:
        return False


async def set_deep_thinking(page, enabled: bool = True) -> None:
    """点击输入区 Deep Thinking；选中后文字/图标应保持绿色。"""
    print(f"🎛️ 深度思考: {'开' if enabled else '关'}")
    if await is_deep_thinking_active(page) == enabled:
        if enabled:
            print("✅ 深度思考已开启（绿色·会话保留），跳过点击")
        else:
            print("✅ 深度思考已关闭，跳过点击")
        return

    coords = await _deep_thinking_target_coords(page)
    if coords:
        x, y = coords
        print(f"👆 鼠标点击 Deep Thinking（{x:.0f},{y:.0f}）")
        await page.mouse.click(x, y)
        await page.wait_for_timeout(1000)
        if await is_deep_thinking_active(page) == enabled:
            print(f"✅ 深度思考已{'开启' if enabled else '关闭'}（{'绿色' if enabled else '灰色'}确认）")
            return
        await page.mouse.click(x, y)
        await page.wait_for_timeout(1000)
        if await is_deep_thinking_active(page) == enabled:
            print(f"✅ 深度思考已{'开启' if enabled else '关闭'}（二次点击{'绿色' if enabled else '灰色'}确认）")
            return

    clicked = await page.evaluate(
        f"""(wantOn) => {{
            const vh = window.innerHeight;
            const labels = ['Deep Thinking', '深度思考'];
            const isGreen = {_is_green_color_js()};
            for (const el of document.querySelectorAll('div, button, span, [role="button"]')) {{
                const r = el.getBoundingClientRect();
                if (r.top < vh * 0.52) continue;
                const t = (el.innerText || '').trim();
                if (!labels.some((l) => t === l || (t.startsWith(l) && t.length <= 24))) continue;
                const btn = el.closest('button, [role="button"]') || el;
                const on = isGreen(btn);
                if (wantOn !== on) btn.click();
                return true;
            }}
            return false;
        }}""",
        enabled,
    )
    await page.wait_for_timeout(900)
    if await is_deep_thinking_active(page) == enabled:
        print(f"✅ 深度思考已{'开启' if enabled else '关闭'}（{'绿色' if enabled else '灰色'}确认）")
        return
    if clicked or coords:
        print(f"⚠️ 已点击但绿色未确认（当前={'开' if await is_deep_thinking_active(page) else '关'}）")
    else:
        print("⚠️ 未找到深度思考按钮，沿用默认")


async def _wait_for_compose_ready(page) -> None:
    """新 UI：底部输入框 placeholder「Ask me anything…」或 ProseMirror。"""
    print("Waiting for chat compose area…")
    for loc in (
        page.get_by_placeholder(re.compile(r"Ask me anything", re.I)),
        page.locator(".ProseMirror, .ql-editor, [contenteditable='true']"),
        page.locator("[data-testid='upload-file-selector']"),
    ):
        try:
            await loc.first.wait_for(state="visible", timeout=25000)
            print("✅ 输入区已就绪")
            return
        except Exception:
            pass
    raise RuntimeError("未找到元宝输入区（需确认 yuanbao_profile 已登录）")


async def _click_upload_plus(page) -> None:
    """输入框右下角 + → 展开 Image / Local Files / Tencent Docs。"""
    for loc in (
        page.locator("[data-testid='upload-file-selector']"),
        page.get_by_role("button", name=re.compile(r"^\+$|upload|attach|添加", re.I)),
    ):
        try:
            if await loc.count() > 0:
                await loc.first.click(timeout=5000)
                await page.wait_for_timeout(600)
                return
        except Exception:
            pass

    clicked = await page.evaluate(
        """() => {
            const tb = document.querySelector(
                '.ProseMirror, .ql-editor, [contenteditable="true"], textarea'
            );
            if (!tb) return false;
            const tbRect = tb.getBoundingClientRect();
            const buttons = [...document.querySelectorAll('button, [role="button"]')];
            const candidates = buttons.filter((b) => {
                const r = b.getBoundingClientRect();
                if (r.width < 24 || r.height < 24) return false;
                return (
                    r.left >= tbRect.right - 80 &&
                    Math.abs(r.bottom - tbRect.bottom) < 50
                );
            });
            candidates.sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right);
            if (!candidates.length) return false;
            candidates[0].click();
            return true;
        }"""
    )
    if not clicked:
        raise RuntimeError("未能点击输入区右下角 + 按钮")
    await page.wait_for_timeout(600)


async def _upload_pdf_via_local_files(page, pdf_path: str) -> None:
    print(f"Uploading PDF: {pdf_path}")
    await _click_upload_plus(page)

    async with page.expect_file_chooser(timeout=15000) as fc_info:
        clicked = False
        for label in ("Local Files", "上传本地文件", "本地文件"):
            try:
                item = page.get_by_text(label, exact=True)
                if await item.count() > 0:
                    await item.first.click(timeout=5000)
                    clicked = True
                    break
            except Exception:
                pass
        if not clicked:
            item = page.get_by_role("menuitem", name=re.compile(r"Local Files|本地文件", re.I))
            if await item.count() > 0:
                await item.first.click(timeout=5000)
                clicked = True
        if not clicked:
            raise RuntimeError("未找到 Local Files 菜单项")

    fc = await fc_info.value
    await fc.set_files(pdf_path)

    print("Waiting for PDF attachment…")
    basename = os.path.basename(pdf_path)
    for _ in range(30):
        await page.wait_for_timeout(1000)
        body = await page.evaluate("() => document.body.innerText || ''")
        if basename in body or ".pdf" in body.lower():
            print("✅ PDF 已附在输入区")
            await page.wait_for_timeout(800)
            return
    print("⚠️ 未确认附件名，继续发送 prompt")


async def _fill_prompt(page, prompt: str) -> None:
    prompt_area = page.locator(".ProseMirror, .ql-editor, textarea, [contenteditable='true']")
    await prompt_area.first.click(timeout=8000)
    try:
        await prompt_area.first.fill(prompt)
    except Exception:
        await page.keyboard.press("Meta+A")
        await page.keyboard.type(prompt, delay=2)
    await page.wait_for_timeout(400)


async def _submit_prompt(page) -> None:
    for loc in (
        page.locator("div[dt-button-id='send_btn']"),
        page.get_by_role("button", name=re.compile(r"Send|发送|提交", re.I)),
    ):
        try:
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                return
        except Exception:
            pass
    await page.keyboard.press("Enter")


async def _wait_for_ai_reply(page) -> None:
    print("Waiting for AI response…")
    await page.wait_for_timeout(3000)
    try:
        await page.wait_for_selector(
            ".agent-chat__list__item--ai[data-conv-outputting='true']",
            timeout=20000,
        )
        print("…生成中")
        await page.wait_for_selector(
            ".agent-chat__list__item--ai[data-conv-outputting='true']",
            state="hidden",
            timeout=180000,
        )
    except Exception:
        try:
            await page.wait_for_selector(
                ".agent-chat__list__item--ai[data-conv-outputting='false']",
                state="attached",
                timeout=120000,
            )
        except Exception:
            print("Wait for outputting timed out; assuming done.")
    await page.wait_for_timeout(1500)


async def _extract_ai_text(page) -> str:
    print("Extracting summary text…")
    text = await page.evaluate(
        """() => {
            const items = document.querySelectorAll('.agent-chat__list__item--ai');
            const last = items[items.length - 1];
            if (!last) return '';
            const root = last.cloneNode(true);
            const drop = [
                '[class*="deep-think"]', '[class*="deepThink"]',
                '[class*="think-fold"]', '[class*="thinkFold"]',
                '[class*="reasoning"]', '[class*="cot-"]',
                '[class*="hyc-think"]',
            ];
            for (const sel of drop) {
                root.querySelectorAll(sel).forEach((el) => el.remove());
            }
            const content = root.querySelector('.hyc-content-text');
            return (content || root).innerText || '';
        }"""
    )
    if not text or len(text) < 80:
        ai_bubbles = page.locator(".agent-chat__list__item--ai .hyc-content-text")
        count = await ai_bubbles.count()
        if count > 0:
            text = await ai_bubbles.last.inner_text()
    if not text:
        for sel in (".agent-chat__list__item--ai", "[class*='markdown']", "main"):
            loc = page.locator(sel)
            if await loc.count() > 0:
                text = await loc.last.inner_text()
                if len(text) > 80:
                    break
    from prompts.open_brief_utils import strip_yuanbao_deep_thinking_fold

    text = strip_yuanbao_deep_thinking_fold(text or "")
    if text:
        print(f"✅ 导读正文 {len(text)} 字（已排除 DT 折叠区）")
    return text


async def get_visible_model_label(page) -> str:
    """读取页面可见模型档位（Round A 记录用）。"""
    try:
        label = await page.evaluate(
            """() => {
                const t = document.body.innerText || '';
                const m = t.match(/(DeepSeek[^\\n]{0,40}|Hunyuan[^\\n]{0,40}|GPT[^\\n]{0,40}|快速|专家|Pro|Flash)/i);
                return m ? m[0].trim() : '';
            }"""
        )
        return label or "unknown"
    except Exception:
        return "unknown"


async def ensure_deep_thinking_before_upload(page, *, enabled: bool) -> bool:
    """上传 PDF 前点选 Deep Thinking，以绿色为选中态。"""
    if not enabled:
        print("🎛️ 上传前关闭 Deep Thinking…")
        if not await is_deep_thinking_active(page):
            print("✅ 上传前 Deep Thinking 已关（非绿）")
            return True
        for attempt in range(3):
            await set_deep_thinking(page, False)
            if not await is_deep_thinking_active(page):
                print("✅ 上传前 Deep Thinking 已关（灰色确认）")
                return True
            print(f"   …第 {attempt + 1} 次点击后仍为绿，重试")
            await page.wait_for_timeout(500)
        print("⚠️ 上传前未能关掉 Deep Thinking，快档可能被污染")
        return False
    print("🎛️ 上传前点选 Deep Thinking…")
    for attempt in range(3):
        await set_deep_thinking(page, True)
        if await is_deep_thinking_active(page):
            print("✅ 上传前 Deep Thinking 已绿")
            return True
        print(f"   …第 {attempt + 1} 次点击后仍未变绿，重试")
        await page.wait_for_timeout(500)
    print("⚠️ 上传前未能确认 Deep Thinking 变绿，仍继续上传")
    return False


async def upload_pdf_and_chat(page, pdf_path, prompt, *, deep_thinking: bool = False):
    print("Navigating to Yuanbao chat…")
    await page.goto(YUANBAO_CHAT_URL, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(2000)

    await _wait_for_compose_ready(page)
    dt_ok = await ensure_deep_thinking_before_upload(page, enabled=deep_thinking)
    dt_active = await is_deep_thinking_active(page)
    model_label = "深度思考" if (deep_thinking and dt_active) else await get_visible_model_label(page)
    if deep_thinking:
        print(f"🎛️ 上传前深度思考: {'绿色已确认' if dt_active else '未确认'}")
    else:
        print(f"🎛️ 快档 Deep Thinking: {'关（非绿）' if not dt_active else '⚠️ 仍为绿'}")
        print(f"🎛️ 页面模型/档位: {model_label}")

    await _upload_pdf_via_local_files(page, pdf_path)

    if deep_thinking and not await is_deep_thinking_active(page):
        print("⚠️ 上传后 Deep Thinking 掉绿，发送 prompt 前再点一次…")
        await set_deep_thinking(page, True)

    print(f"Sending prompt ({len(prompt)} chars)…")
    await _fill_prompt(page, prompt)
    await _submit_prompt(page)

    await _wait_for_ai_reply(page)
    summary_text = await _extract_ai_text(page)
    if deep_thinking:
        final_green = await is_deep_thinking_active(page)
        observed = "深度思考(绿)" if (dt_ok or final_green) else "深度思考(未确认绿)"
        requested = "深度思考"
    else:
        final_active = await is_deep_thinking_active(page)
        observed = "快档(DT关)" if not final_active else "快档(DT仍为绿)"
        requested = "快档"
    tier_meta = make_tier_meta(
        channel="yuanbao",
        tier_requested=requested,
        tier_observed=observed,
        extra={
            "deep_thinking": deep_thinking,
            "deep_thinking_green": bool(final_green if deep_thinking else not final_active),
        },
    )
    return summary_text, tier_meta


async def get_share_link(page):
    print("Opening share menu...")
    share_btns = page.locator("div[aria-label='分享']")
    count = await share_btns.count()
    if count == 0:
        print("Share button not found!")
        return None

    btn = share_btns.nth(count - 1)
    await btn.scroll_into_view_if_needed()
    await btn.click()
    await page.wait_for_timeout(1000)

    copy_link_btn = page.locator(".agent-chat__share-bar__item").first
    if await copy_link_btn.count() == 0:
        print("Copy link item not found!")
        return None

    coords = await copy_link_btn.evaluate(
        """(element) => {
        const rect = element.getBoundingClientRect();
        const x = window.screenX + rect.left + rect.width / 2;
        const y = window.screenY + (window.outerHeight - window.innerHeight) + rect.top + rect.height / 2;
        return {x, y};
    }"""
    )

    print("Clearing clipboard...")
    pyperclip.copy("")

    print("Stealing focus to click...")
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
    await asyncio.sleep(0.5)

    original_x, original_y = pyautogui.position()

    pyautogui.moveTo(coords["x"], coords["y"], duration=0.2)
    pyautogui.click()
    pyautogui.moveTo(original_x, original_y, duration=0.2)

    await asyncio.sleep(1)

    link = pyperclip.paste()
    return link


async def main():
    parser = argparse.ArgumentParser(description="Yuanbao PDF RPA")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--prompt", default="这是一篇真实的医美测试文献，请总结其核心医学观点。", help="Prompt to send")
    parser.add_argument("--mode", choices=["silent", "share"], default="share", help="Running mode")
    parser.add_argument("--idle", type=int, default=60, help="Idle wait time in seconds (for share mode)")
    args = parser.parse_args()

    abs_pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(abs_pdf_path):
        print(f"File not found: {abs_pdf_path}")
        return

    async with async_playwright() as p:
        user_data_dir = "./yuanbao_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await browser.new_page()

        await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 800);")

        summary, tier_meta = await upload_pdf_and_chat(page, abs_pdf_path, args.prompt)
        model_label = tier_meta.get("tier_observed", "?")
        print(f"\n--- SUMMARY (model={model_label}) ---")
        print(summary)
        print("---------------\n")

        share_link = None
        if args.mode == "share":
            await wait_for_idle(args.idle)
            share_link = await get_share_link(page)
            print(f"Share link obtained: {share_link}")

        await browser.close()

        out_file = abs_pdf_path + "_result.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            if share_link:
                f.write(f"Share Link: {share_link}\n")
            f.write(f"Model: {model_label}\n\n")
            f.write("Summary:\n")
            f.write(summary)
        print(f"Result saved to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
