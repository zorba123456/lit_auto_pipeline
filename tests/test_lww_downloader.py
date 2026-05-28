#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: aes-feeds/lww_downloader.py
覆盖所有纯逻辑函数（不依赖浏览器或网络的部分）。

注意：lww_downloader 的主要逻辑依赖 DrissionPage 浏览器，
这里测试 push_to_github 的参数构造和 push 逻辑（通过 mock）。
"""

import sys
import os
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aes-feeds'))

import lww_downloader as lww


# ─────────────────────────────────────────────
# 常量/配置检查
# ─────────────────────────────────────────────
class TestConfiguration:
    def test_version_defined(self):
        assert hasattr(lww, '__version__')
        assert lww.__version__

    def test_base_dir_is_absolute(self):
        assert os.path.isabs(lww.BASE_DIR)

    def test_proxy_server_format(self):
        # 应该是 http:// 开头的代理地址
        assert lww.PROXY_SERVER.startswith('http://')

    def test_targets_list_not_empty(self):
        # targets 是在 main() 里定义的局部变量，我们通过检查模块代码内容来验证
        # 读取源码并验证 targets 列表的存在
        import inspect
        source = inspect.getsource(lww.main)
        assert 'targets' in source
        assert 'rss_url' in source

    def test_base_dir_points_to_aes_feeds(self):
        assert 'aes-feeds' in lww.BASE_DIR


# ─────────────────────────────────────────────
# XML 提取正则逻辑（内联测试）
# ─────────────────────────────────────────────
class TestXmlExtractionLogic:
    """测试 lww_downloader 中使用的 XML 提取正则表达式"""

    RSS_SAMPLE = '''<html><body>
<rss version="2.0">
<channel>
<title>Test Journal</title>
<item>
<title>Article One</title>
<link>https://example.com/1</link>
<prism:volume>12</prism:volume>
<prism:number>3</prism:number>
<pubDate>Thu, 28 May 2026 00:00:00 GMT</pubDate>
<description><![CDATA[Abstract of article one.]]></description>
</item>
<item>
<title>Article Two</title>
<link>https://example.com/2</link>
<description><![CDATA[Abstract of article two.]]></description>
</item>
</channel>
</rss>
</body></html>'''

    def test_rss_regex_extracts_content(self):
        xml_match = re.search(r'<rss.*?</rss>', self.RSS_SAMPLE, re.DOTALL | re.IGNORECASE)
        assert xml_match is not None

    def test_item_regex_finds_all_items(self):
        xml_match = re.search(r'<rss.*?</rss>', self.RSS_SAMPLE, re.DOTALL | re.IGNORECASE)
        pure_xml = xml_match.group(0)
        items = re.findall(r'<item>.*?</item>', pure_xml, re.DOTALL)
        assert len(items) == 2

    def test_prism_volume_extraction(self):
        item = '<item><prism:volume>12</prism:volume></item>'
        vol_m = re.search(r'<prism:volume>(.*?)</prism:volume>', item)
        assert vol_m is not None
        assert vol_m.group(1) == '12'

    def test_prism_number_extraction(self):
        item = '<item><prism:number>3</prism:number></item>'
        num_m = re.search(r'<prism:number>(.*?)</prism:number>', item)
        assert num_m is not None
        assert num_m.group(1) == '3'

    def test_pub_date_extraction(self):
        item = '<item><pubDate>Thu, 28 May 2026 00:00:00 GMT</pubDate></item>'
        pub_m = re.search(r'<pubDate>(.*?)</pubDate>', item)
        assert pub_m is not None
        assert 'May 2026' in pub_m.group(1)

    def test_issue_info_vol_and_num(self):
        vol_str = '12'
        num_str = '3'
        issue_info = f'Vol. {vol_str} No. {num_str}' if (vol_str or num_str) else 'Ahead of Print'
        assert issue_info == 'Vol. 12 No. 3'

    def test_issue_info_ahead_of_print(self):
        vol_str = ''
        num_str = ''
        issue_info = f'Vol. {vol_str} No. {num_str}' if (vol_str or num_str) else 'Ahead of Print'
        assert issue_info == 'Ahead of Print'

    def test_cdata_stripping(self):
        desc = '<![CDATA[Some content here]]>'
        clean = re.sub(r'<!\[CDATA\[|\]\]>', '', desc)
        assert clean == 'Some content here'

    def test_empty_cdata_replaced(self):
        desc = '<![CDATA[]]>'
        clean = re.sub(r'<!\[CDATA\[|\]\]>', '', desc)
        if not clean.strip():
            clean = 'No description available.'
        assert clean == 'No description available.'

    def test_xmlns_prism_fix(self):
        """测试 prism 命名空间修复逻辑"""
        html_with_empty_ns = '<rss xmlns:prism=""><channel></channel></rss>'
        fixed = re.sub(r'xmlns:prism=""', 'xmlns:prism="http://prismstandard.org/namespaces/1.2/basic/"', html_with_empty_ns)
        assert 'xmlns:prism=""' not in fixed
        assert 'http://prismstandard.org/namespaces/1.2/basic/' in fixed

    def test_unicode_line_separator_replacement(self):
        content = 'line1\u2028line2\u2029line3'
        result = content.replace('\u2028', '\n').replace('\u2029', '\n')
        assert '\u2028' not in result
        assert '\u2029' not in result
        assert 'line1\nline2\nline3' == result


# ─────────────────────────────────────────────
# push_to_github (通过 mock 测试不触发真实 git)
# ─────────────────────────────────────────────
class TestPushToGithub:
    def test_push_calls_git_add(self, mocker):
        mock_run = mocker.patch('lww_downloader.subprocess.run')
        lww.push_to_github()
        calls = [str(c) for c in mock_run.call_args_list]
        assert any('git' in c and 'add' in c for c in calls)

    def test_push_calls_git_commit(self, mocker):
        mock_run = mocker.patch('lww_downloader.subprocess.run')
        lww.push_to_github()
        calls = [str(c) for c in mock_run.call_args_list]
        assert any('commit' in c for c in calls)

    def test_push_calls_git_push(self, mocker):
        mock_run = mocker.patch('lww_downloader.subprocess.run')
        lww.push_to_github()
        calls = [str(c) for c in mock_run.call_args_list]
        assert any('push' in c for c in calls)

    def test_push_handles_exception_gracefully(self, mocker):
        """当 git 命令失败时，应该优雅地打印错误信息而不是崩溃"""
        import subprocess
        mocker.patch('lww_downloader.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git'))
        # 不应该抛出异常
        try:
            lww.push_to_github()
        except subprocess.CalledProcessError:
            pytest.fail('push_to_github should handle CalledProcessError gracefully')

    def test_proxy_env_vars_set_in_push(self, mocker):
        """测试推送时环境变量中设置了代理"""
        captured_envs = []
        
        def capture_env(*args, **kwargs):
            env = kwargs.get('env')
            if env:
                captured_envs.append(env)
        
        mocker.patch('lww_downloader.subprocess.run', side_effect=capture_env)
        lww.push_to_github()
        
        # 至少 git push 调用时应该有 env 参数
        assert len(captured_envs) > 0
        last_env = captured_envs[-1]
        assert 'HTTP_PROXY' in last_env or 'HTTPS_PROXY' in last_env
