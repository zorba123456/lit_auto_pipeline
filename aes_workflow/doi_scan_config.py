"""Persist DOI-scan account whitelist in config.json (wechat_rss project).

Detection:
- Can be toggled via 8388 dashboard (future)
- Read by wechat_prefilter to filter which accounts to scan
"""

from __future__ import annotations

import json
from pathlib import Path

# wechat_rss project config
CONFIG_PATH = Path.home() / "coding" / "wechat_rss" / "config.json"


def get_doi_scan_accounts() -> list[str]:
    """返回启用了 DOI 扫描的公众号名称列表。"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("doi_scan_accounts", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def set_doi_scan_accounts(accounts: list[str]) -> None:
    """写入 DOI 扫描白名单。"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}
    cfg["doi_scan_accounts"] = accounts
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
