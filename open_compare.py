#!/usr/bin/env python3
"""Round 2 开放导读比选：brief_open.txt × 3 通道 × N 篇 PDF（串行）。"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from doubao_rpa import load_structured_prompt, process_pdf_with_doubao

LOG_DIR = Path("logs/open_compare")

ROUND2_PDFS: list[tuple[str, str]] = [
    (
        "surgical",
        "less_is_better__full_incision_double_eyelid.18.pdf",
    ),
    (
        "injection",
        "J of Cosmetic Dermatology - 2023 - Peng - Aspiration before tissue filling with hyaluronic acid‐safety enhancement by using.pdf",
    ),
]


def _load_open_prompt() -> str:
    return load_structured_prompt("open")


def _doubao_out_path(pdf: Path, model_label: str | None) -> Path:
    stem = pdf.stem
    if model_label and re.search(r"专家", model_label):
        return pdf.parent / f"{stem}_doubao_expert_open_reading_note.txt"
    return pdf.parent / f"{stem}_doubao_open_reading_note.txt"


def _gemini_out_path(pdf: Path, model_label: str) -> Path:
    stem = pdf.stem
    if re.search(r"flash[- ]?lite", model_label, re.I):
        return pdf.parent / f"{stem}_gemini_flashlite_open_reading_note.txt"
    if re.match(r"pro", model_label, re.I):
        return pdf.parent / f"{stem}_gemini_pro_open_reading_note.txt"
    return pdf.parent / f"{stem}_gemini_open_reading_note.txt"


def _yuanbao_out_path(pdf: Path, deep_thinking: bool) -> Path:
    stem = pdf.stem
    if deep_thinking:
        return pdf.parent / f"{stem}_yuanbao_deepthink_open_reading_note.txt"
    return pdf.parent / f"{stem}_yuanbao_open_reading_note.txt"


async def run_gemini(
    pdf: Path, prompt: str, out: Path, *, model_label: str
) -> dict:
    from gemini_rpa import process_pdf_with_gemini

    t0 = time.time()
    row = {
        "channel": "gemini",
        "model_label": model_label,
        "ok": False,
        "chars": 0,
        "error": None,
    }
    try:
        brief, share, tier_meta = await process_pdf_with_gemini(
            str(pdf),
            prompt=prompt,
            model_label=model_label,
            verify_share_extract=False,
            structured_brief=False,
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row["chars"] = len(text)
        row["share_url"] = share
        row["ok"] = len(text) >= 400
        row.update(tier_meta)
        row["model_label"] = tier_meta.get("tier_observed", model_label)
        print(f"✅ gemini ({model_label}) → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ gemini: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def run_yuanbao(
    pdf: Path, prompt: str, out: Path, *, deep_thinking: bool = False
) -> dict:
    from yuanbao_rpa import upload_pdf_and_chat
    from playwright.async_api import async_playwright

    t0 = time.time()
    row = {
        "channel": "yuanbao",
        "ok": False,
        "chars": 0,
        "error": None,
        "deep_thinking": deep_thinking,
    }
    try:
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
            note, tier_meta = await upload_pdf_and_chat(
                page, str(pdf.resolve()), prompt, deep_thinking=deep_thinking
            )
            await browser.close()
        text = note or ""
        out.write_text(text, encoding="utf-8")
        row["chars"] = len(text)
        row.update(tier_meta)
        row["model_label"] = tier_meta.get("tier_observed", "?")
        row["ok"] = len(text) >= 400
        tag = tier_meta.get("tier_observed", "深度思考" if deep_thinking else "快档")
        print(f"✅ yuanbao ({tag}) → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ yuanbao: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def run_doubao(
    pdf: Path, prompt: str, out: Path, *, model_label: str | None = None
) -> dict:
    t0 = time.time()
    row = {
        "channel": "doubao_brief",
        "ok": False,
        "chars": 0,
        "error": None,
        "model_label": model_label,
    }
    try:
        brief, _, tier_meta = await process_pdf_with_doubao(
            str(pdf),
            prompt,
            "silent",
            job="dev-brief",
            profile="./doubao_profile",
            model_label=model_label,
            structured_brief=False,
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row["chars"] = len(text)
        row["ok"] = len(text) >= 400
        row.update(tier_meta)
        row["model_label"] = tier_meta.get("tier_observed", model_label or "页面默认")
        tag = tier_meta.get("tier_observed", model_label or "页面默认")
        print(f"✅ doubao ({tag}) → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ doubao: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def compare_one(
    pdf: Path,
    paper_type: str,
    prompt: str,
    run_id: str,
    log_path: Path,
    *,
    skip_existing: bool,
    channels: list[str],
    gemini_model: str,
    doubao_model: str | None,
    yuanbao_deep_think: bool,
) -> list[dict]:
    stem = pdf.stem
    outs = {
        "gemini": _gemini_out_path(pdf, gemini_model),
        "yuanbao": _yuanbao_out_path(pdf, yuanbao_deep_think),
        "doubao_brief": _doubao_out_path(pdf, doubao_model),
    }
    runners = {
        "gemini": lambda o: run_gemini(pdf, prompt, o, model_label=gemini_model),
        "yuanbao": lambda o: run_yuanbao(pdf, prompt, o, deep_thinking=yuanbao_deep_think),
        "doubao_brief": lambda o: run_doubao(pdf, prompt, o, model_label=doubao_model),
    }
    rows: list[dict] = []
    for ch in channels:
        if ch not in outs:
            continue
        out = outs[ch]
        base = {
            "run_id": run_id,
            "pdf": str(pdf),
            "stem": stem,
            "paper_type": paper_type,
            "channel": ch,
            "prompt_version": "brief_open",
            "path": str(out),
        }
        if skip_existing and out.exists() and out.stat().st_size > 400:
            text = out.read_text(encoding="utf-8")
            row = {**base, "ok": True, "chars": len(text), "elapsed_sec": 0, "skipped": True}
            print(f"⏭️ {ch} 已有 {out.name} ({len(text)} 字)")
        else:
            print(f"\n===== {paper_type} / {ch} =====")
            row = {**base, **await runners[ch](out)}
        rows.append(row)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser(description="Round 2 开放导读比选")
    parser.add_argument("--pdf-dir", default="~/Desktop/PDFs")
    parser.add_argument("--pdf", action="append", help="单篇路径（可重复）")
    parser.add_argument("--paper-type", default=None, help="与 --pdf 联用")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--channels",
        default="gemini,yuanbao,doubao_brief",
        help="逗号分隔: gemini,yuanbao,doubao_brief",
    )
    parser.add_argument(
        "--gemini-model",
        default="3.5 Flash",
        help="Gemini 模型档，如 '3.5 Flash'、'3.1 Flash-Lite' 或 'Pro'",
    )
    parser.add_argument(
        "--doubao-model",
        default=None,
        help="豆包模型档，如 '快速' 或 '专家'；默认不传=页面当前",
    )
    parser.add_argument(
        "--yuanbao-deep-think",
        action="store_true",
        help="元宝开启深度思考（输出 _deepthink_open_ 文件）",
    )
    parser.add_argument("--list-defaults", action="store_true")
    args = parser.parse_args()

    if args.list_defaults:
        for t, name in ROUND2_PDFS:
            print(f"{t}\t{name}")
        return

    pdf_dir = Path(args.pdf_dir).expanduser()
    jobs: list[tuple[str, Path]] = []
    if args.pdf:
        for p in args.pdf:
            path = Path(p).expanduser().resolve()
            jobs.append((args.paper_type or "unknown", path))
    else:
        for paper_type, name in ROUND2_PDFS:
            path = pdf_dir / name
            if not path.exists():
                raise SystemExit(f"不存在: {path}")
            jobs.append((paper_type, path))

    prompt = _load_open_prompt()
    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== Round 2 开放导读 {run_id} =====")
    print(f"Prompt: brief_open.txt ({len(prompt)} 字)")
    print(f"篇数: {len(jobs)}  通道: {channels}")
    print(f"  Gemini: {args.gemini_model}  豆包: {args.doubao_model or '页面默认'}")
    print(f"  元宝深度思考: {'开' if args.yuanbao_deep_think else '关'}")
    print(f"日志: {log_path}\n")

    all_rows: list[dict] = []
    for paper_type, pdf in jobs:
        print(f"\n######## {pdf.name} ({paper_type}) ########")
        rows = asyncio.run(
            compare_one(
                pdf,
                paper_type,
                prompt,
                run_id,
                log_path,
                skip_existing=args.skip_existing,
                channels=channels,
                gemini_model=args.gemini_model,
                doubao_model=args.doubao_model,
                yuanbao_deep_think=args.yuanbao_deep_think,
            )
        )
        all_rows.extend(rows)

    summary = {
        "run_id": run_id,
        "prompt_version": "brief_open",
        "results": all_rows,
    }
    summary_path = LOG_DIR / f"run_{run_id}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 完成 {len(all_rows)} 条 → {summary_path}")


if __name__ == "__main__":
    main()
