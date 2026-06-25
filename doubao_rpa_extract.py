"""Doubao web RPA helpers: send PDF + prompt, extract assistant reply from chat main area."""

from __future__ import annotations

import re

BRIEF_SECTION_MARKERS = [
    "### 为什么值得读",
    "### 研究概要",
    "### 主要结果",
    "### 安全性与局限",
    "### 深读提示",
]

PLAIN_SECTION_TITLES = (
    "为什么值得读",
    "研究概要",
    "主要结果",
    "安全性与局限",
    "深读提示",
)

# brief_rpa / 注入块里才会出现的占位说明，不应进入 reading_note_zh
PROMPT_BOILERPLATE = frozenset({
    "读者视角：临床问题、作者声称的创新或贡献（1–2点）、读完多知道什么。勿写是否值得报道。",
    "研究设计、样本量、干预与对照（关键参数一笔带过），不展开手术细节。",
    "主要终点与关键数字（P值/CI/率等，文中有则写）；可极简表格。",
    "不良事件（无则写文中未报告）；1–3条局限。",
    "建议全文重点阅读的 2–4 处（如图表、方法段），不列全文纲要。",
})

STYLE_GUIDE_HEADER = "## AES 中文表述规范"

UI_NOISE_LINES = frozenset({
    "搜索…", "豆包", "新对话", "新办公任务", "AI 创作", "云盘", "更多",
    "历史对话", "主对话", "快速", "PPT 生成", "AI 表格", "图像生成",
    "帮我写作", "视频生成", "更多", "分享", "复制", "重新生成", "不满意",
    "满意", "下载电脑版", "新对话", "复制链接", "下载", "朗读",
    "AI 生成可能有误 请核实", "打开豆包",
})

STOP_SUFFIXES = (
    "重新生成", "分享", "复制链接", "下载电脑版", "快速\nPPT",
    "AI 生成可能有误",
)

_WORD_COUNT_TAIL = re.compile(r"\n*（全文总字数\s*\d+）\s*")
_TRAILING_UI = re.compile(r"\n*(打开豆包|复制链接|分享.*)\s*$")


async def wait_for_reply_stable(
    page, *, min_chars: int = 150, timeout_sec: int = 180
) -> str:
    """等待豆包任意回复结束（chip 等公开分享场景，不抠导读结构）。"""
    print(f"⏳ 等待回复完成（最长 {timeout_sec}s）…")
    last_len = 0
    stable = 0
    best = ""

    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        text = await get_main_chat_text(page)
        if len(text) > len(best):
            best = text
        cur_len = len(text)
        if cur_len > last_len:
            last_len = cur_len
            stable = 0
        else:
            stable += 1
            if stable >= 8 and len(best) >= min_chars:
                if "停止生成" not in best and tick > 10:
                    print(f"✅ 回复稳定（约 {len(best)} 字页面文本）")
                    return best
        if tick > 30 and stable >= 6 and len(best) >= min_chars:
            return best

    return best if len(best) >= min_chars else ""


async def start_new_chat(page) -> None:
    """尽量进入空白对话，减少侧边栏历史干扰。"""
    print("🆕 尝试开启新对话…")
    for label in ("新对话", "新聊天"):
        try:
            loc = page.get_by_role("link", name=label)
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(1500)
                return
        except Exception:
            pass
        try:
            loc = page.get_by_text(label, exact=True)
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(1500)
                return
        except Exception:
            pass
    print("ℹ️ 未点到「新对话」，沿用当前会话")


async def get_doubao_visible_model(page) -> str:
    """读取输入区当前显示的模型档（生成中可能临时显示为「快速」）。"""
    try:
        label = await page.evaluate(
            """() => {
                const re = /^(快速|专家|深度思考|Lite|Pro|Max)$/i;
                for (const el of document.querySelectorAll('button, [role="button"], span')) {
                    const t = (el.innerText || '').trim();
                    if (re.test(t)) return t;
                }
                return '';
            }"""
        )
        return label or "unknown"
    except Exception:
        return "unknown"


