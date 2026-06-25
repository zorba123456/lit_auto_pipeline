#!/usr/bin/env python3
"""三通道导读比选：Gemini / 元宝 / 豆包 dev-brief（串行，统一 prompt）。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from doubao_rpa import load_structured_prompt, process_pdf_with_doubao


PROMPT_MARKERS = ("读者视角：临床问题", "## AES 中文表述规范", "你是医美与整形外科")
LOG_DIR = Path("logs/three_channel_compare")


def _no_prompt_leak(text: str) -> bool:
    return not any(m in text for m in PROMPT_MARKERS)


async def run_gemini(pdf: Path, out: Path) -> dict:
    from gemini_rpa import process_pdf_with_gemini

    t0 = time.time()
    row = {"channel": "gemini", "ok": False, "reading_note_len": 0, "error": None}
    try:
        brief, share, tier_meta = await process_pdf_with_gemini(
            str(pdf), verify_share_extract=False
        )
        note = brief or ""
        row.update(tier_meta)
        row["reading_note_len"] = len(note)
        row["ok"] = len(note) >= 80 and _no_prompt_leak(note)
        row["share_url"] = share
        row["prompt_leaked"] = not _no_prompt_leak(note)
        with open(out, "w", encoding="utf-8") as f:
            f.write(note)
        print(f"✅ gemini → {out} ({len(note)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ gemini: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def run_yuanbao(pdf: Path, prompt: str, out: Path) -> dict:
    from yuanbao_rpa import upload_pdf_and_chat
    from playwright.async_api import async_playwright

    t0 = time.time()
    row = {"channel": "yuanbao", "ok": False, "reading_note_len": 0, "error": None}
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
            note, tier_meta = await upload_pdf_and_chat(page, str(pdf.resolve()), prompt)
            await browser.close()
        row.update(tier_meta)
        note = note or ""
        row["reading_note_len"] = len(note)
        row["ok"] = len(note) >= 80 and _no_prompt_leak(note)
        row["prompt_leaked"] = not _no_prompt_leak(note)
        with open(out, "w", encoding="utf-8") as f:
            f.write(note)
        print(f"✅ yuanbao → {out} ({len(note)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ yuanbao: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def run_doubao_brief(pdf: Path, out: Path) -> dict:
    t0 = time.time()
    row = {"channel": "doubao_brief", "ok": False, "reading_note_len": 0, "error": None}
    try:
        prompt = load_structured_prompt("brief")
        brief, _, tier_meta = await process_pdf_with_doubao(
            str(pdf),
            prompt,
            "silent",
            job="dev-brief",
            profile="./doubao_profile",
        )
        note = brief or ""
        row.update(tier_meta)
        row["reading_note_len"] = len(note)
        row["ok"] = len(note) >= 80 and _no_prompt_leak(note)
        row["prompt_leaked"] = not _no_prompt_leak(note)
        with open(out, "w", encoding="utf-8") as f:
            f.write(note)
        print(f"✅ doubao_brief → {out} ({len(note)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ doubao_brief: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def compare_one(
    pdf: Path,
    *,
    channels: list[str],
    skip_existing: bool,
    paper_type: str,
    run_id: str,
    log_path: Path,
) -> list[dict]:
    stem = pdf.with_suffix("")
    prompt_version = "brief_rpa"
    rows: list[dict] = []

    targets = {
        "gemini": (stem.parent / f"{stem.name}_gemini_reading_note.txt", run_gemini),
        "yuanbao": (stem.parent / f"{stem.name}_yuanbao_reading_note.txt", None),
        "doubao_brief": (stem.parent / f"{stem.name}_doubao_brief_reading_note.txt", None),
    }

    prompt = load_structured_prompt("brief")

    for ch in channels:
        out, _ = targets[ch]
        base = {
            "run_id": run_id,
            "pdf": str(pdf),
            "stem": pdf.stem,
            "paper_type": paper_type,
            "channel": ch,
            "prompt_version": prompt_version,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if skip_existing and out.exists() and out.stat().st_size > 80:
            text = out.read_text(encoding="utf-8")
            row = {
                **base,
                "ok": len(text) >= 80 and _no_prompt_leak(text),
                "reading_note_len": len(text),
                "elapsed_sec": 0,
                "skipped": True,
                "error": None,
            }
            print(f"⏭️ {ch} 已有 {out.name} ({len(text)} 字)，跳过")
        elif ch == "gemini":
            row = {**base, **await run_gemini(pdf, out)}
        elif ch == "yuanbao":
            row = {**base, **await run_yuanbao(pdf, prompt, out)}
        elif ch == "doubao_brief":
            row = {**base, **await run_doubao_brief(pdf, out)}
        else:
            continue
        rows.append(row)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser(description="三通道导读比选（串行）")
    parser.add_argument("--pdf", required=True, help="单篇 PDF 路径")
    parser.add_argument(
        "--channels",
        default="gemini,yuanbao,doubao_brief",
        help="逗号分隔: gemini,yuanbao,doubao_brief",
    )
    parser.add_argument("--paper-type", default="review", choices=["review", "rct", "case"])
    parser.add_argument("--skip-existing", action="store_true", help="已有输出则跳过该通道")
    args = parser.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"不存在: {pdf}")

    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== 三通道比选 {run_id} =====")
    print(f"PDF: {pdf.name}")
    print(f"通道: {channels}")
    print(f"日志: {log_path}\n")

    rows = asyncio.run(
        compare_one(
            pdf,
            channels=channels,
            skip_existing=args.skip_existing,
            paper_type=args.paper_type,
            run_id=run_id,
            log_path=log_path,
        )
    )

    summary = {
        "run_id": run_id,
        "pdf": str(pdf),
        "channels": {r["channel"]: {"ok": r.get("ok"), "len": r.get("reading_note_len")} for r in rows},
    }
    summary_path = LOG_DIR / f"run_{run_id}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n===== 汇总 =====\n{json.dumps(summary, ensure_ascii=False, indent=2)}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
