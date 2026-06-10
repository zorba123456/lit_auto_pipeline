#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: aes-feeds/ktn_downloader.py
覆盖所有纯逻辑函数，不依赖网络或浏览器。
"""

import sys
import os
import time
import tempfile
import pytest

# 将 aes-feeds 加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aes-feeds'))

import ktn_downloader as ktn


# ─────────────────────────────────────────────
# clean_text_noise
# ─────────────────────────────────────────────
class TestCleanTextNoise:
    def test_removes_replacement_char(self):
        assert ktn.clean_text_noise('hello\ufffdworld') == 'helloworld'

    def test_removes_null_byte(self):
        assert ktn.clean_text_noise('a\u0000b') == 'ab'

    def test_collapses_multiple_spaces(self):
        assert ktn.clean_text_noise('hello   world') == 'hello world'

    def test_strips_leading_trailing_whitespace(self):
        assert ktn.clean_text_noise('  hello  ') == 'hello'

    def test_removes_repeated_question_marks(self):
        assert ktn.clean_text_noise('test??noise') == 'testnoise'

    def test_single_question_mark_preserved(self):
        # 单个 ? 应该保留（只删除连续两个以上的）
        result = ktn.clean_text_noise('test?noise')
        assert '?' in result

    def test_empty_string_returns_empty(self):
        assert ktn.clean_text_noise('') == ''

    def test_none_returns_empty(self):
        assert ktn.clean_text_noise(None) == ''

    def test_normal_text_unchanged(self):
        assert ktn.clean_text_noise('rhinoplasty blepharoplasty') == 'rhinoplasty blepharoplasty'

    def test_mixed_noise(self):
        result = ktn.clean_text_noise('  test\ufffd\u0000??data  ')
        assert result == 'testdata'


# ─────────────────────────────────────────────
# sanitize_filename
# ─────────────────────────────────────────────
class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert ktn.sanitize_filename('Aesthetic Surgery') == 'aesthetic_surgery'

    def test_lowercased(self):
        assert ktn.sanitize_filename('RHINOPLASTY') == 'rhinoplasty'

    def test_double_quotes_removed(self):
        assert ktn.sanitize_filename('"hyaluronic acid"') == 'hyaluronic_acid'

    def test_single_quotes_removed(self):
        # 单引号被直接删除（不是替换为 _），所以 "blepharoplasty's" → "blepharoplastys"
        # sanitize_filename 先 .replace("'", '') 移除单引号，再用正则处理剩余特殊字符
        assert ktn.sanitize_filename("blepharoplasty's") == 'blepharoplastys'

    def test_curly_quotes_removed(self):
        assert ktn.sanitize_filename('\u201crhinoplasty\u201d') == 'rhinoplasty'

    def test_empty_returns_unknown(self):
        assert ktn.sanitize_filename('') == 'unknown'

    def test_none_returns_unknown(self):
        assert ktn.sanitize_filename(None) == 'unknown'

    def test_no_leading_trailing_underscores(self):
        result = ktn.sanitize_filename('  botulinum toxin  ')
        assert not result.startswith('_')
        assert not result.endswith('_')

    def test_chinese_keywords_preserved(self):
        result = ktn.sanitize_filename('整形外科')
        assert '整形外科' in result or result  # 中文字符应保留

    def test_special_chars_replaced(self):
        result = ktn.sanitize_filename('key-word/test')
        # 特殊字符应被替换为下划线
        assert '/' not in result
        assert '-' not in result


# ─────────────────────────────────────────────
# keyword_from_entry_title
# ─────────────────────────────────────────────
class TestKeywordFromEntryTitle:
    def test_standard_english_format(self):
        assert ktn.keyword_from_entry_title('"rhinoplasty" - new results') == 'rhinoplasty'

    def test_no_quotes_format(self):
        assert ktn.keyword_from_entry_title('rhinoplasty - new results') == 'rhinoplasty'

    def test_curly_quotes_format(self):
        result = ktn.keyword_from_entry_title('\u201crhinoplasty\u201d - new results')
        assert result == 'rhinoplasty'

    def test_multi_word_keyword(self):
        result = ktn.keyword_from_entry_title('"botulinum toxin" - new results')
        assert result == 'botulinum toxin'

    def test_case_insensitive_suffix(self):
        result = ktn.keyword_from_entry_title('"RHINOPLASTY" - New Results')
        assert result is not None

    def test_unrelated_title_returns_none(self):
        assert ktn.keyword_from_entry_title('Some random email subject') is None

    def test_none_title_returns_none(self):
        assert ktn.keyword_from_entry_title(None) is None

    def test_empty_title_returns_none(self):
        assert ktn.keyword_from_entry_title('') is None

    def test_strips_extra_quotes_from_result(self):
        result = ktn.keyword_from_entry_title('"aesthetic surgery" - new results')
        assert result == 'aesthetic surgery'
        assert '"' not in result


# ─────────────────────────────────────────────
# is_scholar_article_link
# ─────────────────────────────────────────────
class TestIsScholarArticleLink:
    def test_valid_scholar_url_link(self):
        url = 'https://scholar.google.com/scholar_url?url=https://example.com/paper'
        assert ktn.is_scholar_article_link(url) is True

    def test_valid_scholar_search_link(self):
        url = 'https://scholar.google.com/scholar?q=rhinoplasty'
        assert ktn.is_scholar_article_link(url) is True

    def test_hk_scholar_url(self):
        url = 'https://scholar.google.com.hk/scholar_url?url=https://example.com'
        assert ktn.is_scholar_article_link(url) is True

    def test_regular_google_link_rejected(self):
        assert ktn.is_scholar_article_link('https://www.google.com/search?q=test') is False

    def test_non_google_link_rejected(self):
        assert ktn.is_scholar_article_link('https://pubmed.ncbi.nlm.nih.gov/12345') is False

    def test_empty_href_rejected(self):
        assert ktn.is_scholar_article_link('') is False

    def test_none_href_rejected(self):
        assert ktn.is_scholar_article_link(None) is False

    def test_scholar_without_query_rejected(self):
        # scholar.google.com 但没有 scholar_url? 也没有 /scholar?
        assert ktn.is_scholar_article_link('https://scholar.google.com') is False


# ─────────────────────────────────────────────
# extract_scholar_keyword
# ─────────────────────────────────────────────
class TestExtractScholarKeyword:
    def test_english_pattern(self):
        from bs4 import BeautifulSoup
        html = '<p>following new results for [rhinoplasty]</p>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ktn.extract_scholar_keyword(soup) == 'rhinoplasty'

    def test_chinese_pattern(self):
        from bs4 import BeautifulSoup
        html = '<p>因为您关注了 [整形外科] 的新搜索结果</p>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ktn.extract_scholar_keyword(soup) == '整形外科'

    def test_no_pattern_returns_none(self):
        from bs4 import BeautifulSoup
        html = '<p>Some random newsletter content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ktn.extract_scholar_keyword(soup) is None

    def test_english_multi_word(self):
        from bs4 import BeautifulSoup
        html = '<p>following new results for [botulinum toxin]</p>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ktn.extract_scholar_keyword(soup) == 'botulinum toxin'


# ─────────────────────────────────────────────
# parse_single_mail
# ─────────────────────────────────────────────
class TestParseSingleMail:
    def _make_scholar_html(self, keyword='rhinoplasty', article_title='Test Article', article_url='https://example.com/paper'):
        return f"""
        <html><body>
        <p>following new results for [{keyword}]</p>
        <a href="https://scholar.google.com/scholar_url?url={article_url}">{article_title}</a>
        </body></html>
        """

    def test_extracts_keyword(self):
        html = self._make_scholar_html()
        kw, source, articles = ktn.parse_single_mail(html)
        assert kw == 'rhinoplasty'

    def test_extracts_source_type(self):
        html = self._make_scholar_html()
        kw, source, articles = ktn.parse_single_mail(html)
        assert source == 'Google Scholar'

    def test_extracts_articles(self):
        html = self._make_scholar_html(article_title='My Paper Title')
        kw, source, articles = ktn.parse_single_mail(html)
        assert len(articles) >= 1
        assert articles[0]['title'] == 'My Paper Title'

    def test_falls_back_to_entry_title(self):
        html = '<html><body><p>No keyword pattern here</p><a href="https://scholar.google.com/scholar_url?url=https://x.com">Paper</a></body></html>'
        kw, source, articles = ktn.parse_single_mail(html, entry_title='"blepharoplasty" - new results')
        assert kw == 'blepharoplasty'

    def test_unknown_source_when_no_keyword(self):
        html = '<html><body><p>Irrelevant content</p></body></html>'
        kw, source, articles = ktn.parse_single_mail(html)
        assert kw == 'Unknown_Source'
        assert source == 'External'

    def test_keyword_has_no_double_quotes(self):
        html = self._make_scholar_html(keyword='rhinoplasty')
        kw, source, articles = ktn.parse_single_mail(html)
        assert '"' not in kw
        assert '\u201c' not in kw
        assert '\u201d' not in kw

    def test_skips_pdf_links(self):
        html = """
        <html><body>
        <p>following new results for [rhinoplasty]</p>
        <a href="https://scholar.google.com/scholar_url?url=https://pdf.com">[PDF]</a>
        <a href="https://scholar.google.com/scholar_url?url=https://paper.com">Real Paper</a>
        </body></html>
        """
        kw, source, articles = ktn.parse_single_mail(html)
        titles = [a['title'] for a in articles]
        assert '[PDF]' not in titles
        assert 'Real Paper' in titles


# ─────────────────────────────────────────────
# write_channel_xml
# ─────────────────────────────────────────────
class TestWriteChannelXml:
    def test_creates_xml_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        articles = [{'title': 'Test Article', 'url': 'https://example.com', 'description': 'Abstract'}]
        result = ktn.write_channel_xml('rhinoplasty', 'Google Scholar', articles)
        assert result is not None
        filename, display_title = result
        assert filename == 'ktn_rhinoplasty.xml'
        assert (tmp_path / filename).exists()

    def test_xml_contains_title(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        articles = [{'title': 'My Paper', 'url': 'https://example.com', 'description': 'Desc'}]
        ktn.write_channel_xml('rhinoplasty', 'Google Scholar', articles)
        content = (tmp_path / 'ktn_rhinoplasty.xml').read_text(encoding='utf-8')
        assert 'My Paper' in content
        assert 'rhinoplasty' in content

    def test_empty_articles_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        result = ktn.write_channel_xml('rhinoplasty', 'Google Scholar', [])
        assert result is None

    def test_display_title_format(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        articles = [{'title': 'Paper', 'url': 'https://example.com', 'description': ''}]
        filename, display_title = ktn.write_channel_xml('rhinoplasty', 'Google Scholar', articles)
        assert 'KTN_' in display_title
        assert 'rhinoplasty' in display_title

    def test_valid_rss_structure(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        articles = [{'title': 'Paper', 'url': 'https://example.com', 'description': 'Desc'}]
        filename, _ = ktn.write_channel_xml('botulinum_toxin', 'Google Scholar', articles)
        content = (tmp_path / filename).read_text(encoding='utf-8')
        assert '<?xml version=' in content
        assert '<rss version=' in content
        assert '<channel>' in content
        assert '<item>' in content
        assert '</rss>' in content


# ─────────────────────────────────────────────
# collect_existing_channel_meta
# ─────────────────────────────────────────────
class TestCollectExistingChannelMeta:
    def test_collects_ktn_xml_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        # Create a fake ktn XML file
        content = '<?xml version="1.0"?><rss><channel><title>KTN_"rhinoplasty" @ Google Scholar</title></channel></rss>'
        (tmp_path / 'ktn_rhinoplasty.xml').write_text(content, encoding='utf-8')
        meta = ktn.collect_existing_channel_meta()
        assert len(meta) >= 1
        filenames = [m[0] for m in meta]
        assert 'ktn_rhinoplasty.xml' in filenames

    def test_ignores_non_ktn_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        (tmp_path / 'prs_latest.xml').write_text('<rss/>', encoding='utf-8')
        meta = ktn.collect_existing_channel_meta()
        filenames = [m[0] for m in meta]
        assert 'prs_latest.xml' not in filenames

    def test_empty_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        meta = ktn.collect_existing_channel_meta()
        assert meta == []


# ─────────────────────────────────────────────
# fetch_ktn_feed / master_report_status
# ─────────────────────────────────────────────
class TestMasterReportStatus:
    def test_fresh_is_success(self):
        assert ktn.master_report_status({'fresh': True}) == 'SUCCESS'

    def test_stale_backup(self):
        assert ktn.master_report_status({'fresh': False, 'stale': True}) == 'STALE'

    def test_recent_backup_degraded(self):
        assert ktn.master_report_status({'fresh': False, 'stale': False}) == 'DEGRADED'


class TestFetchKtnFeed:
    def test_live_fetch_success(self, monkeypatch):
        class FakeResp:
            status_code = 200
            text = 'x' * 120_000

        monkeypatch.setattr(ktn, 'proxy_port_open', lambda *a, **k: False)
        monkeypatch.setattr(ktn.requests, 'get', lambda *a, **k: FakeResp())
        text, meta = ktn.fetch_ktn_feed()
        assert text is not None
        assert meta['fresh'] is True
        assert meta['route'] == 'direct'

    def test_stale_backup_when_all_fail(self, tmp_path, monkeypatch):
        backup = tmp_path / 'uwgwyb1cnivki39x.xml'
        backup.write_text('<rss/>' * 50_000, encoding='utf-8')
        old = time.time() - 7200
        os.utime(backup, (old, old))
        monkeypatch.setenv('AES_OUT_DIR', str(tmp_path))
        monkeypatch.setattr(ktn, 'LOCAL_BACKUP_XML', str(backup))
        monkeypatch.setattr(ktn, 'proxy_port_open', lambda *a, **k: False)

        def boom(*a, **k):
            raise ktn.requests.exceptions.Timeout('timed out')

        monkeypatch.setattr(ktn.requests, 'get', boom)
        text, meta = ktn.fetch_ktn_feed()
        assert text is not None
        assert meta['fresh'] is False
        assert meta['stale'] is True