async def select_doubao_model(page, model_label: str = "快速") -> None:
    """豆包输入区模型档：快速 / 专家 等。"""
    print(f"🎛️ 选择豆包模型: {model_label}")
    opened = False
    for opener in (
        page.get_by_role("button", name=re.compile(r"^快速$|^专家$|深度思考", re.I)),
        page.locator("button, [role='button']").filter(
            has_text=re.compile(r"^快速$|^专家$", re.I)
        ),
    ):
        try:
            if await opener.count() > 0:
                await opener.first.click(timeout=3000)
                opened = True
                break
        except Exception:
            pass
    if not opened:
        print("⚠️ 未点到模型下拉，沿用当前档")
        return
    await page.wait_for_timeout(500)
    for loc in (
        page.get_by_role("menuitem", name=re.compile(model_label, re.I)),
        page.get_by_text(model_label, exact=True),
        page.locator("[role='option']").filter(has_text=re.compile(model_label, re.I)),
    ):
        try:
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                await page.wait_for_timeout(800)
                print(f"✅ 已选 {model_label}")
                return
        except Exception:
            pass
    print(f"⚠️ 未找到 {model_label!r}，沿用当前档")


async def log_doubao_model_state(page, *, expected: str | None, phase: str) -> str:
    """记录豆包档位；生成中 UI 常会回到「快速」，不代表后端降档。"""
    visible = await get_doubao_visible_model(page)
    if expected and visible != "unknown" and visible != expected:
        print(
            f"ℹ️ 豆包档位 [{phase}] 页面显示={visible!r}（期望 {expected!r}；"
            f"生成中回显快速属产品 UI，未必降档）"
        )
    else:
        print(f"ℹ️ 豆包档位 [{phase}] 页面显示={visible!r}")
    return visible


