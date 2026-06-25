#!/usr/bin/env python3
"""英文文献 · 创新性交叉验证比选（各模型单档）。

Prompt: prompts/brief_innovation_audit.txt

档位（每模型家族 1 档）:
  gemini_web      3.5 Flash（Web，可触发 Google 检索）
  deepseek_api    deepseek-v4-flash（API）
  yuanbao_web     Deep Thinking
  doubao_web      快速

用法:
  python3 innovation_compare.py
  python3 innovation_compare.py --lanes deepseek_api --skip-existing
  python3 innovation_compare.py --list-lanes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path

from api_compare_env import load_api_compare_env
from doubao_rpa import load_structured_prompt, process_pdf_with_doubao

LOG_DIR = Path("logs/innovation_compare")

DEFAULT_PDFS = [
    "less_is_better__full_incision_double_eyelid.18.pdf",
    (
        "J of Cosmetic Dermatology - 2023 - Peng - Aspiration before tissue "
        "filling with hyaluronic acid‐safety enhancement by using.pdf"
    ),
]

# lane_id -> 配置
LANES: dict[str, dict] = {
    "gemini_web": {
        "label": "Gemini Web · 3.5 Flash",
        "channel": "gemini",
        "suffix": "gemini35flash",
        "kwargs": {"model_label": "3.5 Flash"},
    },
    "deepseek_api": {
        "label": "DeepSeek API · v4-flash",
        "channel": "api",
        "suffix": "deepseek_v4_flash",
        "kwargs": {"slug": "deepseek-v4-flash"},
    },
    "yuanbao_web": {
        "label": "元宝 Web · Deep Thinking",
        "channel": "yuanbao",
        "suffix": "yuanbao_dt",
        "kwargs": {"deep_thinking": True},
    },
    "doubao_web": {
        "label": "豆包 Web · 快速",
        "channel": "doubao",
        "suffix": "doubao_fast",
        "kwargs": {"model_label": "快速"},
    },
}


def _out_path(pdf: Path, suffix: str) -> Path:
    return pdf.parent / f"{pdf.stem}_innovation_{suffix}.txt"


async def _run_gemini_web(pdf: Path, prompt: str, out: Path, **kwargs) -> dict:
    from gemini_rpa import process_pdf_with_gemini

    t0 = time.time()
    row = {"lane": "gemini_web", "ok": False, "chars": 0, "error": None}
    try:
        brief, _, tier_meta = await process_pdf_with_gemini(
            str(pdf),
            prompt=prompt,
            model_label=kwargs["model_label"],
            verify_share_extract=False,
            structured_brief=False,
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row.update(tier_meta)
        row["chars"] = len(text)
        row["ok"] = len(text) >= 200
        print(f"✅ gemini_web → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ gemini_web: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def _run_yuanbao_web(pdf: Path, prompt: str, out: Path, **kwargs) -> dict:
    from playwright.async_api import async_playwright
    from yuanbao_rpa import upload_pdf_and_chat

    t0 = time.time()
    row = {"lane": "yuanbao_web", "ok": False, "chars": 0, "error": None}
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
                page,
                str(pdf.resolve()),
                prompt,
                deep_thinking=kwargs.get("deep_thinking", False),
            )
            await browser.close()
        text = note or ""
        out.write_text(text, encoding="utf-8")
        row.update(tier_meta)
        row["chars"] = len(text)
        row["ok"] = len(text) >= 200
        print(f"✅ yuanbao_web → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ yuanbao_web: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def _run_doubao_web(pdf: Path, prompt: str, out: Path, **kwargs) -> dict:
    t0 = time.time()
    row = {"lane": "doubao_web", "ok": False, "chars": 0, "error": None}
    try:
        brief, _, tier_meta = await process_pdf_with_doubao(
            str(pdf),
            prompt,
            "silent",
            job="dev-brief",
            profile="./doubao_profile",
            model_label=kwargs["model_label"],
            structured_brief=False,
            prompt_kind="innovation",
        )
        text = brief or ""
        out.write_text(text, encoding="utf-8")
        row.update(tier_meta)
        row["chars"] = len(text)
        row["ok"] = len(text) >= 200
        print(f"✅ doubao_web → {out.name} ({len(text)} 字)")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ doubao_web: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def _run_deepseek_api(pdf: Path, prompt: str, out: Path, **kwargs) -> dict:
    from open_compare_api import API_MODELS, _extract_pdf_text, _user_message, _call_model

    t0 = time.time()
    slug = kwargs["slug"]
    row = {"lane": "deepseek_api", "slug": slug, "ok": False, "chars": 0, "error": None}
    try:
        pdf_text = _extract_pdf_text(pdf)
        user_text = _user_message(prompt, pdf_text)
        text, usage = _call_model(API_MODELS[slug], user_text)
        out.write_text(text, encoding="utf-8")
        row["usage"] = usage
        row["chars"] = len(text)
        row["ok"] = len(text) >= 200
        print(f"✅ deepseek_api → {out.name} ({len(text)} 字) {usage}")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ deepseek_api: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


async def _run_lane(
    lane_id: str,
    pdf: Path,
    prompt: str,
    out: Path,
    *,
    skip_existing: bool,
) -> dict:
    cfg = LANES[lane_id]
    base = {
        "lane": lane_id,
        "label": cfg["label"],
        "pdf": str(pdf),
        "path": str(out),
        "prompt_version": "brief_innovation_audit",
    }
    if skip_existing and out.exists() and out.stat().st_size > 200:
        text = out.read_text(encoding="utf-8")
        print(f"⏭️ {lane_id} 已有 {out.name} ({len(text)} 字)")
        return {**base, "ok": True, "chars": len(text), "skipped": True}

    print(f"\n===== {cfg['label']} =====")
    ch = cfg["channel"]
    kw = cfg["kwargs"]
    if ch == "gemini":
        row = await _run_gemini_web(pdf, prompt, out, **kw)
    elif ch == "yuanbao":
        row = await _run_yuanbao_web(pdf, prompt, out, **kw)
    elif ch == "doubao":
        row = await _run_doubao_web(pdf, prompt, out, **kw)
    elif ch == "api":
        row = _run_deepseek_api(pdf, prompt, out, **kw)
    else:
        raise ValueError(ch)
    return {**base, **row}


def main() -> None:
    parser = argparse.ArgumentParser(description="创新性交叉验证比选")
    parser.add_argument("--pdf-dir", default="~/Desktop/PDFs")
    parser.add_argument("--pdf", action="append")
    parser.add_argument("--lanes", default=",".join(LANES))
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--list-lanes", action="store_true")
    args = parser.parse_args()

    if args.list_lanes:
        for lid, cfg in LANES.items():
            print(f"{lid:16} {cfg['label']}")
        return

    load_api_compare_env()
    lane_ids = [x.strip() for x in args.lanes.split(",") if x.strip()]
    for lid in lane_ids:
        if lid not in LANES:
            raise SystemExit(f"未知 lane: {lid}（--list-lanes）")

    pdf_dir = Path(args.pdf_dir).expanduser()
    pdfs = (
        [Path(p).expanduser() for p in args.pdf]
        if args.pdf
        else [pdf_dir / n for n in DEFAULT_PDFS]
    )
    prompt = load_structured_prompt("innovation")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== 创新性交叉验证 {run_id} =====")
    print(f"Prompt: brief_innovation_audit.txt ({len(prompt)} 字)")
    print(f"Lanes: {lane_ids}")
    print(f"日志: {log_path}\n")

    for pdf in pdfs:
        if not pdf.exists():
            raise SystemExit(f"不存在: {pdf}")
        print(f"\n######## {pdf.name} ########")
        for lid in lane_ids:
            out = _out_path(pdf, LANES[lid]["suffix"])
            row = asyncio.run(
                _run_lane(lid, pdf, prompt, out, skip_existing=args.skip_existing)
            )
            row["run_id"] = run_id
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成 → {log_path}")


if __name__ == "__main__":
    main()
