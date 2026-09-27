"""Comprehensive unit tests validating Phase 0 and Phase 1 components.

All test inputs are strictly TEST_FIXTURE_ONLY.
Tests use mocks and do NOT make live network calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.ingestion.query_library import QueryLibrary
from src.ingestion.adapters.reddit_adapter import RedditAdapter
from src.ingestion.adapters.app_store_adapter import AppStoreAdapter
from src.ingestion.adapters.community_adapter import CommunityAdapter
from src.ingestion.adapters.manual_import_adapter import ManualImportAdapter
from src.ingestion.pipeline import IngestionPipeline


# ==============================================================================
# 1. SCHEMA & MISSING FIELD VALIDATION (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_schema_allows_missing_optional_fields():
    """Verify that absent metadata remains null/empty without being fabricated (TEST_FIXTURE_ONLY)."""
    raw_data = {
        "source": "Reddit",
        "source_url": "https://www.reddit.com/r/googlephotos/comments/test_fixture_only_1",
        "raw_text": "TEST_FIXTURE_ONLY: Looking for that photo from my friend's birthday where everyone wore black.",
    }
    record = RawEvidenceRecord(**raw_data)
    assert record.title is None
    assert record.author is None
    assert record.published_at is None
    assert record.rating is None
    assert record.country_or_region is None
    assert record.raw_text.startswith("TEST_FIXTURE_ONLY")


def test_provenance_chain_preservation():
    """Verify that evidence records preserve full provenance (TEST_FIXTURE_ONLY)."""
    record = RawEvidenceRecord(
        source="Google Play",
        source_url="https://play.google.com/store/apps/details?id=com.google.android.apps.photos&reviewId=TEST_FIXTURE_ONLY_99",
        author="VerifiedReviewer",
        published_at="2024-03-15T10:00:00Z",
        raw_text="TEST_FIXTURE_ONLY: Search stopped finding my old travel photos by place name.",
    )
    assert record.id is not None
    assert record.source == "Google Play"
    assert "reviewId=TEST_FIXTURE_ONLY_99" in record.source_url
    assert record.published_at == "2024-03-15T10:00:00Z"
    assert "TEST_FIXTURE_ONLY" in record.raw_text


def test_normalized_schema_preserves_taxonomy_and_nulls():
    """Verify normalized evidence schema accepts behavioral fields and preserves empty values (TEST_FIXTURE_ONLY)."""
    norm = NormalizedEvidenceRecord(
        id="test-uuid-001",
        source="Reddit",
        source_url="https://www.reddit.com/r/googlephotos/comments/test_fixture_only_2",
        retrieved_at="2026-09-24T12:00:00Z",
        raw_text="TEST_FIXTURE_ONLY: Can't find the photo of my medicine packaging from last year.",
        retrieval_relevance=True,
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_scenario="Finding physical medicine packaging",
        retrieval_object="HEALTH_OR_MEDICAL",
        memory_cues=["OBJECT_OR_ITEM", "TEMPORAL_APPROXIMATE"],
        missing_information=["EXACT_DATE", "EXACT_NAME"],
        search_behavior=["KEYWORD_SEARCH"],
        failure_stage=["RETRIEVAL_RELEVANCE", "QUERY_FORMULATION"],
        workaround=["ENDLESS_MANUAL_SCROLL"],
        confidence=0.9,
    )
    assert norm.retrieval_relevance is True
    assert norm.retrieval_object == "HEALTH_OR_MEDICAL"
    assert len(norm.memory_cues) == 2
    assert norm.cluster_id is None


# ==============================================================================
# 2. ADAPTER FAILURE & ERROR RESILIENCE (TEST_FIXTURE_ONLY)
# ==============================================================================


@patch("requests.get")
def test_reddit_adapter_handles_rate_limit_and_server_error(mock_get):
    """Verify RedditAdapter backs off on HTTP 429 and handles 500 cleanly (TEST_FIXTURE_ONLY)."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_500 = MagicMock()
    mock_resp_500.status_code = 500

    mock_get.side_effect = [mock_resp_429, mock_resp_500]

    adapter = RedditAdapter(delay_seconds=0.0)
    # Provide one subreddit to keep test fast
    adapter.SUBREDDITS = ["googlephotos"]
    records = adapter.fetch(queries=["TEST_FIXTURE_ONLY query"], limit_per_query=5)

    assert isinstance(records, list)
    assert len(records) == 0


