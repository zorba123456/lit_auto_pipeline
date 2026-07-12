"""Tests for PDF inbox filename matching."""

from aes_workflow.pdf_extract import article_key_from_filename, is_incomplete_download


def test_article_key_filename():
    key = "a" * 64
    assert article_key_from_filename(__import__("pathlib").Path(f"{key}.pdf")) == key


def test_reject_short_stem():
    assert article_key_from_filename(__import__("pathlib").Path("not-a-key.pdf")) is None


def test_incomplete_download():
    from pathlib import Path

    assert is_incomplete_download(Path("paper.pdf.crdownload"))
    assert not is_incomplete_download(Path("paper.pdf"))
