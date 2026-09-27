"""Comprehensive offline unit tests validating Phase 4 AI Research Synthesizer & Provenance Verifier.

All test inputs are strictly TEST_FIXTURE_ONLY.
Tests do NOT make live network calls.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import (
    ProvenanceCitation,
    ContradictoryEvidence,
    FindingResult,
    SynthesisReport,
)
from src.synthesis.synthesizer import ResearchSynthesizer
from src.synthesis.provenance_checker import ProvenanceChecker
from src.synthesis.pipeline import SynthesisPipeline
from src.storage.database import DatabaseManager


# ==============================================================================
# TEST FIXTURES (TEST_FIXTURE_ONLY)
# ==============================================================================


@pytest.fixture
def sample_evidence_fixtures() -> list[NormalizedEvidenceRecord]:
    """Diverse cohort of normalized evidence records (TEST_FIXTURE_ONLY)."""
    return [
        NormalizedEvidenceRecord(
            id="TEST_EV_01",
            source="Reddit",
            source_url="https://reddit.com/r/googlephotos/test_fixture_only_01",
            author="UserAlpha",
            published_at="2024-02-01T10:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Looking for the screenshot of my payment receipt from last month. Search 'payment' or 'receipt' shows zero results.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for financial payment screenshot",
            retrieval_object="SCREENSHOT",
            memory_cues=["OBJECT_OR_ITEM", "TEMPORAL_APPROXIMATE", "VISIBLE_TEXT"],
            missing_information=["EXACT_DATE", "EXACT_FILENAME"],
            search_behavior=["KEYWORD_SEARCH"],
            search_formulation_original="payment receipt",
            failure_stage=["RETRIEVAL_RELEVANCE", "QUERY_FORMULATION"],
            workaround=["ENDLESS_MANUAL_SCROLL"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.92,
        ),
        NormalizedEvidenceRecord(
            id="TEST_EV_02",
            source="Google Play",
            source_url="https://play.google.com/store/apps/details?id=test_fixture_only_02",
            author="UserBeta",
            published_at="2024-02-15T11:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Search cannot find my prescription receipt. I have to scroll through 10,000 photos.",
            rating=1.0,
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for medical prescription document",
            retrieval_object="HEALTH_OR_MEDICAL",
            memory_cues=["OBJECT_OR_ITEM", "VISIBLE_TEXT"],
            missing_information=["EXACT_DATE"],
            search_behavior=["KEYWORD_SEARCH", "MANUAL_TIMELINE_SCROLL"],
            search_formulation_original="prescription",
            failure_stage=["RETRIEVAL_RELEVANCE", "RESULT_EVALUATION"],
            workaround=["ENDLESS_MANUAL_SCROLL"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.90,
        ),
        NormalizedEvidenceRecord(
            id="TEST_EV_03",
            source="Reddit",
            source_url="https://reddit.com/r/googlephotos/test_fixture_only_03",
            author="UserGamma",
            published_at="2024-03-01T15:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Trying to find that cafe we went to during Goa vacation. Remember it had a red sign and wooden tables, but forgot which year.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Locating vacation cafe photo with visual appearance cues",
            retrieval_object="EVENT_OR_TRIP",
            memory_cues=["SPATIAL_OR_LOCATION", "VISUAL_APPEARANCE", "OBJECT_OR_LANDMARK"],
            missing_information=["EXACT_DATE", "EXACT_NAME"],
            search_behavior=["KEYWORD_SEARCH", "LOCATION_FILTER"],
            search_formulation_original="Goa cafe red sign",
            failure_stage=["MEMORY_RECALL", "RETRIEVAL_RELEVANCE", "SEARCH_REFINEMENT"],
            workaround=["EXTERNAL_APP_SEARCH"],
            outcome="ABANDONED",
            confidence=0.94,
        ),
        NormalizedEvidenceRecord(
            id="TEST_EV_04",
            source="App Store",
            source_url="https://apps.apple.com/app/test_fixture_only_04",
            author="UserDelta",
            published_at="2024-03-10T09:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Impossible to find birthday party pictures when you don't know the exact year. Search brings up thousands of random pictures.",
            rating=2.0,
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for birthday event photo with approximate memory",
            retrieval_object="EVENT_OR_TRIP",
            memory_cues=["ACTIVITY_OR_OCCASION", "TEMPORAL_APPROXIMATE"],
            missing_information=["EXACT_DATE"],
            search_behavior=["KEYWORD_SEARCH"],
            search_formulation_original="birthday party",
            failure_stage=["RESULT_EVALUATION", "SEARCH_REFINEMENT"],
            workaround=["PEOPLE_COLLABORATION"],
            outcome="ABANDONED",
            confidence=0.88,
        ),
    ]


@pytest.fixture
def sample_clusters_fixtures() -> list[ProblemCluster]:
    """Sample problem clusters for synthesis (TEST_FIXTURE_ONLY)."""
    return [
        ProblemCluster(
            cluster_id="CLUST-01",
            name="OCR & Text Mismatch in Utility Documents",
            description="Friction locating transaction and receipt documents",
            evidence_count=2,
            evidence_ids=["TEST_EV_01", "TEST_EV_02"],
            source_diversity=2,
            source_distribution={"Reddit": 1, "Google Play": 1},
            confidence=0.91,
        ),
        ProblemCluster(
            cluster_id="CLUST-02",
            name="Vague Temporal Anchor Friction for Travel Moments",
            description="Breakdown searching for vacation photos with approximate dates",
            evidence_count=2,
            evidence_ids=["TEST_EV_03", "TEST_EV_04"],
            source_diversity=2,
            source_distribution={"Reddit": 1, "App Store": 1},
            confidence=0.91,
        ),
    ]


@pytest.fixture
def sample_opportunities_fixtures() -> list[OpportunityArea]:
    """Sample opportunity areas for synthesis (TEST_FIXTURE_ONLY)."""
    return [
        OpportunityArea(
            opportunity_id="OPP-01",
            cluster_id="CLUST-01",
            cluster_name="OCR & Text Mismatch in Utility Documents",
            evidence_volume=2,
            source_diversity_count=2,
            source_diversity_ratio=0.4,
            recurrence_rate=1.0,
            severity_assessment="HIGH",
            severity_rationale="High utility loss: Involves critical transaction documents.",
            retrieval_impact_rate=1.0,
            workaround_inefficiency="HIGH",
            evidence_confidence=0.91,
        ),
        OpportunityArea(
            opportunity_id="OPP-02",
            cluster_id="CLUST-02",
            cluster_name="Vague Temporal Anchor Friction for Travel Moments",
            evidence_volume=2,
            source_diversity_count=2,
            source_diversity_ratio=0.4,
            recurrence_rate=1.0,
            severity_assessment="MODERATE",
            severity_rationale="Moderate emotional friction: Discretionary personal memories.",
            retrieval_impact_rate=1.0,
            workaround_inefficiency="HIGH",
            evidence_confidence=0.91,
        ),
    ]


# ==============================================================================
# TESTS
# ==============================================================================


def test_synthesis_model_validation():
    """Verify synthesis Pydantic schemas validate correctly (TEST_FIXTURE_ONLY)."""
    citation = ProvenanceCitation(
        evidence_id="TEST_EV_01",
        source="Reddit",
        source_url="https://reddit.com/test",
        quote_snippet="Looking for the screenshot",
        claim_supported="Utility document search failure",
    )
    assert citation.evidence_id == "TEST_EV_01"

    contra = ContradictoryEvidence(
        topic="Search Effectiveness",
        perspective_a="Works for landmarks",
        evidence_ids_a=["TEST_EV_03"],
        perspective_b="Fails for receipts",
        evidence_ids_b=["TEST_EV_01"],
        synthesis_rationale="Media origin and EXIF differences",
    )
    assert len(contra.evidence_ids_a) == 1
    assert len(contra.evidence_ids_b) == 1

    finding = FindingResult(
        finding_id="FINDING-01",
        title="Target Objects",
        research_question="What memories are hardest to find?",
        summary="Utility documents suffer highest friction",
        detailed_analysis="Detailed analysis text",
        citations=[citation],
        contradictory_evidence=contra,
        implications_for_part2="Examine document surface",
        confidence_score=0.92,
    )
    assert finding.finding_id == "FINDING-01"
    assert len(finding.citations) == 1


def test_all_8_findings_generated(
    sample_evidence_fixtures, sample_clusters_fixtures, sample_opportunities_fixtures
):
    """Verify that exactly 8 core research findings are generated (TEST_FIXTURE_ONLY)."""
    synthesizer = ResearchSynthesizer()
    findings = synthesizer.synthesize_all(
        evidence=sample_evidence_fixtures,
        clusters=sample_clusters_fixtures,
        opportunities=sample_opportunities_fixtures,
    )

    assert len(findings) == 8
    expected_ids = [f"FINDING-{i:02d}" for i in range(1, 9)]
    actual_ids = [f.finding_id for f in findings]
    assert actual_ids == expected_ids

    for f in findings:
        assert len(f.title) > 5
        assert len(f.research_question) > 10
        assert len(f.summary) > 20
        assert len(f.detailed_analysis) > 30
        assert len(f.implications_for_part2) > 15
        assert len(f.citations) >= 1  # Zero-uncited claims rule
        assert 0.0 <= f.confidence_score <= 1.0


def test_provenance_verification_chain(
    sample_evidence_fixtures, sample_clusters_fixtures, sample_opportunities_fixtures
):
    """Verify unbroken provenance audit: all citations match canonical records (TEST_FIXTURE_ONLY)."""
    synthesizer = ResearchSynthesizer()
    findings = synthesizer.synthesize_all(
        evidence=sample_evidence_fixtures,
        clusters=sample_clusters_fixtures,
        opportunities=sample_opportunities_fixtures,
    )

    checker = ProvenanceChecker(evidence_records=sample_evidence_fixtures)
    audit = checker.audit_all(findings)

    assert audit.is_valid is True
    assert audit.total_findings_audited == 8
    assert audit.verified_citations == audit.total_citations_audited
    assert len(audit.errors) == 0


def test_provenance_checker_catches_invalid_citation(sample_evidence_fixtures):
    """Verify ProvenanceChecker flags fabricated or non-existent evidence IDs (TEST_FIXTURE_ONLY)."""
    checker = ProvenanceChecker(evidence_records=sample_evidence_fixtures)

    # 1. Non-existent evidence ID
    bad_finding = FindingResult(
        finding_id="FINDING-01",
        title="Invalid Finding",
        research_question="Test Question",
        summary="Test summary",
        detailed_analysis="Test detailed",
        citations=[
            ProvenanceCitation(
                evidence_id="FAKE_EV_999",
                source="Reddit",
                source_url="https://reddit.com/fake",
                quote_snippet="Fabricated text",
                claim_supported="Unsupported claim",
            )
        ],
        implications_for_part2="None",
    )
    is_valid, errors = checker.verify_finding(bad_finding)
    assert is_valid is False
    assert any("does not exist" in err for err in errors)

    # 2. URL mismatch
    bad_url_finding = FindingResult(
        finding_id="FINDING-02",
        title="Mismatched URL Finding",
        research_question="Test Question",
        summary="Test summary",
        detailed_analysis="Test detailed",
        citations=[
            ProvenanceCitation(
                evidence_id="TEST_EV_01",
                source="Reddit",
                source_url="https://altered-url.com/wrong",
                quote_snippet="TEST_FIXTURE_ONLY: Looking for the screenshot",
                claim_supported="Claim",
            )
        ],
        implications_for_part2="None",
    )
    is_valid_url, errors_url = checker.verify_finding(bad_url_finding)
    assert is_valid_url is False
    assert any("URL mismatch" in err for err in errors_url)


def test_contradictory_evidence_detection(
    sample_evidence_fixtures, sample_clusters_fixtures, sample_opportunities_fixtures
):
    """Verify Finding 8 identifies and documents contradictory user perspectives (TEST_FIXTURE_ONLY)."""
    synthesizer = ResearchSynthesizer()
    findings = synthesizer.synthesize_all(
        evidence=sample_evidence_fixtures,
        clusters=sample_clusters_fixtures,
        opportunities=sample_opportunities_fixtures,
    )

    finding_8 = next(f for f in findings if f.finding_id == "FINDING-08")
    assert finding_8.contradictory_evidence is not None
    contra = finding_8.contradictory_evidence

    assert len(contra.topic) > 5
    assert len(contra.perspective_a) > 10
    assert len(contra.perspective_b) > 10
    assert len(contra.evidence_ids_a) >= 1
    assert len(contra.evidence_ids_b) >= 1

    # Perspectives must not overlap
    assert set(contra.evidence_ids_a).isdisjoint(set(contra.evidence_ids_b))


def test_sqlite_findings_persistence(
    tmp_path, sample_evidence_fixtures, sample_clusters_fixtures, sample_opportunities_fixtures
):
    """Verify SQLite database persists and queries research findings (TEST_FIXTURE_ONLY)."""
    db_file = tmp_path / "test_synthesis.db"
    db = DatabaseManager(db_path=db_file)

    synthesizer = ResearchSynthesizer()
    findings = synthesizer.synthesize_all(
        evidence=sample_evidence_fixtures,
        clusters=sample_clusters_fixtures,
        opportunities=sample_opportunities_fixtures,
    )

    # 1. Save
    db.save_findings(findings)

    # 2. Query all
    loaded_findings = db.get_all_findings()
    assert len(loaded_findings) == 8

    # 3. Query specific
    f1 = db.get_finding("FINDING-01")
    assert f1 is not None
    assert f1.finding_id == "FINDING-01"
    assert len(f1.citations) >= 1

    f8 = db.get_finding("FINDING-08")
    assert f8 is not None
    assert f8.contradictory_evidence is not None


def test_synthesis_pipeline_end_to_end(
    tmp_path, sample_evidence_fixtures, sample_clusters_fixtures, sample_opportunities_fixtures
):
    """Verify SynthesisPipeline end-to-end execution and snapshot exports (TEST_FIXTURE_ONLY)."""
    db_file = tmp_path / "test_pipe.db"
    db = DatabaseManager(db_path=db_file)

    pipeline = SynthesisPipeline(db_manager=db)
    pipeline.analysis_dir = tmp_path
    pipeline.findings_file = tmp_path / "synthesis_findings.json"

    summary = pipeline.run(
        custom_evidence=sample_evidence_fixtures,
        custom_clusters=sample_clusters_fixtures,
        custom_opportunities=sample_opportunities_fixtures,
    )

    assert summary["status"] == "SUCCESS"
    assert summary["findings_count"] == 8
    assert summary["provenance_audit_passed"] is True
    assert summary["citations_count"] >= 8

    # Check JSON snapshot
    assert pipeline.findings_file.exists()
    with open(pipeline.findings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 8
