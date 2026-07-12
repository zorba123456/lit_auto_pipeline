"""Tests for identifier parsing and article_key."""

from aes_workflow.ingest_ids import (
    article_key_from_identifiers,
    extract_doi_from_text,
    extract_pii_from_url,
    pick_canonical_guid,
)


def test_doi_from_url():
    assert extract_doi_from_text("https://link.springer.com/article/10.1007/s00266-026-05951-8") == (
        "10.1007/s00266-026-05951-8"
    )


def test_pii_from_sciencedirect():
    assert (
        extract_pii_from_url("https://www.sciencedirect.com/science/article/pii/S0002939426003107")
        == "S0002939426003107"
    )


def test_article_key_stable():
    ids = {"doi": "10.1097/prs.0000000000012568"}
    k1 = article_key_from_identifiers(ids)
    k2 = article_key_from_identifiers(ids)
    assert k1 == k2
    assert len(k1) == 64


def test_canonical_priority():
    assert pick_canonical_guid({"doi": "10.1/x", "pmid": "123"}) == "doi:10.1/x"
