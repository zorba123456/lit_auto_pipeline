#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: aes-feeds/summary_reporter.py
覆盖所有视觉宽度计算、对齐函数、以及 [REPORT] 日志解析逻辑。
"""

import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aes-feeds'))

import summary_reporter as sr


# ─────────────────────────────────────────────
# get_visual_width
# ─────────────────────────────────────────────
class TestGetVisualWidth:
    def test_ascii_chars_width_1(self):
        assert sr.get_visual_width('hello') == 5

    def test_chinese_chars_width_2(self):
        # 每个中文字符视觉宽度为 2
        assert sr.get_visual_width('你好') == 4

    def test_mixed_chars(self):
        # 'A' (1) + '中' (2) = 3
        assert sr.get_visual_width('A中') == 3

    def test_empty_string_width_0(self):
        assert sr.get_visual_width('') == 0

    def test_space_width_1(self):
        assert sr.get_visual_width('   ') == 3

    def test_digits_width_1(self):
        assert sr.get_visual_width('12345') == 5

    def test_japanese_chars_width_2(self):
        # 日文片假名也应该是 2（ord > 0x7F）
        assert sr.get_visual_width('テスト') == 6


# ─────────────────────────────────────────────
# visual_ljust
# ─────────────────────────────────────────────
class TestVisualLjust:
    def test_pads_ascii_string(self):
        result = sr.visual_ljust('hi', 10)
        assert result == 'hi' + ' ' * 8
        assert len(result) == 10

    def test_pads_chinese_string(self):
        # '你好' 视觉宽度 4，要填充到 8，需要补 4 个空格
        result = sr.visual_ljust('你好', 8)
        assert result == '你好' + ' ' * 4

    def test_no_pad_when_already_wide(self):
        # 字符串已超过宽度，不截断，直接返回
        result = sr.visual_ljust('hello world', 5)
        assert result == 'hello world'

    def test_exact_width_no_padding(self):
        result = sr.visual_ljust('hello', 5)
        assert result == 'hello'

    def test_custom_fill_char(self):
        result = sr.visual_ljust('hi', 6, fillchar='-')
        assert result == 'hi----'


# ─────────────────────────────────────────────
# visual_rjust
# ─────────────────────────────────────────────
class TestVisualRjust:
    def test_pads_ascii_string_on_left(self):
        result = sr.visual_rjust('hi', 10)
        assert result == ' ' * 8 + 'hi'

    def test_pads_chinese_string_on_left(self):
        # '你好' 视觉宽度 4，填充到 8
        result = sr.visual_rjust('你好', 8)
        assert result == ' ' * 4 + '你好'

    def test_no_pad_when_already_wide(self):
        result = sr.visual_rjust('hello world', 5)
        assert result == 'hello world'

    def test_exact_width_no_padding(self):
        result = sr.visual_rjust('hello', 5)
        assert result == 'hello'


# ─────────────────────────────────────────────
# parse_latest_run_reports
# ─────────────────────────────────────────────
class TestParseLatestRunReports:
    def _write_log(self, tmp_path, content):
        log_file = tmp_path / 'test_new.log'
        log_file.write_text(content, encoding='utf-8')
        return str(log_file)

    def test_parses_single_report(self, tmp_path):
        content = """=== [lww] Start (v1.0): Thu May 28 00:00:00 2026 ===
[REPORT] CHANNEL=LWW ITEM=prs_current_issue COUNT=42 STATUS=SUCCESS
=== [lww] End (v1.0): Thu May 28 00:01:00 2026 ===
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert len(reports) == 1
        assert reports[0]['channel'] == 'LWW'
        assert reports[0]['item'] == 'prs_current_issue'
        assert reports[0]['count'] == 42
        assert reports[0]['status'] == 'SUCCESS'

    def test_parses_multiple_reports(self, tmp_path):
        content = """=== [lww] Start (v1.0): Thu May 28 00:00:00 2026 ===
[REPORT] CHANNEL=LWW ITEM=prs_current_issue COUNT=42 STATUS=SUCCESS
[REPORT] CHANNEL=LWW ITEM=aswc_latest COUNT=0 STATUS=FAIL
[REPORT] CHANNEL=LWW ITEM=annals_plast_surg COUNT=15 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert len(reports) == 3

    def test_only_returns_latest_run(self, tmp_path):
        content = """=== [lww] Start (v1.0): old run ===
