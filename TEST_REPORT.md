# AES-INTEL 项目集成与质量测试报告

- **测试时间**: 2026-05-30 18:13:30
- **测试环境**: darwin25 / Python $(python3 -V 2>&1)

## 📊 测试结论

🟢 **全部检查通过！代码状态健康。**

---

## 🔍 详细检查项目

| 检查项 | 状态 | 说明 |
| :--- | :---: | :--- |
| **pytest 单元测试** | ✅ PASS | ============================= 144 passed in 0.31s ============================== |
| **文件输出路径安全性** | ✅ PASS | 检查是否有 XML 泄露到项目根目录 |
| **Python 代码静态编译** | ✅ PASS | 检查 `aes-feeds` 下所有脚本的语法正确性 |

---

## 📝 单元测试原始输出摘要

```text
$(echo "============================= test session starts ==============================
platform darwin -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- /Users/meiyiwangluokeji/coding/lit_auto_pipeline/venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/meiyiwangluokeji/coding/lit_auto_pipeline
configfile: pyproject.toml
testpaths: tests
plugins: mock-3.15.1
collecting ... collected 144 items

tests/test_cnki_downloader.py::TestCleanTextNoise::test_removes_replacement_char PASSED [  0%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_removes_null_byte PASSED [  1%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_collapses_whitespace PASSED [  2%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_strips_whitespace PASSED [  2%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_removes_multiple_question_marks PASSED [  3%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_empty_string PASSED [  4%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_none_input PASSED [  4%]
tests/test_cnki_downloader.py::TestCleanTextNoise::test_chinese_text_preserved PASSED [  5%]
tests/test_cnki_downloader.py::TestLoadTargets::test_loads_valid_json PASSED [  6%]
tests/test_cnki_downloader.py::TestLoadTargets::test_returns_empty_dict_when_file_missing PASSED [  6%]
tests/test_cnki_downloader.py::TestDedupLog::test_save_and_load_roundtrip PASSED [  7%]
tests/test_cnki_downloader.py::TestDedupLog::test_load_empty_when_file_missing PASSED [  8%]
tests/test_cnki_downloader.py::TestDedupLog::test_save_expires_old_entries PASSED [  9%]
tests/test_cnki_downloader.py::TestDedupLog::test_load_handles_corrupted_json PASSED [  9%]
tests/test_cnki_downloader.py::TestGenerateRssXml::test_creates_file PASSED [ 10%]
tests/test_cnki_downloader.py::TestGenerateRssXml::test_filename_is_lowercase PASSED [ 11%]
tests/test_cnki_downloader.py::TestGenerateRssXml::test_xml_contains_article_title PASSED [ 11%]
tests/test_cnki_downloader.py::TestGenerateRssXml::test_valid_rss_structure PASSED [ 12%]
tests/test_cnki_downloader.py::TestGenerateRssXml::test_multiple_articles PASSED [ 13%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_same_links_produce_same_fingerprint PASSED [ 13%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_different_links_produce_different_fingerprint PASSED [ 14%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_order_independent_fingerprint PASSED [ 15%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_empty_links_fingerprint_stable PASSED [ 15%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_read_fingerprint_from_xml PASSED [ 16%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_read_fingerprint_returns_empty_when_no_comment PASSED [ 17%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_read_fingerprint_returns_empty_when_file_missing PASSED [ 18%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_fingerprint_is_32_chars_hex PASSED [ 18%]
tests/test_cnki_downloader.py::TestCmaFingerprint::test_fingerprint_embedded_in_xml_comment PASSED [ 19%]
tests/test_cnki_downloader.py::TestDedupLogic::test_fingerprint_is_consistent PASSED [ 20%]
tests/test_cnki_downloader.py::TestDedupLogic::test_different_articles_have_different_fingerprints PASSED [ 20%]
tests/test_cnki_downloader.py::TestParseCnkiPubdate::test_parse_valid_datetime PASSED [ 21%]
tests/test_cnki_downloader.py::TestParseCnkiPubdate::test_parse_valid_date_only PASSED [ 22%]
tests/test_cnki_downloader.py::TestParseCnkiPubdate::test_parse_page_range_returns_none PASSED [ 22%]
tests/test_cnki_downloader.py::TestParseCnkiPubdate::test_parse_invalid_date_returns_none PASSED [ 23%]
tests/test_cnki_downloader.py::TestParseCnkiPubdate::test_parse_empty_or_none_returns_none PASSED [ 24%]
tests/test_cnki_downloader.py::TestGenerateRssXmlRolling::test_merges_existing_and_new_items PASSED [ 25%]
tests/test_cnki_downloader.py::TestGenerateRssXmlRolling::test_limits_items_to_30 PASSED [ 25%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_removes_replacement_char PASSED [ 26%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_removes_null_byte PASSED [ 27%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_collapses_multiple_spaces PASSED [ 27%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_strips_leading_trailing_whitespace PASSED [ 28%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_removes_repeated_question_marks PASSED [ 29%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_single_question_mark_preserved PASSED [ 29%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_empty_string_returns_empty PASSED [ 30%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_none_returns_empty PASSED [ 31%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_normal_text_unchanged PASSED [ 31%]
tests/test_ktn_downloader.py::TestCleanTextNoise::test_mixed_noise PASSED [ 32%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_spaces_become_underscores PASSED [ 33%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_lowercased PASSED [ 34%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_double_quotes_removed PASSED [ 34%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_single_quotes_removed PASSED [ 35%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_curly_quotes_removed PASSED [ 36%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_empty_returns_unknown PASSED [ 36%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_none_returns_unknown PASSED [ 37%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_no_leading_trailing_underscores PASSED [ 38%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_chinese_keywords_preserved PASSED [ 38%]
tests/test_ktn_downloader.py::TestSanitizeFilename::test_special_chars_replaced PASSED [ 39%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_standard_english_format PASSED [ 40%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_no_quotes_format PASSED [ 40%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_curly_quotes_format PASSED [ 41%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_multi_word_keyword PASSED [ 42%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_case_insensitive_suffix PASSED [ 43%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_unrelated_title_returns_none PASSED [ 43%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_none_title_returns_none PASSED [ 44%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_empty_title_returns_none PASSED [ 45%]
tests/test_ktn_downloader.py::TestKeywordFromEntryTitle::test_strips_extra_quotes_from_result PASSED [ 45%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_valid_scholar_url_link PASSED [ 46%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_valid_scholar_search_link PASSED [ 47%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_hk_scholar_url PASSED [ 47%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_regular_google_link_rejected PASSED [ 48%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_non_google_link_rejected PASSED [ 49%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_empty_href_rejected PASSED [ 50%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_none_href_rejected PASSED [ 50%]
tests/test_ktn_downloader.py::TestIsScholarArticleLink::test_scholar_without_query_rejected PASSED [ 51%]
tests/test_ktn_downloader.py::TestExtractScholarKeyword::test_english_pattern PASSED [ 52%]
tests/test_ktn_downloader.py::TestExtractScholarKeyword::test_chinese_pattern PASSED [ 52%]
tests/test_ktn_downloader.py::TestExtractScholarKeyword::test_no_pattern_returns_none PASSED [ 53%]
tests/test_ktn_downloader.py::TestExtractScholarKeyword::test_english_multi_word PASSED [ 54%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_extracts_keyword PASSED [ 54%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_extracts_source_type PASSED [ 55%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_extracts_articles PASSED [ 56%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_falls_back_to_entry_title PASSED [ 56%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_unknown_source_when_no_keyword PASSED [ 57%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_keyword_has_no_double_quotes PASSED [ 58%]
tests/test_ktn_downloader.py::TestParseSingleMail::test_skips_pdf_links PASSED [ 59%]
tests/test_ktn_downloader.py::TestWriteChannelXml::test_creates_xml_file PASSED [ 59%]
tests/test_ktn_downloader.py::TestWriteChannelXml::test_xml_contains_title PASSED [ 60%]
tests/test_ktn_downloader.py::TestWriteChannelXml::test_empty_articles_returns_none PASSED [ 61%]
tests/test_ktn_downloader.py::TestWriteChannelXml::test_display_title_format PASSED [ 61%]
tests/test_ktn_downloader.py::TestWriteChannelXml::test_valid_rss_structure PASSED [ 62%]
tests/test_ktn_downloader.py::TestCollectExistingChannelMeta::test_collects_ktn_xml_files PASSED [ 63%]
tests/test_ktn_downloader.py::TestCollectExistingChannelMeta::test_ignores_non_ktn_files PASSED [ 63%]
tests/test_ktn_downloader.py::TestCollectExistingChannelMeta::test_empty_dir_returns_empty PASSED [ 64%]
tests/test_lww_downloader.py::TestConfiguration::test_version_defined PASSED [ 65%]
tests/test_lww_downloader.py::TestConfiguration::test_base_dir_is_absolute PASSED [ 65%]
tests/test_lww_downloader.py::TestConfiguration::test_proxy_server_format PASSED [ 66%]
tests/test_lww_downloader.py::TestConfiguration::test_targets_list_not_empty PASSED [ 67%]
tests/test_lww_downloader.py::TestConfiguration::test_base_dir_points_to_aes_feeds PASSED [ 68%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_rss_regex_extracts_content PASSED [ 68%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_item_regex_finds_all_items PASSED [ 69%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_prism_volume_extraction PASSED [ 70%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_prism_number_extraction PASSED [ 70%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_pub_date_extraction PASSED [ 71%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_issue_info_vol_and_num PASSED [ 72%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_issue_info_ahead_of_print PASSED [ 72%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_cdata_stripping PASSED [ 73%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_empty_cdata_replaced PASSED [ 74%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_xmlns_prism_fix PASSED [ 75%]
tests/test_lww_downloader.py::TestXmlExtractionLogic::test_unicode_line_separator_replacement PASSED [ 75%]
tests/test_lww_downloader.py::TestPushToGithub::test_push_calls_git_add PASSED [ 76%]
tests/test_lww_downloader.py::TestPushToGithub::test_push_calls_git_commit PASSED [ 77%]
tests/test_lww_downloader.py::TestPushToGithub::test_push_calls_git_push PASSED [ 77%]
tests/test_lww_downloader.py::TestPushToGithub::test_push_handles_exception_gracefully PASSED [ 78%]
tests/test_lww_downloader.py::TestPushToGithub::test_proxy_env_vars_set_in_push PASSED [ 79%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_ascii_chars_width_1 PASSED [ 79%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_chinese_chars_width_2 PASSED [ 80%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_mixed_chars PASSED [ 81%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_empty_string_width_0 PASSED [ 81%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_space_width_1 PASSED [ 82%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_digits_width_1 PASSED [ 83%]
tests/test_summary_reporter.py::TestGetVisualWidth::test_japanese_chars_width_2 PASSED [ 84%]
tests/test_summary_reporter.py::TestVisualLjust::test_pads_ascii_string PASSED [ 84%]
tests/test_summary_reporter.py::TestVisualLjust::test_pads_chinese_string PASSED [ 85%]
tests/test_summary_reporter.py::TestVisualLjust::test_no_pad_when_already_wide PASSED [ 86%]
tests/test_summary_reporter.py::TestVisualLjust::test_exact_width_no_padding PASSED [ 86%]
tests/test_summary_reporter.py::TestVisualLjust::test_custom_fill_char PASSED [ 87%]
tests/test_summary_reporter.py::TestVisualRjust::test_pads_ascii_string_on_left PASSED [ 88%]
tests/test_summary_reporter.py::TestVisualRjust::test_pads_chinese_string_on_left PASSED [ 88%]
tests/test_summary_reporter.py::TestVisualRjust::test_no_pad_when_already_wide PASSED [ 89%]
tests/test_summary_reporter.py::TestVisualRjust::test_exact_width_no_padding PASSED [ 90%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_parses_single_report PASSED [ 90%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_parses_multiple_reports PASSED [ 91%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_only_returns_latest_run PASSED [ 92%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_returns_empty_when_no_start_marker PASSED [ 93%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_returns_empty_for_missing_file PASSED [ 93%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_count_parsed_as_int PASSED [ 94%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_fail_status_parsed PASSED [ 95%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_handles_item_with_spaces_in_name PASSED [ 95%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_mixed_success_and_fail PASSED [ 96%]
tests/test_summary_reporter.py::TestParseLatestRunReports::test_zero_count_in_success PASSED [ 97%]
tests/test_summary_reporter.py::TestPrintSummaryTable::test_does_not_raise_on_empty PASSED [ 97%]
tests/test_summary_reporter.py::TestPrintSummaryTable::test_does_not_raise_on_success_reports PASSED [ 98%]
tests/test_summary_reporter.py::TestPrintSummaryTable::test_does_not_raise_on_fail_reports PASSED [ 99%]
tests/test_summary_reporter.py::TestPrintSummaryTable::test_total_count_in_output PASSED [100%]

============================= 144 passed in 0.31s ==============================" | tail -n 20)
```
