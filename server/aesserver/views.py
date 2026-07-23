"""AES 中台 — 首页视图。"""
from django.shortcuts import render
from django.http import JsonResponse
from pathlib import Path
import sqlite3

WORKFLOW_ROOT = Path(__file__).resolve().parent.parent.parent
AES_DB = WORKFLOW_ROOT / "data" / "aes_workflow.db"
FRESHRSS_DB = Path("/Users/meiyiwangluokeji/coding/freshrss/data/users/alnews/db.sqlite")


def index(request):
    """中台首页 — 状态总览。"""
    ctx = {"page": "dashboard"}
    # aes_workflow.db 计数
    try:
        conn = sqlite3.connect(str(AES_DB))
        aes_entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        aes_ids = conn.execute("SELECT COUNT(*) FROM entry_identifiers").fetchone()[0]
        aes_log = conn.execute("SELECT COUNT(*) FROM ingest_log").fetchone()[0]
        conn.close()
    except Exception:
        aes_entries = aes_ids = aes_log = -1

    # FreshRSS 计数
    try:
        fr = sqlite3.connect(str(FRESHRSS_DB))
        fr_entries = fr.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
        fr_feeds = fr.execute("SELECT COUNT(*) FROM feed").fetchone()[0]
        fr.close()
    except Exception:
        fr_entries = fr_feeds = -1

    ctx.update({
        "aes_entries": aes_entries,
        "aes_identifiers": aes_ids,
        "aes_ingest_log": aes_log,
        "fr_entries": fr_entries,
        "fr_feeds": fr_feeds,
    })
    return render(request, "aesserver/index.html", ctx)


def api_status(request):
    """JSON 状态 API（供 dashboard 或调试用）。"""
    try:
        conn = sqlite3.connect(str(AES_DB))
        aes_entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        conn.close()
    except Exception:
        aes_entries = -1
    try:
        fr = sqlite3.connect(str(FRESHRSS_DB))
        fr_entries = fr.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
        fr.close()
    except Exception:
        fr_entries = -1
    return JsonResponse({
        "aes_workflow": {"entries": aes_entries},
        "freshrss": {"entries": fr_entries},
        "bridge_needed": aes_entries == 0 and fr_entries > 0,
    })
