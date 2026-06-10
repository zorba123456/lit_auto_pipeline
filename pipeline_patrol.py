#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AES-INTEL 管线巡查哨兵：扫描日志与数据新鲜度，写入日记供观察期复盘。
"""

import glob
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
FEEDS_DIR = os.path.join(PROJECT_DIR, "aes-feeds")
DIARY_DIR = os.path.join(LOG_DIR, "patrol_diary")
KTN_BACKUP = os.path.join(FEEDS_DIR, "uwgwyb1cnivki39x.xml")

CHANNEL_LOGS = {
    "KTN": "ktn.log",
    "CMA": "cma.log",
    "CNKI": "cnki.log",
    "LWW": "lww.log",
}

REPORT_RE = re.compile(
    r"\[REPORT\] CHANNEL=(\S+)\s+ITEM=(.*?)\s+COUNT=(\d+)\s+STATUS=(\S+)"
)


def append_diary(lines):
    os.makedirs(DIARY_DIR, exist_ok=True)
    diary_path = os.path.join(DIARY_DIR, f"{datetime.now():%Y-%m-%d}.md")
    stamp = datetime.now().strftime("%H:%M:%S")
    block = [f"\n## {stamp} 巡查\n"] + [f"- {line}" for line in lines] + [""]
    with open(diary_path, "a", encoding="utf-8") as f:
        f.write("\n".join(block))
    return diary_path


def _read_tail(path, max_lines=400):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()[-max_lines:]


def _latest_run_slice(lines):
    start_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        if "===" in lines[idx] and "Start" in lines[idx]:
            start_idx = idx
            break
    return lines[start_idx:] if start_idx >= 0 else []


def check_log_channel(channel, log_name):
    findings = []
    path = os.path.join(LOG_DIR, log_name)
    if not os.path.exists(path):
        findings.append(f"🟡 {channel}: 日志缺失 ({log_name})")
        return findings

    latest = _latest_run_slice(_read_tail(path))
    if not latest:
        findings.append(f"🟡 {channel}: 未找到最近一次 Start 记录")
        return findings

    text = "".join(latest)
    if "Skipped" in text and "pipeline.lock" in text:
        findings.append(f"🟡 {channel}: 最近一次运行被 pipeline.lock 跳过")
    if "网络拉取异常" in text or "母流全部拉取路径失败" in text:
        findings.append(f"🔴 {channel}: 最近一次母流/网络拉取失败")
    if "Read timed out" in text:
        findings.append(f"🔴 {channel}: 检测到 Read timed out")
    if "STALE" in text:
        findings.append(f"🔴 {channel}: 检测到 STALE（已阻止过期推送）")
    if "DEGRADED" in text:
        findings.append(f"🟡 {channel}: 检测到 DEGRADED（使用较新备份）")

    reports = REPORT_RE.findall(text)
    fails = [r for r in reports if r[3] in ("FAIL", "STALE")]
    if fails:
        items = ", ".join(f"{it}({st})" for _, it, _, st in fails[:5])
        findings.append(f"🔴 {channel}: 子源异常 {len(fails)} 项: {items}")

    if not findings:
        ok = [r for r in reports if r[3] == "SUCCESS"]
        findings.append(f"🟢 {channel}: 最近一次运行未见异常 ({len(ok)} 项 SUCCESS)")
    return findings


def _newest_pubdate_from_feed_xml(path):
    try:
        tree = ET.parse(path)
        channel = tree.getroot().find("channel")
        if channel is None:
            return None
        dates = []
        for tag in ("lastBuildDate", "pubDate"):
            node = channel.find(tag)
            if node is not None and node.text:
                dates.append(node.text.strip())
        for item in channel.findall("item"):
            node = item.find("pubDate")
            if node is not None and node.text:
                dates.append(node.text.strip())
        return dates[0] if dates else None
    except Exception:
        return None


def check_cnki_rss_schedule():
    """白天应每 2h 有 CNKI RSS；日志过久未更新则告警。"""
    hour = datetime.now().hour
    if hour < 8 or hour > 22:
        return []
    path = os.path.join(LOG_DIR, "cnki.log")
    if not os.path.exists(path):
        return ["🔴 CNKI: 白天时段但 cnki.log 不存在"]
    age_h = (time.time() - os.path.getmtime(path)) / 3600
    if age_h > 3:
        return [f"🔴 CNKI: 白天 RSS 应每 2h 运行，日志已 {age_h:.1f}h 未更新"]
    return [f"🟢 CNKI: RSS 日志 {age_h:.1f}h 内更新（白天 2h 调度）"]


def check_ktn_freshness():
    findings = []
    if not os.path.exists(KTN_BACKUP):
        findings.append("🔴 KTN: 本地母流备份不存在")
        return findings

    age_h = (time.time() - os.path.getmtime(KTN_BACKUP)) / 3600
    if age_h > 1:
        findings.append(f"🔴 KTN: 母流备份已 {age_h:.1f}h 未更新")
    else:
        findings.append(f"🟢 KTN: 母流备份 {age_h:.1f}h 内更新")

    newest_sub = None
    for path in glob.glob(os.path.join(FEEDS_DIR, "ktn_*.xml")):
        pub = _newest_pubdate_from_feed_xml(path)
        if pub and (newest_sub is None or pub > newest_sub):
            newest_sub = pub
    if newest_sub:
        findings.append(f"ℹ️ KTN: 子流最新 pubDate ≈ {newest_sub}")
    return findings


def check_other_sources():
    """其他源的共性问题速查（观察期记录，暂不自动修复）。"""
    findings = []

    cnki_log = os.path.join(LOG_DIR, "cnki.log")
    if os.path.exists(cnki_log):
        tail = "".join(_read_tail(cnki_log, 200))
        if "抓取失败" in tail:
            findings.append("🟡 CNKI: RSS 模式近期有抓取失败记录")
        if "验证码" in tail or "captcha" in tail.lower():
            findings.append("🟡 CNKI: 近期触发验证码/人工介入")

    cma_log = os.path.join(LOG_DIR, "cma.log")
    if os.path.exists(cma_log):
        latest = "".join(_latest_run_slice(_read_tail(cma_log)))
        if "STATUS=FAIL" in latest:
            findings.append("🟡 CMA: 最近一次有子源 FAIL")

    lww_log = os.path.join(LOG_DIR, "lww.log")
    if os.path.exists(lww_log):
        latest = "".join(_latest_run_slice(_read_tail(lww_log)))
        if "STATUS=FAIL" in latest:
            findings.append("🟡 LWW: 最近一次有子源 FAIL")

    findings.append(
        "ℹ️ 共性问题提示: KTN 有 429 限流风险(请求过密); "
        "CNKI RSS timeout=15s 偏紧; CMA/LWW 受代理+浏览器稳定性影响"
    )
    return findings


def main():
    print("=" * 60)
    print(f"🔭 AES-INTEL 管线巡查  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    findings = []
    for channel, log_name in CHANNEL_LOGS.items():
        findings.extend(check_log_channel(channel, log_name))
    findings.extend(check_cnki_rss_schedule())
    findings.extend(check_ktn_freshness())
    findings.extend(check_other_sources())

    diary_path = append_diary(findings)
    print(f"\n📓 日记已写入: {diary_path}\n")
    for line in findings:
        print(line)
    print()

    if any(line.startswith("🔴") for line in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
