"""Tests for blind PDF ingest and CrossRef parsing."""

from unittest.mock import patch

from aes_workflow.blind_pdf_ingest import build_blind_pdf_row, try_ingest_blind_pdf
from aes_workflow.db import db_session, get_entry, init_db
from aes_workflow.meta_enrich import parse_crossref_message
from aes_workflow.pdf_watcher import process_inbox_once
from aes_workflow.pdf_store import LocalPdfStore


def test_parse_crossref_message():
    data = parse_crossref_message(
        {
            "title": ["Sample Paper"],
            "container-title": ["Plast Reconstr Surg"],
            "author": [{"given": "A", "family": "Author"}],
            "DOI": "10.1097/prs.0000000000012345",
            "URL": "https://doi.org/10.1097/prs.0000000000012345",
            "published-print": {"date-parts": [[2026, 6, 1]]},
        }
    )
    assert data["title"] == "Sample Paper"
    assert data["journal"] == "Plast Reconstr Surg"
    assert data["doi"] == "10.1097/prs.0000000000012345"


@patch("aes_workflow.blind_pdf_ingest.enrich_identifiers")
@patch("aes_workflow.blind_pdf_ingest.extract_ids_from_pdf")
def test_try_ingest_blind_pdf_creates_entry(mock_ids, mock_enrich, tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    pdf = tmp_path / "inbox" / "paper.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-1.4")

    mock_ids.return_value = {"doi": "10.1097/prs.0000000000012999"}
    mock_enrich.return_value = (
        {
            "title": "Blind Download Paper",
            "journal": "PRS",
            "authors": "One Author",
            "abstract": "Test abstract.",
            "doi": "10.1097/prs.0000000000012999",
            "publisher_url": "https://doi.org/10.1097/prs.0000000000012999",
            "source_url": "https://doi.org/10.1097/prs.0000000000012999",
        },
        "crossref",
    )

    with db_session(db) as conn:
        key, ids, reason = try_ingest_blind_pdf(conn, pdf)
    assert reason == "ingested"
    assert key
    assert ids["doi"] == "10.1097/prs.0000000000012999"

    with db_session(db) as conn:
        row = get_entry(conn, key)
    assert row["ingest_source"] == "blind_pdf"
    assert row["screening_status"] == "screening_pending"
    assert row["title"] == "Blind Download Paper"


@patch("aes_workflow.pdf_watcher.try_ingest_blind_pdf")
@patch("aes_workflow.pdf_watcher.extract_ids_from_pdf")
@patch("aes_workflow.pdf_watcher.lookup_article_key")
def test_watcher_blind_ingest_branch(mock_lookup, mock_extract, mock_blind, tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    inbox = tmp_path / "inbox"
    store_dir = tmp_path / "pdf"
    inbox.mkdir()
    store_dir.mkdir()
    pdf = inbox / "new.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    mock_lookup.return_value = None
    mock_extract.return_value = {"doi": "10.1007/s00266-026-09999-9"}
    mock_blind.return_value = ("a" * 64, {"doi": "10.1007/s00266-026-09999-9"}, "ingested")

    store = LocalPdfStore(inbox=inbox, store_dir=store_dir)
    stats = process_inbox_once(store=store, db_path=db, quarantine=False, blind_ingest=True)
    assert stats["ingested"] == 1
    assert not pdf.exists()
    assert (store_dir / f"{'a' * 64}.pdf").is_file()
