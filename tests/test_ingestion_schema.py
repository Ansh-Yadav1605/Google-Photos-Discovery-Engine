"""Unit tests for schemas and query library."""

import pytest
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.ingestion.query_library import QueryLibrary


def test_query_library_initialization():
    ql = QueryLibrary()
    queries = ql.get_all_queries()
    assert len(queries) > 10
    assert any("can't find" in q for q in queries)
    assert any("search people" in q for q in queries)


def test_raw_evidence_record_validation():
    rec = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test",
        title="Can't find old photo",
        raw_text="I remember taking a picture of my dog at Goa beach in 2023 but search won't show it.",
    )
    assert rec.source == "Reddit"
    assert rec.raw_text is not None
    assert rec.id is not None
    assert rec.retrieved_at is not None


def test_normalized_evidence_record_validation():
    rec = NormalizedEvidenceRecord(
        id="test-123",
        source="Google Play",
        source_url="https://play.google.com/store/apps/details?id=com.google.android.apps.photos",
        retrieved_at="2026-09-24T00:00:00Z",
        raw_text="Search is useless. Cannot find my receipts.",
        retrieval_relevance=True,
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_object="UTILITY_DOCUMENT",
        memory_cues=["OBJECT_OR_ITEM"],
        failure_stage=["RETRIEVAL_RELEVANCE"],
        confidence=0.85,
    )
    assert rec.retrieval_relevance is True
    assert "RETRIEVAL_RELEVANCE" in rec.failure_stage
