#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: aes-feeds/cma_downloader.py
覆盖所有纯逻辑函数，不依赖浏览器或网络。
包含 V6.4.0 新增的增量指纹去重逻辑测试。
"""

import sys
import os
import json
import time
import tempfile
import hashlib
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aes-feeds'))

import cnki_downloader as cnki
import cma_downloader as cma


# ─────────────────────────────────────────────
# clean_text_noise (from cnki_downloader, shared utility)
# ─────────────────────────────────────────────
class TestCleanTextNoise:
    def test_removes_replacement_char(self):
        assert cnki.clean_text_noise('test\ufffddata') == 'testdata'

    def test_removes_null_byte(self):
        assert cnki.clean_text_noise('test\u0000data') == 'testdata'

    def test_collapses_whitespace(self):
        assert cnki.clean_text_noise('hello   world') == 'hello world'

    def test_strips_whitespace(self):
        assert cnki.clean_text_noise('  hello  ') == 'hello'

    def test_removes_multiple_question_marks(self):
        assert cnki.clean_text_noise('test??data') == 'testdata'

    def test_empty_string(self):
        assert cnki.clean_text_noise('') == ''

    def test_none_input(self):
        assert cnki.clean_text_noise(None) == ''

    def test_chinese_text_preserved(self):
        result = cnki.clean_text_noise('中华整形外科杂志')
        assert result == '中华整形外科杂志'


# ─────────────────────────────────────────────
# load_targets
# ─────────────────────────────────────────────
class TestLoadTargets:
    def test_loads_valid_json(self, tmp_path, monkeypatch):
        targets_file = tmp_path / 'cnki_targets.json'
        data = {"LCPF": {"name": "中华整形外科杂志", "rss_url": "https://example.com/rss"}}
        targets_file.write_text(json.dumps(data), encoding='utf-8')
        monkeypatch.setattr(cnki, 'TARGETS_JSON_PATH', str(targets_file))
        result = cnki.load_targets()
        assert 'LCPF' in result
        assert result['LCPF']['name'] == '中华整形外科杂志'

    def test_returns_empty_dict_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'TARGETS_JSON_PATH', str(tmp_path / 'nonexistent.json'))
        assert cnki.load_targets() == {}


# ─────────────────────────────────────────────
# load_dedup_log / save_dedup_log
# ─────────────────────────────────────────────
class TestDedupLog:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        log_file = tmp_path / 'cnki_dedup_log.json'
        monkeypatch.setattr(cnki, 'LOG_FILE_PATH', str(log_file))
        data = {'abc123': {'title': 'Test Paper', 'ts': time.time()}}
        cnki.save_dedup_log(data)
        loaded = cnki.load_dedup_log()
        assert 'abc123' in loaded
        assert loaded['abc123']['title'] == 'Test Paper'

    def test_load_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'LOG_FILE_PATH', str(tmp_path / 'nonexistent.json'))
        assert cnki.load_dedup_log() == {}

    def test_save_expires_old_entries(self, tmp_path, monkeypatch):
        log_file = tmp_path / 'cnki_dedup_log.json'
        monkeypatch.setattr(cnki, 'LOG_FILE_PATH', str(log_file))
        monkeypatch.setattr(cnki, 'DEDUP_EXPIRE_DAYS', 1)
        old_ts = time.time() - (91 * 86400)
        recent_ts = time.time() - 3600
        data = {
            'old_entry': {'title': 'Old Paper', 'ts': old_ts},
            'new_entry': {'title': 'New Paper', 'ts': recent_ts}
        }
        cnki.save_dedup_log(data)
        loaded = cnki.load_dedup_log()
        assert 'old_entry' not in loaded
        assert 'new_entry' in loaded

    def test_load_handles_corrupted_json(self, tmp_path, monkeypatch):
        log_file = tmp_path / 'cnki_dedup_log.json'
        log_file.write_text('THIS IS NOT VALID JSON!!!', encoding='utf-8')
        monkeypatch.setattr(cnki, 'LOG_FILE_PATH', str(log_file))
        result = cnki.load_dedup_log()
        assert result == {}


# ─────────────────────────────────────────────
# generate_rss_xml (CNKI)
# ─────────────────────────────────────────────
class TestGenerateRssXml:
    def _make_article(self, title='测试论文', url='https://cnki.example.com/article/1'):
        fp = hashlib.md5(f'{title}{url}'.replace(' ', '').encode('utf-8')).hexdigest()
        return {
            'fingerprint': fp,
            'title': title,
            'url': url,
            'author': '张三, 李四',
            'description': '这是摘要',
            'pubDate': 'Thu, 28 May 2026 00:00:00 GMT'
        }

    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        articles = [self._make_article()]
        filename = cnki.generate_rss_xml(articles, 'LCPF', '中华整形外科杂志')
        assert filename == 'cnki_lcpf.xml'
        assert (tmp_path / filename).exists()

    def test_filename_is_lowercase(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        articles = [self._make_article()]
        filename = cnki.generate_rss_xml(articles, 'MRYX', '某期刊')
        assert filename == 'cnki_mryx.xml'

    def test_xml_contains_article_title(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        articles = [self._make_article(title='特定论文标题')]
        cnki.generate_rss_xml(articles, 'LCPF', '期刊A')
        content = (tmp_path / 'cnki_lcpf.xml').read_text(encoding='utf-8')
        assert '特定论文标题' in content

    def test_valid_rss_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        articles = [self._make_article()]
        cnki.generate_rss_xml(articles, 'TEST', '测试期刊')
        content = (tmp_path / 'cnki_test.xml').read_text(encoding='utf-8')
        assert '<?xml version=' in content
        assert '<rss version=' in content
        assert '<channel>' in content
        assert '<item>' in content
        assert '</rss>' in content

    def test_multiple_articles(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        articles = [
            self._make_article(title='论文一', url='https://cnki.example.com/1'),
            self._make_article(title='论文二', url='https://cnki.example.com/2'),
            self._make_article(title='论文三', url='https://cnki.example.com/3'),
        ]
        cnki.generate_rss_xml(articles, 'MULTI', '多篇论文期刊')
        content = (tmp_path / 'cnki_multi.xml').read_text(encoding='utf-8')
        assert content.count('<item>') == 3


# ─────────────────────────────────────────────
# [V6.4.0 新增] CMA 增量指纹逻辑测试
# ─────────────────────────────────────────────
class TestCmaFingerprint:
    """测试 V6.4.0 新增的 MD5 链接指纹对比机制"""

    def test_same_links_produce_same_fingerprint(self):
        links = ['https://yiigle.com/1', 'https://yiigle.com/2']
        fp1 = cma._compute_links_fingerprint(links)
        fp2 = cma._compute_links_fingerprint(links)
        assert fp1 == fp2

    def test_different_links_produce_different_fingerprint(self):
        fp1 = cma._compute_links_fingerprint(['https://yiigle.com/1'])
        fp2 = cma._compute_links_fingerprint(['https://yiigle.com/2'])
        assert fp1 != fp2

    def test_order_independent_fingerprint(self):
        """链接顺序不同，指纹应相同（因为内部做了 sorted）"""
        fp1 = cma._compute_links_fingerprint(['https://a.com', 'https://b.com'])
        fp2 = cma._compute_links_fingerprint(['https://b.com', 'https://a.com'])
        assert fp1 == fp2

    def test_empty_links_fingerprint_stable(self):
        fp1 = cma._compute_links_fingerprint([])
        fp2 = cma._compute_links_fingerprint([])
        assert fp1 == fp2

    def test_read_fingerprint_from_xml(self, tmp_path):
        xml_content = '<?xml version="1.0"?>\n<!--CMA-FINGERPRINT:abcdef1234567890abcdef1234567890-->\n<rss/>'
        xml_file = tmp_path / 'test.xml'
        xml_file.write_text(xml_content, encoding='utf-8')
        result = cma._read_existing_fingerprint(str(xml_file))
        assert result == 'abcdef1234567890abcdef1234567890'

    def test_read_fingerprint_returns_empty_when_no_comment(self, tmp_path):
        xml_content = '<?xml version="1.0"?>\n<rss/>'
        xml_file = tmp_path / 'test.xml'
        xml_file.write_text(xml_content, encoding='utf-8')
        result = cma._read_existing_fingerprint(str(xml_file))
        assert result == ''

    def test_read_fingerprint_returns_empty_when_file_missing(self, tmp_path):
        result = cma._read_existing_fingerprint(str(tmp_path / 'nonexistent.xml'))
        assert result == ''

    def test_fingerprint_is_32_chars_hex(self):
        fp = cma._compute_links_fingerprint(['https://yiigle.com/article/1'])
        assert len(fp) == 32
        assert all(c in '0123456789abcdef' for c in fp)

    def test_fingerprint_embedded_in_xml_comment(self, tmp_path):
        """验证生成的 XML 注释格式与读取函数完全匹配"""
        import re
        links = ['https://yiigle.com/1', 'https://yiigle.com/2']
        fp = cma._compute_links_fingerprint(links)
        # 模拟写入 XML 注释
        xml_content = f'<?xml version="1.0"?>\n<!--CMA-FINGERPRINT:{fp}-->\n<rss/>'
        xml_file = tmp_path / 'test.xml'
        xml_file.write_text(xml_content, encoding='utf-8')
        # 读回应完全一致
        recovered = cma._read_existing_fingerprint(str(xml_file))
        assert recovered == fp


# ─────────────────────────────────────────────
# 去重逻辑集成测试
# ─────────────────────────────────────────────
class TestDedupLogic:
    def test_fingerprint_is_consistent(self):
        title = '测试论文'
        url = 'https://cnki.net/article/1'
        fp1 = hashlib.md5(f'{title}{url}'.replace(' ', '').encode('utf-8')).hexdigest()
        fp2 = hashlib.md5(f'{title}{url}'.replace(' ', '').encode('utf-8')).hexdigest()
        assert fp1 == fp2

    def test_different_articles_have_different_fingerprints(self):
        fp1 = hashlib.md5('论文A https://cnki.net/1'.replace(' ', '').encode('utf-8')).hexdigest()
        fp2 = hashlib.md5('论文B https://cnki.net/2'.replace(' ', '').encode('utf-8')).hexdigest()
        assert fp1 != fp2


# ─────────────────────────────────────────────
# parse_cnki_pubdate 测试
# ─────────────────────────────────────────────
class TestParseCnkiPubdate:
    def test_parse_valid_datetime(self):
        # 2026-05-12 07:15:34 (Beijing time UTC+8) -> 2026-05-11 23:15:34 (UTC)
        res = cnki.parse_cnki_pubdate("2026-05-12 07:15:34")
        assert res == "Mon, 11 May 2026 23:15:34 GMT"

    def test_parse_valid_date_only(self):
        # 2026-05-12 (Beijing time UTC+8) -> 2026-05-11 16:00:00 (UTC)
        res = cnki.parse_cnki_pubdate("2026-05-12")
        assert res == "Mon, 11 May 2026 16:00:00 GMT"

    def test_parse_page_range_returns_none(self):
        assert cnki.parse_cnki_pubdate("97-106") is None

    def test_parse_invalid_date_returns_none(self):
        assert cnki.parse_cnki_pubdate("not-a-date") is None

    def test_parse_empty_or_none_returns_none(self):
        assert cnki.parse_cnki_pubdate("") is None
        assert cnki.parse_cnki_pubdate(None) is None


# ─────────────────────────────────────────────
# generate_rss_xml 滚动历史测试
# ─────────────────────────────────────────────
class TestGenerateRssXmlRolling:
    def test_merges_existing_and_new_items(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        
        # 1. 产生初始 XML，有两条文献
        old_items = [
            {'title': '旧文献1', 'link': 'https://example.com/old1', 'description': 'desc1', 'pubDate': 'Mon, 11 May 2026 23:15:34 GMT'},
            {'title': '旧文献2', 'link': 'https://example.com/old2', 'description': 'desc2', 'pubDate': 'Mon, 11 May 2026 23:15:34 GMT'}
        ]
        cnki.generate_rss_xml(old_items, 'ROLL', '测试滚动期刊')
        
        # 2. 用两条新文献再次调用，其中一条与旧文献重复，一条是全新的
        new_items = [
            {'title': '新文献1', 'link': 'https://example.com/new1', 'description': 'desc_new1', 'pubDate': 'Tue, 12 May 2026 23:15:34 GMT'},
            {'title': '旧文献2', 'link': 'https://example.com/old2', 'description': 'desc2_updated', 'pubDate': 'Tue, 12 May 2026 23:15:34 GMT'}
        ]
        cnki.generate_rss_xml(new_items, 'ROLL', '测试滚动期刊')
        
        # 3. 读取合并后的 XML，验证去重和顺序
        import xml.etree.ElementTree as ET
        xml_file = tmp_path / 'cnki_roll.xml'
        assert xml_file.exists()
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        items = root.findall(".//item")
        
        # 应该包含：新文献1、旧文献2（已使用最新字段更新并排在前面）、旧文献1。共 3 条。
        assert len(items) == 3
        assert items[0].find('title').text == '新文献1'
        assert items[0].find('link').text == 'https://example.com/new1'
        assert items[1].find('title').text == '旧文献2'
        assert items[2].find('title').text == '旧文献1'

    def test_limits_items_to_30(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cnki, 'CURRENT_DIR', str(tmp_path))
        
        # 产生 35 条新文献
        items = []
        for i in range(35):
            items.append({
                'title': f'文献{i}',
                'link': f'https://example.com/{i}',
                'description': f'desc{i}',
                'pubDate': 'Mon, 11 May 2026 23:15:34 GMT'
            })
            
        cnki.generate_rss_xml(items, 'LIMIT', '限额测试期刊')
        
        # 读取 XML 验证只有 30 条
        import xml.etree.ElementTree as ET
        xml_file = tmp_path / 'cnki_limit.xml'
        assert xml_file.exists()
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        items_in_xml = root.findall(".//item")
        assert len(items_in_xml) == 30
        assert items_in_xml[0].find('title').text == '文献0'
        assert items_in_xml[29].find('title').text == '文献29'
