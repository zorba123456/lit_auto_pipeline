#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单元测试: pipeline_patrol.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pipeline_patrol as patrol


class TestCheckLogChannel:
    def test_detects_stale_in_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patrol, 'LOG_DIR', str(tmp_path))
        (tmp_path / 'ktn.log').write_text(
            '=== [ktn] Start: Wed Jun 10 18:00:00 2026 ===\n'
            '[REPORT] CHANNEL=KTN ITEM=master_feed COUNT=1 STATUS=STALE\n'
            '=== [ktn] End: Wed Jun 10 18:00:10 2026 ===\n',
            encoding='utf-8',
        )
        findings = patrol.check_log_channel('KTN', 'ktn.log')
        assert any('STALE' in f for f in findings)

    def test_missing_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patrol, 'LOG_DIR', str(tmp_path))
        findings = patrol.check_log_channel('KTN', 'ktn.log')
        assert any('日志缺失' in f for f in findings)
