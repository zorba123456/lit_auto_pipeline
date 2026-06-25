#!/usr/bin/env python3
"""豆包 chip 分享链 — 流程稳定性压测（不含自定义 prompt）。"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from doubao_rpa import CHIP_PROMPT, process_pdf_with_doubao


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


async def run_one(pdf_path: Path) -> dict:
    t0 = time.time()
    row = {
        "pdf": str(pdf_path),
        "basename": pdf_path.name,
        "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "chip_prompt": CHIP_PROMPT,
        "share_url": None,
        "ok_share": False,
        "error": None,
        "elapsed_sec": None,
    }
    try:
        _, share_url, _ = await process_pdf_with_doubao(
            str(pdf_path), mode="share", job="share-link"
        )
        row["share_url"] = share_url
        row["ok_share"] = bool(share_url)
        if share_url:
            stem = pdf_path.with_suffix("")
            with open(f"{stem}_stress_share.txt", "w", encoding="utf-8") as f:
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
        print(f"❌ 未找到 PDF: {pdf_dir}")
        return 1

    log_dir = Path(__file__).resolve().parent / "logs" / "doubao_stress"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = log_dir / f"run_{run_id}.jsonl"
    summary_path = log_dir / f"run_{run_id}_summary.json"

    print(f"===== 豆包 chip 压测 run_{run_id} =====")
    print(f"chip: {CHIP_PROMPT!r}")
    print(f"篇数: {len(pdfs)} | 策略: {args.strategy}")
    print(f"报告: {report_path}\n")

    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'='*60}\n[{i}/{len(pdfs)}] {pdf.name}\n{'='*60}")
        row = await run_one(pdf)
        results.append(row)
        with open(report_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"→ {'share✓' if row['ok_share'] else 'share✗'} | {row['elapsed_sec']}s")
        if row.get("share_url"):
            print(f"  {row['share_url']}")
        if row.get("error"):
            print(f"  error: {row['error']}")
        if i < len(pdfs):
            delay = random.uniform(args.delay_min, args.delay_max)
            print(f"⏸ 休眠 {delay:.0f}s …")
            await asyncio.sleep(delay)

    ok = sum(1 for r in results if r["ok_share"])
    summary = {
        "run_id": run_id,
        "job": "share-link",
        "chip_prompt": CHIP_PROMPT,
        "count": len(results),
        "ok_share": ok,
        "report": str(report_path),
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n===== 汇总: share {ok}/{len(results)} =====")
    print(f"summary: {summary_path}")
    return 0 if ok == len(results) else 1


def main():
    parser = argparse.ArgumentParser(description="豆包 chip 分享链压测")
    parser.add_argument("--pdf-dir", default="/Users/meiyiwangluokeji/Desktop/PDFs")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--strategy",
        choices=["smallest", "largest", "spread", "random"],
        default="smallest",
    )
    parser.add_argument("--delay-min", type=int, default=30)
    parser.add_argument("--delay-max", type=int, default=60)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