@patch("requests.get")
def test_reddit_adapter_filters_deleted_and_empty_posts(mock_get):
    """Verify deleted and malformed Reddit posts are excluded (TEST_FIXTURE_ONLY)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "permalink": "/r/googlephotos/comments/del1",
                        "title": "deleted post",
                        "selftext": "[deleted]",
                    }
                },
                {
                    "data": {
                        "permalink": "/r/googlephotos/comments/short1",
                        "title": "hi",
                        "selftext": "",
                    }
                },
                {
                    "data": {
                        "permalink": "/r/googlephotos/comments/valid1",
                        "title": "TEST_FIXTURE_ONLY: Search fails when searching for white dog at beach",
                        "selftext": "I distinctly remember taking it around June 2023.",
                        "created_utc": 1687000000,
                        "author": "TestUser",
                    }
                },
            ]
        }
    }
    mock_get.return_value = mock_resp

    adapter = RedditAdapter(delay_seconds=0.0)
    adapter.SUBREDDITS = ["googlephotos"]
    records = adapter.fetch(queries=["dog beach"], limit_per_query=5)

    assert len(records) == 1
    assert "white dog at beach" in records[0].raw_text
    assert records[0].author == "TestUser"


@patch("requests.get")
def test_app_store_adapter_deduplicates_and_filters_unrelated(mock_get):
    """Verify AppStoreAdapter filters irrelevant reviews and deduplicates (TEST_FIXTURE_ONLY)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "feed": {
            "entry": [
                {},  # App metadata header entry
                {
                    "id": {"label": "REV_001"},
                    "title": {"label": "App crashes"},
                    "content": {"label": "The app crashes when I try to edit lighting."},
                    "im:rating": {"label": "1"},
                },
                {
                    "id": {"label": "REV_002"},
                    "title": {"label": "TEST_FIXTURE_ONLY: Search can't find old receipts"},
                    "content": {"label": "I tried to find a screenshot of a receipt from last month and search showed zero results."},
                    "im:rating": {"label": "2"},
                    "updated": {"label": "2024-02-10T15:00:00Z"},
                },
            ]
        }
    }
    mock_get.return_value = mock_resp

    adapter = AppStoreAdapter(delay_seconds=0.0)
    adapter.REGIONS = ["us"]
    records = adapter.fetch(queries=["receipt"], limit_per_query=10)

    # First entry (crashes editing) should be filtered out because no retrieval keywords
    # Second entry should be kept
    assert len(records) == 1
    assert "Search can't find old receipts" in records[0].title


# ==============================================================================
# 3. PIPELINE ISOLATION & ORCHESTRATION (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_pipeline_continues_when_one_adapter_crashes():
    """Verify that a catastrophic exception in one adapter does not crash the entire pipeline (TEST_FIXTURE_ONLY)."""
    pipeline = IngestionPipeline()

    # Mock first adapter to raise unexpected runtime error
    faulty_adapter = MagicMock()
    faulty_adapter.source_name = "FaultyAdapter"
    faulty_adapter.fetch.side_effect = RuntimeError("TEST_FIXTURE_ONLY: Simulated crash")

    # Mock second adapter to succeed
    healthy_adapter = MagicMock()
    healthy_adapter.source_name = "HealthyAdapter"
    test_rec = RawEvidenceRecord(
        source="Forum",
        source_url="https://forum.example.com/test_fixture_only_thread",
        raw_text="TEST_FIXTURE_ONLY: Healthy adapter retrieved this post cleanly.",
    )
    healthy_adapter.fetch.return_value = [test_rec]

    pipeline.adapters = [faulty_adapter, healthy_adapter]

    summary = pipeline.run(query_limit=2)

    assert summary["source_distribution"]["FaultyAdapter"] == 0
    assert summary["source_distribution"]["HealthyAdapter"] == 1
    assert summary["total_records"] == 1
