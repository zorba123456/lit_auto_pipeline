"""三通道 RPA 档位识别 — 统一 tier 日志字段。"""

from __future__ import annotations

import re


def tiers_match(requested: str, observed: str, *, channel: str) -> bool:
    """requested 与 observed 是否一致（模糊匹配）。"""
    if not observed or observed in ("unknown", "?"):
        return False
    r = (requested or "").strip().lower()
    o = observed.strip().lower()
    if channel == "gemini":
        if "pro" in r:
            return "pro" in o
        if "flash" in r or "fast" in r:
            return "flash" in o or "fast" in o or "3.5" in o
        return r in o or o in r
    if channel == "doubao_brief":
        if "专家" in requested:
            return "专家" in observed
        if "快速" in (requested or ""):
            return "快速" in observed
        return True  # 未指定则不做强校验
    if channel == "yuanbao":
        want_dt = "深度思考" in (requested or "")
        if want_dt:
            return "深度思考" in observed and "未确认" not in observed
        return "DT关" in observed
    return r in o or o in r


def make_tier_meta(
    *,
    channel: str,
    tier_requested: str,
    tier_observed: str,
    extra: dict | None = None,
) -> dict:
    verified = tiers_match(tier_requested, tier_observed, channel=channel)
    meta = {
        "tier_requested": tier_requested,
        "tier_observed": tier_observed,
        "tier_verified": verified,
    }
    if extra:
        meta.update(extra)
    label = f"{'✓' if verified else '?'} {tier_observed} (要 {tier_requested})"
    print(f"📊 档位确认 [{channel}]: {label}")
    return meta
