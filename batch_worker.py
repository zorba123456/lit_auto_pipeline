#!/usr/bin/env python3
"""L3 产线 batch_worker：DeepSeek 导读 + 豆包 / 元宝 AI 阅读外链。

定型（C37 + 双轨测试）：
  reading_note_zh   ← DeepSeek V4 Flash API
  doubao_read_url   ← 豆包 Web RPA · share-link · chip（可追问）
  yuanbao_read_url  ← 元宝 AI 阅读 RPA · deep-reading-detail 直链

用法:
  python3 batch_worker.py --article-key <64-hex>          # 导读 + 豆包（默认）
  python3 batch_worker.py --article-key <key> --with-yuanbao   # + 元宝 AI 阅读
  python3 batch_worker.py --article-key <key> --links-only   # 仅两条外链
  python3 batch_worker.py --article-key <key> --doubao-only
  python3 batch_worker.py --article-key <key> --yuanbao-only
  python3 batch_worker.py --article-key <key> --note-only
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
from aes_workflow.db import db_session, get_entry, update_entry_l3
from aes_workflow.paths import ROOT as WORKFLOW_ROOT
from aes_workflow.pdf_store import LocalPdfStore
from doubao_rpa import load_structured_prompt, process_pdf_with_doubao
from open_compare_api import API_MODELS, _call_deepseek, _extract_pdf_text, _user_message
from yuanbao_ai_read_rpa import process_pdf_ai_read

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


def run_yuanbao_ai_read(
    pdf: Path, *, profile: str, entry: str = "direct", timeout_sec: int = 300
) -> dict:
    t0 = time.time()
    row = {"task": "yuanbao_ai_read", "ok": False, "error": None}
    try:
        link = asyncio.run(
            process_pdf_ai_read(
                str(pdf.resolve()),
                profile=profile,
                entry=entry,
                timeout_sec=timeout_sec,
            )
        )
        if not link or not _is_valid_yuanbao_read_url(link):
            raise RuntimeError("未获取元宝 AI 阅读 deep-reading-detail 分享链")
        row.update({"ok": True, "yuanbao_read_url": link})
        print(f"✅ 元宝 AI 阅读 → {link[:60]}…")
    except Exception as e:
        row["error"] = str(e)
        print(f"❌ 元宝 AI 阅读: {e}")
    row["elapsed_sec"] = round(time.time() - t0, 1)
    return row


def _is_valid_yuanbao_read_url(url: str) -> bool:
    return "deep-reading-detail" in url and url.startswith("http")


def _should_skip_yuanbao(pdf: Path, skip_existing: bool) -> bool:
    if not skip_existing:
        return False
    m = _load_manifest(pdf)
    url = m.get("yuanbao_read_url") or ""
    return _is_valid_yuanbao_read_url(url)


def _should_skip_yuanbao_db(entry: dict | None, skip_existing: bool) -> bool:
    if not skip_existing or not entry:
        return False
    url = entry.get("yuanbao_read_url") or ""
    return _is_valid_yuanbao_read_url(url)


def _should_skip_doubao_db(entry: dict | None, skip_existing: bool) -> bool:
    if not skip_existing or not entry:
        return False
    url = entry.get("doubao_read_url") or ""
    return url.startswith("http")


def _should_skip_note_db(entry: dict | None, skip_existing: bool) -> bool:
    if not skip_existing or not entry:
        return False
    note = entry.get("reading_note_zh") or ""
    return len(note.strip()) >= 200


def resolve_pdf_for_article_key(article_key: str, db_path: Path | str | None = None) -> Path:
    with db_session(db_path) as conn:
        row = get_entry(conn, article_key)
    if row is None:
        raise KeyError(f"entries 中无 article_key: {article_key}")
    entry = dict(row)
    if entry.get("fulltext_status") != "PDF_HAS_FILE":
        raise FileNotFoundError(f"{article_key[:12]}… 尚无 PDF（fulltext_status={entry.get('fulltext_status')})")

    pdf_rel = entry.get("pdf_path") or ""
    if pdf_rel:
        pdf = (WORKFLOW_ROOT / pdf_rel).resolve()
        if pdf.is_file():
            return pdf

    store = LocalPdfStore()
    pdf = store.get(article_key)
    if pdf:
        return pdf.resolve()
    raise FileNotFoundError(f"找不到 PDF：{pdf_rel or article_key}")


def write_l3_to_db(
    article_key: str,
    manifest: dict,
    *,
    db_path: Path | str | None = None,
) -> None:
    note = manifest.get("reading_note_zh")
    doubao = manifest.get("doubao_read_url")
    yuanbao = manifest.get("yuanbao_read_url")
    status = manifest.get("reading_note_status")
    with db_session(db_path) as conn:
        update_entry_l3(
            conn,
            article_key,
            reading_note_zh=note if note else None,
            doubao_read_url=doubao if doubao else None,
            yuanbao_read_url=yuanbao if yuanbao else None,
            reading_note_status=status if status else None,
        )


def process_one_pdf(
    pdf: Path,
    *,
    prompt: str,
    profile: str,
    yuanbao_profile: str,
    yuanbao_entry: str,
    yuanbao_timeout: int,
    run_note: bool,
    run_doubao: bool,
    run_yuanbao: bool,
    skip_existing: bool,
    parallel: bool,
    article_key: str | None = None,
    db_path: Path | str | None = None,
    entry: dict | None = None,
) -> dict:
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)

    manifest = _load_manifest(pdf)
    manifest.setdefault("pdf", str(pdf))
    if article_key:
        manifest["article_key"] = article_key
    manifest["processed_at"] = _utc_now()

    skip_note = run_note and (
        _should_skip_note_db(entry, skip_existing) if article_key else _should_skip_note(pdf, skip_existing)
    )
    skip_doubao = run_doubao and (
        _should_skip_doubao_db(entry, skip_existing) if article_key else _should_skip_doubao(pdf, skip_existing)
    )
    skip_yuanbao = run_yuanbao and (
        _should_skip_yuanbao_db(entry, skip_existing) if article_key else _should_skip_yuanbao(pdf, skip_existing)
    )

    if skip_note:
        if article_key and entry:
            note_text = (entry.get("reading_note_zh") or "").strip()
        else:
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
            "doubao_read_url": (entry or {}).get("doubao_read_url") or manifest.get("doubao_read_url"),
        }
        url = doubao_row.get("doubao_read_url") or ""
        print(f"⏭️ 豆包链已有 {url[:50]}…")
    else:
        doubao_row = None

    if skip_yuanbao:
        yuanbao_row = {
            "task": "yuanbao_ai_read",
            "ok": True,
            "skipped": True,
            "yuanbao_read_url": (entry or {}).get("yuanbao_read_url") or manifest.get("yuanbao_read_url"),
        }
        url = yuanbao_row.get("yuanbao_read_url") or ""
        print(f"⏭️ 元宝 AI 阅读已有 {url[:50]}…")
    else:
        yuanbao_row = None

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

    # 元宝 AI 阅读单独开浏览器，不与豆包并行
    if run_yuanbao and not skip_yuanbao:
        yuanbao_row = run_yuanbao_ai_read(
            pdf,
            profile=yuanbao_profile,
            entry=yuanbao_entry,
            timeout_sec=yuanbao_timeout,
        )

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

    if yuanbao_row:
        if yuanbao_row.get("ok"):
            manifest["yuanbao_read_url"] = yuanbao_row.get("yuanbao_read_url")
            manifest["yuanbao_status"] = "yuanbao_complete"
        else:
            manifest["yuanbao_status"] = "yuanbao_failed"
        manifest["yuanbao_meta"] = {
            k: yuanbao_row.get(k) for k in ("elapsed_sec", "error", "skipped")
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

    if article_key:
        write_l3_to_db(article_key, manifest, db_path=db_path)
        print(f"💾 DB  → entries ({article_key[:12]}…)")

    return {
        "pdf": str(pdf),
        "article_key": article_key,
        "manifest": str(out_manifest),
        "reading_note": note_row,
        "doubao": doubao_row,
        "yuanbao": yuanbao_row,
        "ok": all(
            r.get("ok")
            for r in (note_row, doubao_row, yuanbao_row)
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
    parser = argparse.ArgumentParser(description="L3 batch_worker：导读 + 豆包 / 元宝 AI 阅读外链")
    parser.add_argument("--pdf", action="append", help="PDF 路径（可重复）")
    parser.add_argument("--article-key", action="append", help="entries.article_key（可重复）")
    parser.add_argument("--db", default=str(WORKFLOW_ROOT / "data" / "aes_workflow.db"))
    parser.add_argument(
        "--pdf-dir",
        default=None,
        help="扫描目录（默认 ~/Desktop/PDFs，仅在未给 --article-key/--pdf 或显式传入时启用）",
    )
    parser.add_argument("--glob", dest="glob_pat", default="*.pdf")
    parser.add_argument("--profile", default="./doubao_profile", help="豆包 Chrome profile")
    parser.add_argument("--yuanbao-profile", default="./yuanbao_profile", help="元宝 Chrome profile")
    parser.add_argument(
        "--yuanbao-entry",
        choices=("direct", "home"),
        default="direct",
        help="元宝 AI 阅读入口：direct=书签URL; home=首页侧栏",
    )
    parser.add_argument("--yuanbao-timeout", type=int, default=600, help="元宝 AI 阅读解析超时秒数（含脑图）")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--sequential", action="store_true", help="导读与豆包串行（元宝始终串行）")
    parser.add_argument("--note-only", action="store_true", help="仅 DeepSeek 导读")
    parser.add_argument("--doubao-only", action="store_true", help="仅豆包 share-link")
    parser.add_argument("--yuanbao-only", action="store_true", help="仅元宝 AI 阅读 share-link")
    parser.add_argument("--links-only", action="store_true", help="仅豆包 + 元宝两条外链")
    parser.add_argument("--with-yuanbao", action="store_true", help="在默认任务上追加元宝 AI 阅读")
    args = parser.parse_args()

    mode_flags = sum(
        int(x)
        for x in (args.note_only, args.doubao_only, args.yuanbao_only, args.links_only)
    )
    if mode_flags > 1:
        raise SystemExit("不能同时指定多种 --*-only / --links-only 模式")

    load_api_compare_env()

    if args.links_only:
        run_note, run_doubao, run_yuanbao = False, True, True
    elif args.note_only:
        run_note, run_doubao, run_yuanbao = True, False, False
    elif args.doubao_only:
        run_note, run_doubao, run_yuanbao = False, True, False
    elif args.yuanbao_only:
        run_note, run_doubao, run_yuanbao = False, False, True
    else:
        run_note, run_doubao, run_yuanbao = True, True, False
        if args.with_yuanbao:
            run_yuanbao = True

    prompt = load_structured_prompt("open")

    jobs: list[tuple[Path, str | None, dict | None]] = []

    if args.article_key:
        for key in args.article_key:
            key = key.strip().lower()
            with db_session(args.db) as conn:
                row = get_entry(conn, key)
            if row is None:
                raise SystemExit(f"无此 article_key: {key}")
            entry = dict(row)
            pdf = resolve_pdf_for_article_key(key, args.db)
            jobs.append((pdf, key, entry))

    explicit_pdfs = [Path(p).expanduser() for p in args.pdf] if args.pdf else []

    # 仅在以下情况扫描目录：
    #   1) 用户显式传了 --pdf-dir，或
    #   2) 既没给 --article-key 也没给 --pdf（保留旧的纯目录扫描默认行为）
    scan_dir: Path | None = None
    if args.pdf_dir is not None:
        scan_dir = Path(args.pdf_dir).expanduser()
    elif not args.article_key and not args.pdf:
        scan_dir = Path("~/Desktop/PDFs").expanduser()

    if scan_dir is not None or explicit_pdfs:
        pdfs = collect_pdfs(
            scan_dir if scan_dir is not None else Path("~/Desktop/PDFs").expanduser(),
            [args.glob_pat],
            explicit_pdfs,
        )
        for pdf in pdfs:
            jobs.append((pdf, None, None))

    if not jobs:
        raise SystemExit("未找到任务（用 --article-key 或 --pdf 或 --pdf-dir + --glob）")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{run_id}.jsonl"

    print(f"===== batch_worker {run_id} =====")
    print(f"导读: {NOTE_MODEL if run_note else '跳过'}")
    print(f"豆包: share-link @ {args.profile if run_doubao else '跳过'}")
    print(
        f"元宝: AI阅读 @ {args.yuanbao_profile if run_yuanbao else '跳过'}"
        + (f" entry={args.yuanbao_entry}" if run_yuanbao else "")
    )
    print(f"模式: {'串行' if args.sequential else '并行'}")
    print(f"日志: {log_path}\n")

    for pdf, article_key, entry in jobs:
        label = article_key[:12] + "…" if article_key else pdf.name
        print(f"\n######## {label} ########")
        row = {
            "run_id": run_id,
            **process_one_pdf(
                pdf,
                prompt=prompt,
                profile=args.profile,
                yuanbao_profile=args.yuanbao_profile,
                yuanbao_entry=args.yuanbao_entry,
                yuanbao_timeout=args.yuanbao_timeout,
                run_note=run_note,
                run_doubao=run_doubao,
                run_yuanbao=run_yuanbao,
                skip_existing=args.skip_existing,
                parallel=not args.sequential,
                article_key=article_key,
                db_path=args.db,
                entry=entry,
            ),
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成 → {log_path}")


if __name__ == "__main__":
    main()