[REPORT] CHANNEL=LWW ITEM=old_item COUNT=999 STATUS=SUCCESS
=== [lww] Start (v1.0): new run ===
[REPORT] CHANNEL=LWW ITEM=new_item COUNT=5 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        # 只解析最后一个 Start 之后的内容
        assert len(reports) == 1
        assert reports[0]['item'] == 'new_item'
        assert reports[0]['count'] == 5

    def test_returns_empty_when_no_start_marker(self, tmp_path):
        content = "[REPORT] CHANNEL=LWW ITEM=prs COUNT=10 STATUS=SUCCESS\n"
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert reports == []

    def test_returns_empty_for_missing_file(self, tmp_path):
        reports = sr.parse_latest_run_reports(str(tmp_path / 'nonexistent.log'))
        assert reports == []

    def test_count_parsed_as_int(self, tmp_path):
        content = """=== Start ===
[REPORT] CHANNEL=CNKI ITEM=期刊名 COUNT=123 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert isinstance(reports[0]['count'], int)
        assert reports[0]['count'] == 123

    def test_fail_status_parsed(self, tmp_path):
        content = """=== Start ===
[REPORT] CHANNEL=KTN ITEM=rhinoplasty COUNT=0 STATUS=FAIL
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert reports[0]['status'] == 'FAIL'

    def test_handles_item_with_spaces_in_name(self, tmp_path):
        """ITEM 字段可以包含非空白内容（用空白分隔各字段）"""
        content = """=== Start ===
[REPORT] CHANNEL=CNKI ITEM=中华整形外科杂志 COUNT=10 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert len(reports) == 1
        assert reports[0]['item'] == '中华整形外科杂志'

    def test_mixed_success_and_fail(self, tmp_path):
        content = """=== Start ===
[REPORT] CHANNEL=LWW ITEM=journal_a COUNT=10 STATUS=SUCCESS
[REPORT] CHANNEL=LWW ITEM=journal_b COUNT=0 STATUS=FAIL
[REPORT] CHANNEL=CMA ITEM=皮肤科 COUNT=5 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        statuses = [r['status'] for r in reports]
        assert 'SUCCESS' in statuses
        assert 'FAIL' in statuses

    def test_zero_count_in_success(self, tmp_path):
        content = """=== Start ===
[REPORT] CHANNEL=LWW ITEM=empty_journal COUNT=0 STATUS=SUCCESS
"""
        log_path = self._write_log(tmp_path, content)
        reports = sr.parse_latest_run_reports(log_path)
        assert reports[0]['count'] == 0
        assert reports[0]['status'] == 'SUCCESS'


# ─────────────────────────────────────────────
# print_summary_table (烟雾测试 - 不崩溃即可)
# ─────────────────────────────────────────────
class TestPrintSummaryTable:
    def test_does_not_raise_on_empty(self, capsys):
        sr.print_summary_table([])
        captured = capsys.readouterr()
        # 表格应该至少打印了边框
        assert '┌' in captured.out or '─' in captured.out

    def test_does_not_raise_on_success_reports(self, capsys):
        reports = [
            {'channel': 'LWW', 'item': 'prs_current_issue', 'count': 42, 'status': 'SUCCESS'},
            {'channel': 'CNKI', 'item': '中华整形外科杂志', 'count': 5, 'status': 'SUCCESS'},
        ]
        sr.print_summary_table(reports)
        captured = capsys.readouterr()
        assert 'LWW' in captured.out
        assert 'CNKI' in captured.out
        assert '42' in captured.out

    def test_does_not_raise_on_fail_reports(self, capsys):
        reports = [
            {'channel': 'KTN', 'item': 'rhinoplasty', 'count': 0, 'status': 'FAIL'},
        ]
        sr.print_summary_table(reports)
        captured = capsys.readouterr()
        assert 'KTN' in captured.out
        assert 'FAIL' in captured.out

    def test_total_count_in_output(self, capsys):
        reports = [
            {'channel': 'LWW', 'item': 'a', 'count': 10, 'status': 'SUCCESS'},
            {'channel': 'LWW', 'item': 'b', 'count': 20, 'status': 'SUCCESS'},
        ]
        sr.print_summary_table(reports)
        captured = capsys.readouterr()
        # 汇总中应该显示总数 30
        assert '30' in captured.out
