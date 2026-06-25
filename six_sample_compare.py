#!/usr/bin/env python3
"""六样本比选：三平台 × 两档位（快/升一档），统一 brief_rpa prompt，出报告。"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from doubao_rpa import load_structured_prompt, process_pdf_with_doubao

LOG_DIR = Path("logs/six_sample_compare")
PROMPT_MARKERS = ("读者视角：临床问题", "## AES 中文表述规范", "你是医美与整形外科")
SECTIONS = ("为什么值得读", "研究概要", "主要结果", "安全性与局限", "深读提示")

# 已有 fast 档文件映射（pilot 2026-06-24）
FAST_LEGACY = {
    "gemini": ("_gemini_reading_note.txt", "3.5 Flash"),
    "doubao_brief": ("_doubao_brief_reading_note.txt", "快速(页面默认·未脚本锁定)"),
    "yuanbao": ("_yuanbao_reading_note.txt", "标准(深度思考关·未脚本锁定)"),
}

TIER_PRO = {
    "gemini": ("Pro", "_gemini_pro_reading_note.txt"),
    "doubao_brief": ("专家", "_doubao_expert_reading_note.txt"),
    "yuanbao": ("深度思考", "_yuanbao_deepthink_reading_note.txt"),
}


def _analyze(text: str) -> dict:
    if not text:
        return {"chars": 0, "sections": 0, "prompt_leak": False, "ui_noise": True}
    sections = sum(1 for s in SECTIONS if s in text)
    leak = any(m in text for m in PROMPT_MARKERS)
    noise = bool(
        re.search(r"用自己的话总结|请再提供|AI Reading|医美行业的发展趋势", text)
    )
    return {
        "chars": len(text),
        "sections": sections,
        "prompt_leak": leak,
        "ui_noise": noise,
        "has_深读提示": "深读提示" in text,
    }


def _load_fast_samples(pdf: Path) -> list[dict]:
    rows = []
    for ch, (suffix, model) in FAST_LEGACY.items():
        path = pdf.parent / f"{pdf.stem}{suffix}"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        rows.append(
            {
                "channel": ch,
                "tier": "fast",
                "model_label": model,
                "path": str(path),
                "ok": path.exists() and len(text) >= 80,
                "skipped": True,
                "source": "pilot_20260624",
                **_analyze(text),
            }
        )
    return rows


async def _run_gemini(pdf: Path, out: Path, model: str) -> dict:
    from gemini_rpa import process_pdf_with_gemini

    t0 = time.time()
    row = {"channel": "gemini", "tier": "pro", "model_label": model, "path": str(out)}
    try:
        brief, _, tier_meta = await process_pdf_with_gemini(
            str(pdf), model_label=model, verify_share_extract=False
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row.update(tier_meta)
        row["ok"] = len(text) >= 80 and not any(m in text for m in PROMPT_MARKERS)
        row.update(_analyze(text))
    except Exception as e:
        row["ok"] = False
        row["error"] = str(e)
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def _run_doubao(pdf: Path, out: Path, model: str) -> dict:
    t0 = time.time()
    row = {"channel": "doubao_brief", "tier": "pro", "model_label": model, "path": str(out)}
    try:
        prompt = load_structured_prompt("brief")
        brief, _, tier_meta = await process_pdf_with_doubao(
            str(pdf), prompt, "silent", job="dev-brief", profile="./doubao_profile", model_label=model
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row.update(tier_meta)
        row["ok"] = len(text) >= 80 and not any(m in text for m in PROMPT_MARKERS)
        row.update(_analyze(text))
    except Exception as e:
        row["ok"] = False
        row["error"] = str(e)
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def _run_yuanbao(pdf: Path, out: Path, deep: bool) -> dict:
    from playwright.async_api import async_playwright
    from yuanbao_rpa import upload_pdf_and_chat

    t0 = time.time()
    model = "深度思考" if deep else "标准"
    row = {"channel": "yuanbao", "tier": "pro" if deep else "fast", "model_label": model, "path": str(out)}
    try:
        prompt = load_structured_prompt("brief")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                "./yuanbao_profile",
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
                permissions=["clipboard-read", "clipboard-write"],
            )
            page = await browser.new_page()
            await page.evaluate("window.moveTo(0,0); window.resizeTo(1280, 800);")
            text, tier_meta = await upload_pdf_and_chat(page, str(pdf), prompt, deep_thinking=deep)
            await browser.close()
        row.update(tier_meta)
        row["model_label"] = tier_meta.get("tier_observed", model)
        text = text or ""
        out.write_text(text, encoding="utf-8")
        row["ok"] = len(text) >= 80 and not any(m in text for m in PROMPT_MARKERS)
        row.update(_analyze(text))
    except Exception as e:
        row["ok"] = False
        row["error"] = str(e)
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def _write_report(pdf: Path, rows: list[dict], report_path: Path) -> None:
    lines = [
        f"# 六样本导读比选报告",
        f"",
        f"- **PDF**: `{pdf.name}`",
        f"- **Prompt**: `brief_rpa.txt` + style_guide（三平台同一套，**本轮未微调**）",
        f"- **生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **抠字方式**: 均为对话页直接抠字（非分享页）",
        f"",
        f"## 档位说明",
        f"",
        f"| 平台 | 快档 (Round A) | 升一档 (Round B) |",
        f"|------|----------------|------------------|",
        f"| Gemini | 3.5 Flash | Pro |",
        f"| 豆包导读 | 快速(默认) | 专家 |",
        f"| 元宝 | 标准(深度思考关) | 深度思考(开) |",
        f"",
        f"## 样本一览",
        f"",
        f"| 平台 | 档位 | 模型 | 字数 | 五节 | prompt泄漏 | UI杂质 | 耗时(s) | 状态 |",
        f"|------|------|------|------|------|------------|--------|---------|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['channel']} | {r['tier']} | {r.get('model_label','?')} | "
            f"{r.get('chars',0)} | {r.get('sections',0)}/5 | "
            f"{'是' if r.get('prompt_leak') else '否'} | "
            f"{'是' if r.get('ui_noise') else '否'} | "
            f"{r.get('elapsed_sec','-')} | "
            f"{'✓' if r.get('ok') else '✗'} |"
        )
    lines += [
        f"",
        f"## Prompt 对齐结论",
        f"",
        f"- 三平台均使用同一 `load_structured_prompt('brief')`（≈1171 字含表述规范）",
        f"- **比选公平性**：prompt 已对齐；**模型档** fast 档部分为页面默认（豆包/元宝未脚本锁定），解读时需注意",
        f"- **是否微调 prompt**：本轮为 baseline 五段式；流畅度问题留待 `brief_reader` 第二轮回比",
        f"",
        f"## 人工评分（待填 1–5）",
        f"",
        f"| 样本 | 流畅度 | 空节/硬凑 | 数字忠实 | 术语 | 备注 |",
        f"|------|--------|-----------|----------|------|------|",
    ]
    for r in rows:
        tag = f"{r['channel']}/{r['tier']}"
        lines.append(f"| {tag} | | | | | |")
    lines += [
        f"",
        f"## 文件路径",
        f"",
    ]
    for r in rows:
        lines.append(f"- `{r.get('path','')}`")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_all(pdf: Path, *, pro_only: bool) -> list[dict]:
    rows: list[dict] = []
    if not pro_only:
        rows.extend(_load_fast_samples(pdf))

    # Round B — 串行
    pro_jobs = [
        ("gemini", _run_gemini(pdf, pdf.parent / f"{pdf.stem}{TIER_PRO['gemini'][1]}", "Pro")),
        (
            "doubao_brief",
            _run_doubao(pdf, pdf.parent / f"{pdf.stem}{TIER_PRO['doubao_brief'][1]}", "专家"),
        ),
        (
            "yuanbao",
            _run_yuanbao(pdf, pdf.parent / f"{pdf.stem}{TIER_PRO['yuanbao'][1]}", True),
        ),
    ]
    for name, coro in pro_jobs:
        print(f"\n===== Round B: {name} =====")
        rows.append(await coro)
    return rows


def main():
    parser = argparse.ArgumentParser(description="六样本比选 + 报告")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--pro-only", action="store_true", help="只跑升一档三样本（快档读已有文件）")
    parser.add_argument("--report-only", action="store_true", help="仅从已有文件生成报告")
    args = parser.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"不存在: {pdf}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = LOG_DIR / f"report_{pdf.stem}_{run_id}.md"
    jsonl_path = LOG_DIR / f"run_{run_id}.jsonl"

    if args.report_only:
        rows = _load_fast_samples(pdf)
        for ch, (_, suffix) in TIER_PRO.items():
            p = pdf.parent / f"{pdf.stem}{suffix}"
            if p.exists():
                text = p.read_text(encoding="utf-8")
                rows.append(
                    {
                        "channel": ch,
                        "tier": "pro",
                        "model_label": TIER_PRO[ch][0],
                        "path": str(p),
                        "ok": len(text) >= 80,
                        **_analyze(text),
                    }
                )
    else:
        rows = asyncio.run(run_all(pdf, pro_only=args.pro_only))
        for r in rows:
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    _write_report(pdf, rows, report_path)
    print(f"\n✅ 报告: {report_path}")
    print(f"   样本数: {len(rows)}")


if __name__ == "__main__":
    main()
