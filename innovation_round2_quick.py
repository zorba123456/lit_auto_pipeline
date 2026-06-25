#!/usr/bin/env python3
"""创新性 Round 2 快测：遮 References + v2 prompt（强制 PMID）。

默认：HA JCD 2023 一篇；Gemini API 3.5 + DeepSeek API（无浏览器）。
可选：--gemini-web 走 Web RPA（上传去掉末页 ref 的 PDF）。

  python3 innovation_round2_quick.py
  python3 innovation_round2_quick.py --gemini-web
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path

from api_compare_env import load_api_compare_env
from pypdf import PdfReader, PdfWriter

HA_PDF = (
    "J of Cosmetic Dermatology - 2023 - Peng - Aspiration before tissue "
    "filling with hyaluronic acid‐safety enhancement by using.pdf"
)
LOG_DIR = Path("logs/innovation_round2")
GOLD_PMIDS = {
    "30624257": "Torbeck 2019 Dermatol Surg — HA aspiration delay",
    "32749775": "Kogan 2020 JCD — saline flashing",
    "34526796": "van Loghem 2021 Clin Cosmet Investig Dermatol — HA consensus",
}


def mask_pdf_drop_last_pages(src: Path, dst: Path, drop_last: int = 1) -> Path:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages[: max(1, len(reader.pages) - drop_last)]:
        writer.add_page(page)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as f:
        writer.write(f)
    return dst


def load_v2_prompt() -> str:
    p = Path("prompts/brief_innovation_audit_v2.txt")
    return p.read_text(encoding="utf-8").strip() + "\n"


def extract_pmids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b(\d{7,8})\b", text)))


def audit_output(text: str) -> dict:
    pmids = extract_pmids(text)
    gold_hit = {p: GOLD_PMIDS[p] for p in pmids if p in GOLD_PMIDS}
    gold_miss = [p for p in GOLD_PMIDS if p not in pmids]
    fake_risk = [p for p in pmids if p not in GOLD_PMIDS]
    return {
        "pmids_found": pmids,
        "gold_hit": gold_hit,
        "gold_miss": gold_miss,
        "other_pmids": fake_risk,
    }


def run_api(slug: str, pdf: Path, prompt: str, out: Path) -> dict:
    from open_compare_api import API_MODELS, _call_model, _extract_pdf_text, _user_message

    t0 = time.time()
    row = {"slug": slug, "ok": False, "chars": 0, "error": None}
    try:
        pdf_text = _extract_pdf_text(pdf)
        text, usage = _call_model(API_MODELS[slug], _user_message(prompt, pdf_text))
        out.write_text(text, encoding="utf-8")
        row.update({"ok": len(text) >= 200, "chars": len(text), "usage": usage, "audit": audit_output(text)})
        print(f"✅ {slug} → {out.name} ({len(text)} 字) audit={row['audit']}")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ {slug}: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def run_gemini_web(pdf: Path, prompt: str, out: Path) -> dict:
    from doubao_rpa import load_structured_prompt  # noqa: F401
    from gemini_rpa import process_pdf_with_gemini

    t0 = time.time()
    row = {"lane": "gemini_web", "ok": False, "chars": 0, "error": None}
    try:
        brief, _, meta = await process_pdf_with_gemini(
            str(pdf),
            prompt=prompt,
            model_label="3.5 Flash",
            verify_share_extract=False,
            structured_brief=False,
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row.update({"ok": len(text) >= 200, "chars": len(text), "tier_meta": meta, "audit": audit_output(text)})
        print(f"✅ gemini_web → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ gemini_web: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="创新性 Round2 快测（遮 ref）")
    parser.add_argument("--pdf-dir", default="~/Desktop/PDFs")
    parser.add_argument("--gemini-web", action="store_true", help="额外跑 Gemini Web RPA")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    load_api_compare_env()
    pdf_dir = Path(args.pdf_dir).expanduser()
    src = pdf_dir / HA_PDF
    if not src.exists():
        raise SystemExit(f"不存在: {src}")

    masked = pdf_dir / f"{src.stem}_no_refs.pdf"
    if not masked.exists() or masked.stat().st_mtime < src.stat().st_mtime:
        mask_pdf_drop_last_pages(src, masked, drop_last=1)
        print(f"已生成遮 ref PDF: {masked.name} ({len(PdfReader(str(masked)).pages)} 页)")

    prompt = load_v2_prompt()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"
    print(f"===== Round2 快测 {run_id} | 金标准 PMID: {list(GOLD_PMIDS)} =====\n")

    jobs = [
        ("gemini-3.5-flash", f"{src.stem}_innovation_v2_gemini35_api.txt"),
        ("deepseek-v4-flash", f"{src.stem}_innovation_v2_deepseek_api.txt"),
    ]
    for slug, out_name in jobs:
        out = pdf_dir / out_name
        if args.skip_existing and out.exists() and out.stat().st_size > 200:
            print(f"⏭️ {slug} 已有 {out.name}")
            continue
        row = run_api(slug, masked, prompt, out)
        row.update({"run_id": run_id, "pdf": str(masked), "prompt": "v2"})
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if args.gemini_web:
        out = pdf_dir / f"{src.stem}_innovation_v2_gemini35flash.txt"
        if not (args.skip_existing and out.exists() and out.stat().st_size > 200):
            row = asyncio.run(run_gemini_web(masked, prompt, out))
            row.update({"run_id": run_id, "pdf": str(masked), "prompt": "v2"})
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成 → {log_path}")


if __name__ == "__main__":
    main()
