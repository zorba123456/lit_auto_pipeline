#!/usr/bin/env python3
"""Gemini 导读 RPA 稳定性压测（brief + 3.5 Flash + share 抠字）。"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from gemini_rpa import process_pdf_with_gemini
from gemini_rpa_extract import DEFAULT_MODEL_LABEL


def pick_pdfs(pdf_dir: Path, limit: int, strategy: str) -> list[Path]:
    pdfs = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)
    if not pdfs:
        return []
    if strategy == "smallest":
        return pdfs[:limit]
    if strategy == "largest":
        return sorted(pdfs, key=lambda p: p.stat().st_size, reverse=True)[:limit]
    if strategy == "spread":
        if len(pdfs) <= limit:
            return pdfs
        step = max(1, len(pdfs) // limit)
        return [pdfs[i * step] for i in range(limit)]
    return random.sample(pdfs, min(limit, len(pdfs)))


PROMPT_MARKERS = ("读者视角：临床问题", "## AES 中文表述规范", "你是医美与整形外科")


def _pick_reading_note(session_brief: str, thread_brief: str) -> str:
    """优先 share 抠字；取较长且不含 prompt 的候选。"""
    candidates = [c for c in (thread_brief, session_brief) if c]
    clean = [c for c in candidates if not any(m in c for m in PROMPT_MARKERS)]
    pool = clean or candidates
    return max(pool, key=len) if pool else ""


async def run_one(pdf_path: Path, model: str) -> dict:
    t0 = time.time()
    row = {
        "pdf": str(pdf_path),
        "basename": pdf_path.name,
        "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
        "model": model,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "share_url": None,
        "session_brief_len": 0,
        "thread_brief_len": 0,
        "reading_note_len": 0,
        "ok_share": False,
        "ok_brief": False,
        "ok_thread_brief": False,
        "prompt_leaked": False,
        "error": None,
        "elapsed_sec": None,
    }
    try:
        from fetch_gemini_share_brief import fetch_gemini_share_brief

        brief, share_url = await process_pdf_with_gemini(
            str(pdf_path),
            model_label=model,
            verify_share_extract=False,
        )
        row["share_url"] = share_url
        row["session_brief_len"] = len(brief or "")
        row["ok_share"] = bool(share_url)
        row["ok_brief"] = len(brief or "") >= 80

        thread_brief = ""
        if share_url:
            thread_brief = await fetch_gemini_share_brief(share_url, headless=True)
            row["thread_brief_len"] = len(thread_brief or "")
            row["ok_thread_brief"] = len(thread_brief or "") >= 80

        final = _pick_reading_note(brief or "", thread_brief)
        row["reading_note_len"] = len(final)
        row["prompt_leaked"] = any(m in final for m in PROMPT_MARKERS)
        row["ok_brief"] = len(final) >= 80 and not row["prompt_leaked"]
        row["ok_thread_brief"] = len(thread_brief or "") >= 80

        stem = pdf_path.with_suffix("")
        if final:
            with open(f"{stem}_gemini_reading_note.txt", "w", encoding="utf-8") as f:
                f.write(final)
        if share_url:
            with open(f"{stem}_gemini_stress_share.txt", "w", encoding="utf-8") as f:
                f.write(share_url + "\n")
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def main_async(args):
    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    if not pdf_dir.is_dir():
        print(f"❌ 目录不存在: {pdf_dir}")
        return 1

    pdfs = pick_pdfs(pdf_dir, args.limit, args.strategy)
    if not pdfs:
        print(f"❌ 无 PDF: {pdf_dir}")
        return 1

    log_dir = Path(__file__).resolve().parent / "logs" / "gemini_stress"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = log_dir / f"run_{run_id}.jsonl"
    summary_path = log_dir / f"run_{run_id}_summary.json"

    print(f"===== Gemini 压测 run_{run_id} =====")
    print(f"模型: {args.model} | 篇数: {len(pdfs)} | 策略: {args.strategy}")
    print(f"⚠️ 首次运行需在弹出 Chrome 登录 Google / Gemini")
    print(f"报告: {report_path}\n")

    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'='*60}\n[{i}/{len(pdfs)}] {pdf.name}\n{'='*60}")
        row = await run_one(pdf, args.model)
        results.append(row)
        with open(report_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        flags = []
        flags.append("share✓" if row["ok_share"] else "share✗")
        flags.append("brief✓" if row["ok_brief"] else "brief✗")
        if row.get("prompt_leaked"):
            flags.append("prompt泄漏")
        print(f"→ {' | '.join(flags)} | {row['elapsed_sec']}s | 导读 {row['reading_note_len']} 字")
        if row.get("error"):
            print(f"  error: {row['error']}")
        if row.get("share_url"):
            print(f"  {row['share_url']}")

        if i < len(pdfs):
            delay = random.uniform(args.delay_min, args.delay_max)
            print(f"⏸ 休眠 {delay:.0f}s …")
            await asyncio.sleep(delay)

    ok_share = sum(1 for r in results if r["ok_share"])
    ok_brief = sum(1 for r in results if r["ok_brief"])
    summary = {
        "run_id": run_id,
        "model": args.model,
        "count": len(results),
        "ok_share": ok_share,
        "ok_brief": ok_brief,
        "ok_thread_brief": sum(1 for r in results if r["ok_thread_brief"]),
        "report": str(report_path),
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n===== 汇总: share {ok_share}/{len(results)} | 导读 {ok_brief}/{len(results)} =====")
    print(f"summary: {summary_path}")
    return 0 if ok_share == len(results) and ok_brief == len(results) else 1


def main():
    parser = argparse.ArgumentParser(description="Gemini RPA 压测")
    parser.add_argument("--pdf-dir", default="/Users/meiyiwangluokeji/Desktop/PDFs")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument(
        "--strategy",
        choices=["smallest", "largest", "spread", "random"],
        default="smallest",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--delay-min", type=int, default=45)
    parser.add_argument("--delay-max", type=int, default=90)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
