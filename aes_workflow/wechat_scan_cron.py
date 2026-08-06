#!/usr/bin/env python3
"""wechat_scan_cron — 微信 DOI 持续自动扫描调度（§十余 §D50 落地）

两档定时（错峰，避免与 rss_aggregator/微信抓取并发冲突）：

  每日增量  --mode incremental
     只扫「最近一次成功扫描水位之后」、白名单命中池内、DOI 为空的 wechat_news。
     水位存 data/wechat_scan_state.json，跑完推进，不重扫历史。

  每周全量  --mode full
     不限 journal 白名单，翻页扫全部 wechat_news（DOI 为空）→ 兜底 + 补提历史漏网；
     跑完按库内 discovery_type='wechat_discovery' 的 DISTINCT journal 刷新命中池
     （增补 36 号之外新命中的号，§10.2b）。

OCR 已取消（用户裁定）——仅文本正则扫描 DOI/PMID，不做截图 OCR。

用法（cron）：
  python3 -m aes_workflow.wechat_scan_cron --mode incremental
  python3 -m aes_workflow.wechat_scan_cron --mode full

并发防护：data/wechat_scan.lock 目录锁，已存在则跳过本轮（防 cron 重入）。
日志：logs/wechat_scan.log。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "data" / "wechat_scan_state.json"
LOCK_DIR = ROOT / "data" / "wechat_scan.lock"
LOG_FILE = ROOT / "logs" / "wechat_scan.log"


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_lock() -> bool:
    """目录锁原子获取。返回 True=拿到锁，False=已有实例在跑。"""
    try:
        LOCK_DIR.mkdir(parents=True, exist_ok=False)
        return True
    except FileExistsError:
        return False


def release_lock() -> None:
    LOCK_DIR.rmdir()


def refresh_hit_pool() -> list[str]:
    """按库内 wechat_discovery 的 DISTINCT journal 刷新命中池（§10.2b 增补）。

    全量扫完自动把新命中的号并入 doi_scan_accounts，下次每日增量即可命中。
    返回增补后的完整命中池列表。
    """
    from aes_workflow.db import db_session
    from aes_workflow.doi_scan_config import get_doi_scan_accounts, set_doi_scan_accounts

    with db_session() as conn:
        rows = conn.execute(
            "SELECT DISTINCT journal FROM entries WHERE discovery_type='wechat_discovery' "
            "AND journal IS NOT NULL AND journal != ''"
        ).fetchall()
    hit_accounts = sorted({r["journal"] for r in rows})

    cur = set(get_doi_scan_accounts())
    merged = sorted(set(hit_accounts) | set(x for x in cur if x))
    if set(merged) != cur:
        set_doi_scan_accounts(merged)
        new = [x for x in hit_accounts if x not in cur]
        log(f"命中池增补: {len(new)} 个新号 {' '.join(new) if new else '(无)'}")
    else:
        log(f"命中池无变化（{len(merged)} 个）")
    return merged


def run_incremental() -> None:
    """每日增量：只扫水位之后、白名单内、DOI 为空的 wechat_news。"""
    from aes_workflow import wechat_prefilter

    state = load_state()
    watermark = state.get("last_incremental_ingest_at")
    log(f"[incremental] 起始水位: {watermark or '（无，从最新一批起扫）'}")

    # 用 db 里的最新 ingest_at 作为本次水位推进目标（扫描前先记，避免漏扫扫描期间的入库）
    from aes_workflow.db import db_session
    with db_session() as conn:
        cur = conn.execute(
            "SELECT MAX(ingest_at) AS mx FROM entries WHERE discovery_type='wechat_news'"
        ).fetchone()
        next_water = cur["mx"] if cur and cur["mx"] else watermark

    grand = {"scanned": 0, "found": 0, "no_id": 0, "fetch_failed": 0}
    cursor = None
    n = 0
    while True:
        stats = wechat_prefilter.scan_batch(cursor=cursor, min_ingest_at=watermark)
        for k in grand:
            grand[k] += int(stats.get(k, 0))
        n += 1
        if not stats.get("next_cursor") or stats.get("scanned", 0) == 0:
            break
        cursor = stats["next_cursor"]
    log(f"[incremental] 完成（{n} 批）: {grand}")

    if next_water:
        state["last_incremental_ingest_at"] = next_water
        save_state(state)
        log(f"[incremental] 水位推进到: {next_water}")


def run_full() -> None:
    """每周全量：不限白名单翻页扫全部 DOI 为空的 wechat_news，随后刷命中池。"""
    from aes_workflow import wechat_prefilter
    from aes_workflow.db import db_session

    # 全量前记当前 max ingest_at，作为本轮全量覆盖天花板（避免与增量水位打架，全量天然兜底）
    grand = {"scanned": 0, "found": 0, "no_id": 0, "fetch_failed": 0}
    cursor = None
    n = 0
    while True:
        stats = wechat_prefilter.scan_batch(cursor=cursor, full=True)
        for k in grand:
            grand[k] += int(stats.get(k, 0))
        n += 1
        if not stats.get("next_cursor") or stats.get("scanned", 0) == 0:
            break
        cursor = stats["next_cursor"]
    log(f"[full] 完成（{n} 批）: {grand}")

    # 刷命中池（增补新号）
    refresh_hit_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="微信 DOI 自动扫描（cron）")
    parser.add_argument("--mode", choices=["incremental", "full"], required=True,
                        help="incremental=每日增量(白名单+水位)；full=每周全量(不限白名单+增补命中池)")
    parser.add_argument("--refresh-hit-pool", action="store_true", help="仅刷命中池，不扫描")
    args = parser.parse_args()

    if not acquire_lock():
        log(f"⚠️ 已有扫描实例在跑（{LOCK_DIR} 锁存在），本轮跳过")
        sys.exit(0)

    try:
        if args.refresh_hit_pool:
            refresh_hit_pool()
            return
        if args.mode == "incremental":
            run_incremental()
        else:
            run_full()
    except Exception as e:
        import traceback
        log(f"❌ {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            release_lock()
        except OSError:
            pass


if __name__ == "__main__":
    main()
