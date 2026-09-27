"""Comprehensive offline tests validating Phase 2 AI extraction & classification.

All test inputs are strictly TEST_FIXTURE_ONLY.
Tests use mocks and do NOT make live network calls.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.models.extraction import LLMExtractionResult
from src.extraction.llm_adapter import GroqLLMAdapter
from src.extraction.extractor import EvidenceExtractor
from src.extraction.pipeline import ExtractionPipeline


# ==============================================================================
# 1. RELEVANCE CLASSIFICATION TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_directly_relevant_classification():
    """Verify DIRECTLY_RELEVANT user searching for physical medicine (TEST_FIXTURE_ONLY)."""
    raw = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_med",
        raw_text="TEST_FIXTURE_ONLY: Looking for the picture of the medicine I took when sick last year.",
    )

    mock_llm_result = LLMExtractionResult(
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="User attempting to locate a specific photo of medicine packaging",
        retrieval_scenario="Searching for past prescription/medicine photo",
        retrieval_object="HEALTH_OR_MEDICAL",
        memory_cues=["OBJECT_OR_ITEM", "TEMPORAL_APPROXIMATE"],
        missing_information=["EXACT_NAME", "EXACT_DATE"],
        search_behavior=["KEYWORD_SEARCH"],
        failure_stage=["RETRIEVAL_RELEVANCE"],
        outcome="FAILED_RETRIEVAL",
        confidence=0.92,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.return_value = mock_llm_result

    norm = extractor.process_record(raw)
    assert norm.retrieval_relevance is True
    assert norm.retrieval_relevance_class == "DIRECTLY_RELEVANT"
    assert norm.retrieval_object == "HEALTH_OR_MEDICAL"
    assert "OBJECT_OR_ITEM" in norm.memory_cues


def test_indirectly_relevant_classification():
    """Verify INDIRECTLY_RELEVANT classification for broken facial grouping (TEST_FIXTURE_ONLY)."""
    raw = RawEvidenceRecord(
        source="Google Photos Community",
        source_url="https://support.google.com/photos/thread/test_fixture_only_faces",
        raw_text="TEST_FIXTURE_ONLY: Face tagging stopped grouping my daughter's face, so I can't search for her pictures.",
    )

    mock_llm_result = LLMExtractionResult(
        retrieval_relevance_class="INDIRECTLY_RELEVANT",
        retrieval_relevance_reason="Facial recognition indexing bug indirectly degrading people retrieval",
        retrieval_scenario="People search failure due to grouping indexing",
        retrieval_object="PERSONAL_PHOTO",
        memory_cues=["PERSON_OR_FACE"],
        failure_stage=["METADATA_OR_INDEXING"],
        outcome="FAILED_RETRIEVAL",
        confidence=0.88,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.return_value = mock_llm_result

    norm = extractor.process_record(raw)
    assert norm.retrieval_relevance is True
    assert norm.retrieval_relevance_class == "INDIRECTLY_RELEVANT"
    assert "METADATA_OR_INDEXING" in norm.failure_stage


def test_not_relevant_classification():
    """Verify NOT_RELEVANT classification for photo editor crash (TEST_FIXTURE_ONLY)."""
    raw = RawEvidenceRecord(
        source="Google Play",
        source_url="https://play.google.com/store/apps/details?id=com.google.android.apps.photos&reviewId=test_fixture_only_crash",
        raw_text="TEST_FIXTURE_ONLY: Magic Eraser crashes every time I try to save an edited photo. Fix this bug!",
        rating=1.0,
    )

    mock_llm_result = LLMExtractionResult(
        retrieval_relevance_class="NOT_RELEVANT",
        retrieval_relevance_reason="Editing tool crash unrelated to photo retrieval or search",
        confidence=0.99,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.return_value = mock_llm_result

    norm = extractor.process_record(raw)
    assert norm.retrieval_relevance is False
    assert norm.retrieval_relevance_class == "NOT_RELEVANT"
    assert norm.retrieval_object is None
    assert norm.memory_cues == []
    assert norm.failure_stage == []


# ==============================================================================
# 2. BEHAVIORAL EXTRACTION & ANTI-HALLUCINATION TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_missing_optional_fields_no_hallucination():
    """Verify that unmentioned details are NOT assumed to be forgotten (TEST_FIXTURE_ONLY)."""
    raw = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_beach",
        raw_text="TEST_FIXTURE_ONLY: Can't find my beach photo.",
    )

    mock_llm_result = LLMExtractionResult(
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="User searching for beach photo",
        retrieval_scenario="Vague photo search",
        retrieval_object="PERSONAL_PHOTO",
        memory_cues=["SPATIAL_OR_LOCATION"],
        missing_information=[],  # Not mentioned != forgotten!
        search_formulation_original=None,  # No query mentioned
        search_formulation_normalized=None,
        failure_stage=["RETRIEVAL_RELEVANCE"],
        outcome="UNCLEAR",
        confidence=0.75,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.return_value = mock_llm_result

    norm = extractor.process_record(raw)
    assert norm.missing_information == []
    assert norm.search_formulation_original is None
    assert norm.search_formulation["original_query"] is None


def test_problem_a_vs_problem_b_distinction():
    """Verify clear distinction between Problem A (backup loss) and Problem B (search UX) (TEST_FIXTURE_ONLY)."""
    # Problem A: Content actually missing
    raw_a = RawEvidenceRecord(
        source="Google Photos Community",
        source_url="https://support.google.com/photos/thread/test_fixture_only_loss",
        raw_text="TEST_FIXTURE_ONLY: After I cancelled Google One, all photos from 2022 disappeared from cloud.",
    )
    result_a = LLMExtractionResult(
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="Data loss / backup deletion inquiry",
        failure_stage=["CONTENT_NOT_PRESENT_OR_UNAVAILABLE"],
        outcome="FAILED_RETRIEVAL",
        confidence=0.9,
    )

    # Problem B: Photo exists, but search cannot retrieve it
    raw_b = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_ux",
        raw_text="TEST_FIXTURE_ONLY: The photo is right there when I scroll to June 2023, but searching 'dog red ball' returns nothing.",
    )
    result_b = LLMExtractionResult(
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="Photo exists but search relevance fails",
        search_formulation_original="dog red ball",
        search_formulation_normalized="dog red ball",
        failure_stage=["RETRIEVAL_RELEVANCE", "QUERY_FORMULATION"],
        outcome="FAILED_RETRIEVAL",
        confidence=0.95,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.side_effect = [result_a, result_b]

    norm_a = extractor.process_record(raw_a)
    norm_b = extractor.process_record(raw_b)

    assert "CONTENT_NOT_PRESENT_OR_UNAVAILABLE" in norm_a.failure_stage
    assert "RETRIEVAL_RELEVANCE" in norm_b.failure_stage
    assert norm_b.search_formulation_original == "dog red ball"


def test_multiple_failure_stages_and_workarounds():
    """Verify multiple failure stages and compensatory workarounds (TEST_FIXTURE_ONLY)."""
    raw = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_stages",
        raw_text="TEST_FIXTURE_ONLY: I forgot the exact date of my friend's party. I searched 'party black dress' but it gave 500 photos without filter options. I gave up and asked my friend on WhatsApp to send it.",
    )

    mock_llm_result = LLMExtractionResult(
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="Multi-stage retrieval failure with external workaround",
        retrieval_scenario="Finding social event photo with visual clothing cue",
        retrieval_object="GROUP_PHOTO",
        memory_cues=["ACTIVITY_OR_OCCASION", "VISUAL_APPEARANCE"],
        missing_information=["EXACT_DATE"],
        search_behavior=["KEYWORD_SEARCH", "SEARCH_ABANDONMENT"],
        search_formulation_original="party black dress",
        search_formulation_normalized="party black dress",
        failure_stage=[
            "MEMORY_RECALL",
            "RESULT_EVALUATION",
            "SEARCH_REFINEMENT",
        ],
        workaround=["EXTERNAL_APP_SEARCH", "PEOPLE_COLLABORATION"],
        outcome="ABANDONED",
        confidence=0.94,
    )

    extractor = EvidenceExtractor(llm_adapter=MagicMock())
    extractor.llm_adapter.extract.return_value = mock_llm_result

    norm = extractor.process_record(raw)
    assert len(norm.failure_stage) == 3
    assert "MEMORY_RECALL" in norm.failure_stage
    assert "SEARCH_REFINEMENT" in norm.failure_stage
    assert "PEOPLE_COLLABORATION" in norm.workaround
    assert norm.outcome == "ABANDONED"


# ==============================================================================
# 3. SCHEMA VALIDATION & RESILIENCE TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_invalid_enum_sanitization():
    """Verify invalid or hallucinated enum values are safely filtered out (TEST_FIXTURE_ONLY)."""
    raw_json = {
        "retrieval_relevance_class": "DIRECTLY_RELEVANT",
        "retrieval_relevance_reason": "Valid reason",
        "failure_stage": [
            "RETRIEVAL_RELEVANCE",
            "FABRICATED_IMAGINARY_STAGE",
            "OTHER",
        ],
        "outcome": "UNCLEAR",
        "confidence": 1.5,  # Needs clamping to 1.0
    }

    result = LLMExtractionResult(**raw_json)
    assert "RETRIEVAL_RELEVANCE" in result.failure_stage
    assert "OTHER" in result.failure_stage
    assert "FABRICATED_IMAGINARY_STAGE" not in result.failure_stage
    assert result.confidence == 1.0


def test_malformed_json_fallback():
    """Verify that unparseable LLM output returns fallback with provenance intact (TEST_FIXTURE_ONLY)."""
    adapter = GroqLLMAdapter(api_key="TEST_FIXTURE_ONLY_KEY")
    mock_client = MagicMock()
    adapter.client = mock_client

    # Simulate LLM returning invalid JSON string
    mock_choice = MagicMock()
    mock_choice.message.content = "{ 'broken': json without closing brace"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    raw = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_broken",
        raw_text="TEST_FIXTURE_ONLY: Malformed JSON test",
    )

    extractor = EvidenceExtractor(llm_adapter=adapter)
    norm = extractor.process_record(raw)

    # Provenance preserved, error handled gracefully
    assert norm.id == raw.id
    assert norm.source_url == raw.source_url
    assert norm.retrieval_relevance is None
    assert norm.retrieval_relevance_reason == "EXTRACTION_FAILED_OR_UNINITIALIZED"


def test_rate_limit_and_timeout_resilience():
    """Verify Groq adapter handles RateLimitError and Timeout with retry (TEST_FIXTURE_ONLY)."""
    adapter = GroqLLMAdapter(api_key="TEST_FIXTURE_ONLY_KEY", max_retries=2)
    mock_client = MagicMock()
    adapter.client = mock_client

    from groq import RateLimitError

    # First call raises RateLimitError, second succeeds
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "retrieval_relevance_class": "NOT_RELEVANT",
            "retrieval_relevance_reason": "Recovered after rate limit",
            "confidence": 0.9,
        }
    )
    mock_success = MagicMock()
    mock_success.choices = [mock_choice]

    mock_client.chat.completions.create.side_effect = [
        RateLimitError("Rate limit exceeded", response=MagicMock(), body=None),
        mock_success,
    ]

    raw = RawEvidenceRecord(
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/test_fixture_only_retry",
        raw_text="TEST_FIXTURE_ONLY: Testing rate limit retry",
    )

    with patch("time.sleep"):  # Avoid actual test sleep
        result = adapter.extract(raw)

    assert result is not None
    assert result.retrieval_relevance_class == "NOT_RELEVANT"


# ==============================================================================
# 4. PIPELINE IDEMPOTENCY & PROVENANCE TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_pipeline_idempotency(tmp_path):
    """Verify that already processed records are skipped by the pipeline (TEST_FIXTURE_ONLY)."""
    pipeline = ExtractionPipeline(rate_delay=0.0)
    pipeline.processed_dir = tmp_path
    pipeline.enriched_file = tmp_path / "evidence_enriched.jsonl"
    pipeline.rejected_file = tmp_path / "rejected_evidence.jsonl"

    # Write a pre-existing processed record
    existing_rec = {
        "id": "ALREADY_PROCESSED_ID_001",
        "source": "Reddit",
        "source_url": "https://reddit.com/r/googlephotos/processed",
        "retrieved_at": "2026-09-24T12:00:00Z",
        "raw_text": "TEST_FIXTURE_ONLY: Already done",
    }
    with open(pipeline.enriched_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(existing_rec) + "\n")

    processed_ids = pipeline.get_processed_ids()
    assert "ALREADY_PROCESSED_ID_001" in processed_ids

    # Setup 1 existing + 1 new raw record
    raw_old = RawEvidenceRecord(
        id="ALREADY_PROCESSED_ID_001",
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/processed",
        raw_text="TEST_FIXTURE_ONLY: Already done",
    )
    raw_new = RawEvidenceRecord(
        id="NEW_UNPROCESSED_ID_002",
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/new",
        raw_text="TEST_FIXTURE_ONLY: New record to process",
    )

    pipeline.load_raw_records = MagicMock(return_value=[raw_old, raw_new])

    mock_extractor = MagicMock()
    mock_norm = NormalizedEvidenceRecord(
        id="NEW_UNPROCESSED_ID_002",
        source="Reddit",
        source_url="https://reddit.com/r/googlephotos/new",
        retrieved_at="2026-09-24T12:00:00Z",
        raw_text="TEST_FIXTURE_ONLY: New record to process",
        retrieval_relevance=True,
        retrieval_relevance_class="DIRECTLY_RELEVANT",
    )
    mock_extractor.process_record.return_value = mock_norm
    pipeline.extractor = mock_extractor

    stats = pipeline.run()

    # Old record was skipped!
    assert stats["total_queued"] == 1
    assert stats["processed"] == 1
    mock_extractor.process_record.assert_called_once_with(raw_new)
