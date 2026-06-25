#!/usr/bin/env python3
"""L3 产线 batch_worker：DeepSeek API 导读 + 豆包 Web 深读链。

定型（C37）：
  reading_note_zh  ← DeepSeek V4 Flash API · pypdf 抽文本 · brief_open.txt
  doubao_read_url  ← 豆包 Web RPA · share-link · chip

用法:
  python3 batch_worker.py --pdf paper.pdf
  python3 batch_worker.py --pdf a.pdf --pdf b.pdf --skip-existing
  python3 batch_worker.py --pdf paper.pdf --note-only      # 仅导读 API
  python3 batch_worker.py --pdf paper.pdf --doubao-only    # 仅豆包链
  python3 batch_worker.py --sequential                   # 先导读后豆包（默认并行）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from api_compare_env import load_api_compare_env
from doubao_rpa import load_structured_prompt, process_pdf_with_doubao
from open_compare_api import API_MODELS, _call_deepseek, _extract_pdf_text, _user_message

LOG_DIR = Path("logs/batch_worker")
NOTE_MODEL = "deepseek-v4-flash"
MAX_NOTE_CHARS = 1000


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _note_path(pdf: Path) -> Path:
    return pdf.parent / f"{pdf.stem}_reading_note_zh.txt"


def _manifest_path(pdf: Path) -> Path:
    return pdf.parent / f"{pdf.stem}.aes_l3.json"


def _load_manifest(pdf: Path) -> dict:
    p = _manifest_path(pdf)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def truncate_note(text: str, limit: int = MAX_NOTE_CHARS) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("。", "！", "？", "\n\n"):
        idx = cut.rfind(sep)
        if idx > limit // 2:
            return cut[: idx + len(sep)].strip()
    return cut.rstrip() + "…"


def run_reading_note(pdf: Path, prompt: str) -> dict:
    t0 = time.time()
    row = {"task": "reading_note", "ok": False, "chars": 0, "error": None, "usage": {}}
    try:
        pdf_text = _extract_pdf_text(pdf)
        user_text = _user_message(prompt, pdf_text)
        spec = API_MODELS[NOTE_MODEL]
        raw, usage = _call_deepseek(spec, user_text)
        note = truncate_note(raw)
        out = _note_path(pdf)
        out.write_text(note, encoding="utf-8")
        row.update(
            {
                "ok": len(note) >= 200,
                "chars": len(note),
                "chars_raw": len(raw),
                "truncated": len(raw) > len(note),
                "usage": usage,
                "path": str(out),
                "pdf_text_chars": len(pdf_text),
            }
        )
        print(f"✅ 导读 → {out.name} ({len(note)} 字" + ("，已截断" if row["truncated"] else "") + ")")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ 导读: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def run_doubao_share(pdf: Path, profile: str) -> dict:
    t0 = time.time()
    row = {"task": "doubao_share", "ok": False, "error": None}
    try:
        _, share_link, tier_meta = asyncio.run(
            process_pdf_with_doubao(
                str(pdf.resolve()),
                mode="share",
                job="share-link",
                profile=profile,
            )
        )
        if not share_link:
            raise RuntimeError("未获取豆包分享链接")
        row.update(
            {
                "ok": True,
                "doubao_read_url": share_link,
                "tier_meta": tier_meta,
            }
        )
        print(f"✅ 豆包链 → {share_link[:60]}…")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ 豆包链: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def _should_skip_note(pdf: Path, skip_existing: bool) -> bool:
    if not skip_existing:
        return False
    out = _note_path(pdf)
    return out.is_file() and out.stat().st_size > 200


def _should_skip_doubao(pdf: Path, skip_existing: bool) -> bool:
    if not skip_existing:
        return False
    m = _load_manifest(pdf)
    url = m.get("doubao_read_url") or ""
    return bool(url.startswith("http"))


def process_one_pdf(
    pdf: Path,
    *,
    prompt: str,
    profile: str,
    run_note: bool,
    run_doubao: bool,
    skip_existing: bool,
    parallel: bool,
) -> dict:
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)

    manifest = _load_manifest(pdf)
    manifest.setdefault("pdf", str(pdf))
    manifest["processed_at"] = _utc_now()

    skip_note = run_note and _should_skip_note(pdf, skip_existing)
    skip_doubao = run_doubao and _should_skip_doubao(pdf, skip_existing)

    if skip_note:
        note_text = _note_path(pdf).read_text(encoding="utf-8")
        note_row = {
            "task": "reading_note",
            "ok": True,
            "skipped": True,
            "chars": len(note_text),
            "path": str(_note_path(pdf)),
        }
        print(f"⏭️ 导读已有 {_note_path(pdf).name} ({len(note_text)} 字)")
    else:
        note_row = None

    if skip_doubao:
        doubao_row = {
            "task": "doubao_share",
            "ok": True,
            "skipped": True,
            "doubao_read_url": manifest.get("doubao_read_url"),
        }
        print(f"⏭️ 豆包链已有 {manifest.get('doubao_read_url', '')[:50]}…")
    else:
        doubao_row = None

    t0 = time.time()

    if parallel and run_note and run_doubao and not skip_note and not skip_doubao:
        print("⚡ 并行：DeepSeek API + 豆包 Web")
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_note = pool.submit(run_reading_note, pdf, prompt)
            f_doubao = pool.submit(run_doubao_share, pdf, profile)
            note_row = f_note.result()
            doubao_row = f_doubao.result()
    else:
        if run_note and not skip_note:
            note_row = run_reading_note(pdf, prompt)
        if run_doubao and not skip_doubao:
            doubao_row = run_doubao_share(pdf, profile)

    if note_row:
        if note_row.get("ok"):
            manifest["reading_note_zh"] = _note_path(pdf).read_text(encoding="utf-8")
            manifest["reading_note_status"] = "note_complete"
        else:
            manifest["reading_note_status"] = "note_failed"
        manifest["reading_note_meta"] = {
            k: note_row.get(k)
            for k in ("chars", "chars_raw", "truncated", "usage", "elapsed_sec", "error", "skipped")
        }

    if doubao_row:
        if doubao_row.get("ok"):
            manifest["doubao_read_url"] = doubao_row.get("doubao_read_url")
            manifest["doubao_status"] = "doubao_complete"
        else:
            manifest["doubao_status"] = "doubao_failed"
        manifest["doubao_meta"] = {
            k: doubao_row.get(k)
            for k in ("elapsed_sec", "error", "skipped", "tier_meta")
        }

    manifest["elapsed_sec_total"] = round(time.time() - t0, 1)
    manifest["prompt"] = "brief_open.txt"
    manifest["note_model"] = NOTE_MODEL

    out_manifest = _manifest_path(pdf)
    out_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"📋 清单 → {out_manifest.name}")

    return {
        "pdf": str(pdf),
        "manifest": str(out_manifest),
        "reading_note": note_row,
        "doubao": doubao_row,
        "ok": all(
            r.get("ok")
            for r in (note_row, doubao_row)
            if r is not None
        ),
    }


def collect_pdfs(pdf_dir: Path, globs: list[str], explicit: list[Path]) -> list[Path]:
    if explicit:
        return explicit
    found: list[Path] = []
    for pattern in globs:
        found.extend(sorted(pdf_dir.glob(pattern)))
    return sorted({p.resolve() for p in found})


def main() -> None:
    parser = argparse.ArgumentParser(description="L3 batch_worker：导读 API + 豆包深读链")
    parser.add_argument("--pdf", action="append", help="PDF 路径（可重复）")
    parser.add_argument("--pdf-dir", default="~/Desktop/PDFs")
    parser.add_argument("--glob", dest="glob_pat", default="*.pdf")
    parser.add_argument("--profile", default="./doubao_profile", help="豆包 Chrome profile")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--sequential", action="store_true", help="串行（默认并行）")
    parser.add_argument("--note-only", action="store_true", help="仅 DeepSeek 导读")
    parser.add_argument("--doubao-only", action="store_true", help="仅豆包 share-link")
    args = parser.parse_args()

    if args.note_only and args.doubao_only:
        raise SystemExit("不能同时 --note-only 与 --doubao-only")

    load_api_compare_env()
    run_note = not args.doubao_only
    run_doubao = not args.note_only
    prompt = load_structured_prompt("open")

    pdfs = collect_pdfs(
        Path(args.pdf_dir).expanduser(),
        [args.glob_pat],
        [Path(p).expanduser() for p in args.pdf] if args.pdf else [],
    )
    if not pdfs:
        raise SystemExit("未找到 PDF（用 --pdf 或 --pdf-dir + --glob）")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== batch_worker {run_id} =====")
    print(f"导读: {NOTE_MODEL if run_note else '跳过'}")
    print(f"豆包: share-link @ {args.profile if run_doubao else '跳过'}")
    print(f"模式: {'串行' if args.sequential else '并行'}")
    print(f"日志: {log_path}\n")

    for pdf in pdfs:
        print(f"\n######## {pdf.name} ########")
        row = {
            "run_id": run_id,
            **process_one_pdf(
                pdf,
                prompt=prompt,
                profile=args.profile,
                run_note=run_note,
                run_doubao=run_doubao,
                skip_existing=args.skip_existing,
                parallel=not args.sequential,
            ),
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成 → {log_path}")


if __name__ == "__main__":
    main()