async def wait_pdf_ready(page, max_sec: int = 90) -> None:
    print(f"⏳ 等待 PDF 解析完成（最多 {max_sec} 秒）…")
    for _ in range(max_sec // 2):
        await page.wait_for_timeout(2000)
        body = await get_main_chat_text(page)
        if "解析中" not in body and "Analyzing" not in body:
            if ".pdf" in body.lower() or "PDF" in body:
                break
    await page.wait_for_timeout(1500)


async def send_prompt(page, prompt: str) -> bool:
    print(f"✍️ 输入提示词 ({len(prompt)} 字)…")
    ta = page.locator("textarea").first
    await ta.wait_for(state="visible", timeout=15000)
    await ta.fill(prompt)
    await page.wait_for_timeout(400)
    await ta.focus()

    print("🚀 发送（Enter）…")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(800)

    try:
        send_btn = page.get_by_role("button", name="发送")
        if await send_btn.count() > 0:
            await send_btn.last.click(timeout=2000)
    except Exception:
        pass

    for _ in range(30):
        await page.wait_for_timeout(500)
        try:
            val = (await ta.input_value()).strip()
            if len(val) < max(30, len(prompt) // 4):
                print("✅ 输入框已清空，判定已发送")
                return True
        except Exception:
            pass
        main = await get_main_chat_text(page)
        if "停止生成" in main or "Stop" in main:
            print("✅ 检测到「停止生成」，判定已发送")
            return True

    print("⚠️ 未能确认是否发送成功（可能仍在输入框内）")
    return False


async def get_main_chat_text(page) -> str:
    """只取主对话区文字，排除左侧导航。"""
    return await page.evaluate(
        """() => {
            const main = document.querySelector('main[data-container-name="main"]');
            if (main) return main.innerText || '';
            const root = document.querySelector('#root main') || document.querySelector('main');
            return root ? (root.innerText || '') : (document.body.innerText || '');
        }"""
    )


async def wait_for_assistant_reply(
    page,
    min_chars: int = 120,
    timeout_sec: int = 180,
    *,
    structured: bool = True,
    prompt_kind: str = "brief",
) -> str:
    """等待主对话区出现导读正文（不含 prompt）。"""
    if not structured:
        return await _wait_for_open_reply(
            page, timeout_sec=timeout_sec, prompt_kind=prompt_kind
        )

    print(f"⏳ 等待豆包回复（最长 {timeout_sec}s）…")
    last_len = 0
    stable = 0
    best = ""

    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        text = await get_main_chat_text(page)
        extracted = extract_brief_from_main_text(text)
        if extracted and len(extracted) >= min_chars:
            best = extracted
            if tick % 4 == 0:
                print(f"   …已捕获导读 {len(extracted)} 字（不含 prompt）")
        cur_len = len(text)
        if cur_len > last_len:
            last_len = cur_len
            stable = 0
        elif best and len(best) >= min_chars:
            stable += 1
            if stable >= 8:
                print("✅ 导读长度稳定，结束等待")
                return best
        if tick > 20 and extracted and len(extracted) >= min_chars and stable >= 4:
            return extracted

    return best


async def _doubao_still_generating(page) -> bool:
    main = await get_main_chat_text(page)
    return any(
        x in main for x in ("停止生成", "Stop generating", "正在生成", "生成中")
    )


async def _wait_for_open_reply(
    page, *, timeout_sec: int = 240, prompt_kind: str = "open"
) -> str:
    from prompts.open_brief_utils import (
        INNOVATION_MIN_CHARS,
        OPEN_MIN_CHARS,
        extract_after_innovation_prompt,
        extract_after_open_prompt,
        innovation_is_ready,
        open_brief_is_ready,
        thinking_noise_ratio,
    )

    extract_fn = (
        extract_after_innovation_prompt
        if prompt_kind == "innovation"
        else extract_after_open_prompt
    )
    min_chars = INNOVATION_MIN_CHARS if prompt_kind == "innovation" else OPEN_MIN_CHARS
    ready_fn = innovation_is_ready if prompt_kind == "innovation" else open_brief_is_ready
    label = "创新性评估" if prompt_kind == "innovation" else "开放导读"

    print(f"⏳ 等待豆包{label}（最长 {timeout_sec}s）…")
    last_len = 0
    stable = 0
    best = ""
    peak_best = 0

    for tick in range(timeout_sec * 2):
        await page.wait_for_timeout(500)
        text = await get_main_chat_text(page)
        extracted = extract_fn(text)
        if extracted and len(extracted) >= min_chars:
            if thinking_noise_ratio(extracted) > 0.35:
                if tick % 8 == 0:
                    print("   …专家档思考链未结束，继续等待…")
                stable = 0
                continue
            if len(extracted) >= len(best):
                best = extracted
                peak_best = max(peak_best, len(extracted))
            if tick % 4 == 0:
                print(f"   …已捕获导读 {len(extracted)} 字（best={len(best)}）")
        generating = await _doubao_still_generating(page)
        cur_len = len(text)
        if cur_len > last_len or generating:
            last_len = max(last_len, cur_len)
            stable = 0
        elif best and len(best) >= max(min_chars, int(peak_best * 0.9)):
            stable += 1
            if not generating and ready_fn(best) and stable >= 12:
                print(f"✅ {label}稳定（{len(best)} 字）")
                return best
        elif best and len(best) >= min_chars and stable >= 8 and tick > 60 and not generating:
            return best

    if best:
        print(f"⚠️ 等待结束，返回最佳导读（{len(best)} 字，peak={peak_best}）")
    return best


def _looks_like_prompt_chunk(chunk: str) -> bool:
    if STYLE_GUIDE_HEADER in chunk:
        return True
    if "读者视角：临床问题、作者声称" in chunk[:400]:
        return True
    hits = sum(1 for line in PROMPT_BOILERPLATE if line in chunk)
    return hits >= 3


def _has_real_sections(text: str) -> bool:
    count = 0
    for title in PLAIN_SECTION_TITLES:
        if title in text or f"### {title}" in text:
            count += 1
    return count >= 2


def _strip_prompt_and_style_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    in_style_guide = False
    for line in lines:
        t = line.strip()
        if not t or t in UI_NOISE_LINES:
            continue
        if t.startswith("你是医美") or t.startswith("纪律："):
            continue
        if STYLE_GUIDE_HEADER in t or t.startswith("## AES 中文表述规范"):
            in_style_guide = True
            continue
        if in_style_guide:
            if t in PLAIN_SECTION_TITLES or t in BRIEF_SECTION_MARKERS:
                in_style_guide = False
            else:
                continue
        if t in PROMPT_BOILERPLATE:
            continue
        if t.startswith("### ") and t[4:].strip() in PLAIN_SECTION_TITLES:
            if in_style_guide:
                continue
            out.append(t[4:].strip())
            continue
        out.append(line.rstrip())
    return out


def _finalize_brief_chunk(chunk: str) -> str:
    for stop in STOP_SUFFIXES:
        if stop in chunk:
            chunk = chunk.split(stop)[0]
    if STYLE_GUIDE_HEADER in chunk:
        chunk = chunk.split(STYLE_GUIDE_HEADER)[0]
    lines = _strip_prompt_and_style_lines(chunk.splitlines())
    result = "\n".join(lines).strip()
    result = _WORD_COUNT_TAIL.sub("", result).strip()
    result = _TRAILING_UI.sub("", result).strip()
    if len(result) < 80 or not _has_real_sections(result):
        return ""
    if _looks_like_prompt_chunk(result):
        return ""
    return result


def _extract_from_plain_section(text: str, start_line_idx: int, lines: list[str]) -> str:
    if start_line_idx + 1 < len(lines):
        nxt = lines[start_line_idx + 1].strip()
        if not nxt or nxt in PROMPT_BOILERPLATE or nxt.startswith("读者视角：临床问题"):
            return ""
    return _finalize_brief_chunk("\n".join(lines[start_line_idx:]))


def _extract_plain_sections(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != "为什么值得读":
            continue
        got = _extract_from_plain_section(text, i, lines)
        if got:
            return got
    return ""


def _extract_plain_after_style_guide(text: str) -> str:
    idx = text.find(STYLE_GUIDE_HEADER)
    if idx == -1:
        return ""
    return _extract_plain_sections(text[idx:])


def _extract_from_marked_sections(text: str) -> str:
    marker = "### 为什么值得读"
    candidates: list[str] = []
    pos = 0
    while True:
        i = text.find(marker, pos)
        if i == -1:
            break
        got = _finalize_brief_chunk(text[i:])
        if got:
            candidates.append(got)
        pos = i + len(marker)
    if not candidates:
        return ""
    return max(candidates, key=len)


def extract_brief_from_main_text(text: str) -> str:
    """从页面文本提取豆包导读正文；**不含**用户 prompt 与表述规范注入块。"""
    if not text:
        return ""

    candidates: list[str] = []

    marked = _extract_from_marked_sections(text)
    if marked and not _looks_like_prompt_chunk(marked):
        candidates.append(marked)

    for fn in (_extract_plain_after_style_guide, _extract_plain_sections):
        got = fn(text)
        if got:
            candidates.append(got)

    if not candidates:
        return ""

    # 优先取最长且不像 prompt 的候选（多为完整五节导读）
    candidates = [c for c in candidates if not _looks_like_prompt_chunk(c)]
    if not candidates:
        return ""
    return max(candidates, key=len)


def extract_brief_legacy(full_text: str, prompt: str) -> str:
    """Fallback：整页再抠一次（已统一走 extract_brief_from_main_text）。"""
    got = extract_brief_from_main_text(full_text)
    if got:
        return got
    compact = prompt.strip()[:120]
    if compact and compact in full_text:
        return extract_brief_from_main_text(full_text.split(compact)[-1])
    return ""


async def capture_assistant_reply(
    page, prompt: str, pdf_path: str, *, structured: bool = True, prompt_kind: str = "brief"
) -> str:
    """主流程：等待并提取；失败时 dump 主对话区（非整页）。"""
    main_text = await wait_for_assistant_reply(
        page, structured=structured, prompt_kind=prompt_kind
    )
    if main_text and not structured:
        from prompts.open_brief_utils import strip_expert_thinking

        main_text = strip_expert_thinking(main_text)
    if main_text:
        return main_text

    main_text = await get_main_chat_text(page)
    if structured:
        legacy = extract_brief_legacy(main_text, prompt)
    else:
        from prompts.open_brief_utils import (
            extract_after_innovation_prompt,
            extract_after_open_prompt,
        )

        legacy = (
            extract_after_innovation_prompt(main_text)
            if prompt_kind == "innovation"
            else extract_after_open_prompt(main_text)
        )
    if legacy:
        return legacy

    print("⚠️ 未抓到有效导读（可能未发送、仍在生成、或需登录/验证码）")
    debug_path = pdf_path + "_doubao_debug.txt"
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("=== MAIN CHAT AREA ===\n")
        f.write(main_text)
        f.write("\n\n=== FULL BODY (diagnostic) ===\n")
        full = await page.evaluate("document.body.innerText")
        f.write(full)
    print(f"📋 已 dump 主对话区: {debug_path} ({len(main_text)} chars in main)")
    return ""
