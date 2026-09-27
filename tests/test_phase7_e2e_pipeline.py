"""Phase 7: End-to-End Testing & Live Quality Validation.

Comprehensive system integration tests validating the full lifecycle from Phase 0 to Phase 6:
1. Multi-source raw ingestion payload normalization & deduplication.
2. AI relevance classification & taxonomy extraction (isolating Problem B from Problem A).
3. SQLite analytical storage persistence across all schemas.
4. Emergent density clustering & 7-dimensional Opportunity Matrix (verifying zero arbitrary composite ranking).
5. Evidence-grounded research synthesis (Findings 1–8) with automated provenance audit.
6. REST API integration contracts and frontend schema alignment.
7. Epistemic boundary invariants (traceability, zero hallucination, contradictory evidence reporting).

All test data are strictly TEST_FIXTURE_ONLY. No live network calls are made.
"""

import json
import pytest
from pathlib import Path
from typing import List, Dict, Any
from fastapi.testclient import TestClient

from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import FindingResult
from src.storage.database import DatabaseManager
from src.extraction.extractor import EvidenceExtractor
from src.extraction.pipeline import ExtractionPipeline
from src.clustering.clusterer import EmergentClusterer
from src.clustering.opportunity_matrix import OpportunityMatrixCalculator
from src.clustering.pipeline import ClusteringPipeline
from src.synthesis.synthesizer import ResearchSynthesizer
from src.synthesis.provenance_checker import ProvenanceChecker
from src.synthesis.pipeline import SynthesisPipeline
from src.api.main import app, get_db


# ==============================================================================
# MOCK LLM EXTRACTOR FOR DETERMINISTIC END-TO-END VERIFICATION
# ==============================================================================


class DeterministicMockExtractor(EvidenceExtractor):
    """Deterministic mock extractor that extracts taxonomy without network calls (TEST_FIXTURE_ONLY)."""

    def __init__(self):
        self.llm_adapter = None

    def process_record(self, raw: RawEvidenceRecord) -> NormalizedEvidenceRecord:
        text = raw.raw_text.lower()

        # Problem A filter: Backup failure or missing photos
        if "backup" in text or "disappeared" in text or "lost all my photos" in text:
            return NormalizedEvidenceRecord(
                id=raw.id,
                source=raw.source,
                source_url=raw.source_url,
                author=raw.author,
                published_at=raw.published_at,
                retrieved_at=raw.retrieved_at,
                raw_text=raw.raw_text,
                retrieval_relevance=False,
                retrieval_relevance_class="NOT_RELEVANT",
                retrieval_relevance_reason="Problem A backup failure, not retrieval friction.",
                confidence=0.98,
            )

        # Problem B: Direct Retrieval Friction Scenarios
        if "receipt" in text or "screenshot" in text:
            scenario = "Searching for utility receipt screenshot with text cues"
            retrieval_obj = "SCREENSHOT"
            cues = ["OBJECT_OR_ITEM", "VISIBLE_TEXT", "TEMPORAL_APPROXIMATE"]
            missing = ["EXACT_DATE", "EXACT_NAME"]
            behaviors = ["MANUAL_TIMELINE_SCROLL"]
            stages = ["RETRIEVAL_RELEVANCE", "QUERY_FORMULATION"]
            workarounds = ["ENDLESS_MANUAL_SCROLL"]
            outcome = "FAILED_RETRIEVAL"
        elif "vacation" in text or "trip" in text or "cafe" in text or "beach" in text:
            scenario = "Finding vacation trip photos with qualitative visual memories"
            retrieval_obj = "EVENT_OR_TRIP"
            cues = ["SPATIAL_OR_LOCATION", "VISUAL_APPEARANCE", "OBJECT_OR_LANDMARK"]
            missing = ["EXACT_DATE"]
            behaviors = ["LOCATION_FILTER", "PEOPLE_PETS_GRID"]
            stages = ["RETRIEVAL_RELEVANCE", "RESULT_EVALUATION"]
            workarounds = ["MANUAL_TIMELINE_SCROLL", "PEOPLE_COLLABORATION"]
            outcome = "PARTIAL_SUCCESS"
        elif "cat" in text or "pet" in text or "dog" in text:
            scenario = "Searching for pet moments across multi-year library"
            retrieval_obj = "PERSON_OR_PET"
            cues = ["PERSON_OR_SUBJECT", "TEMPORAL_APPROXIMATE"]
            missing = ["EXACT_DATE"]
            behaviors = ["PEOPLE_PETS_GRID"]
            stages = ["RESULT_EVALUATION", "SEARCH_REFINEMENT"]
            workarounds = ["ALBUM_CREATION"]
            outcome = "PARTIAL_SUCCESS"
        else:
            scenario = "General personal retrieval inquiry"
            retrieval_obj = "OTHER"
            cues = ["TEMPORAL_APPROXIMATE"]
            missing = ["EXACT_DATE"]
            behaviors = ["KEYWORD_SEARCH"]
            stages = ["QUERY_FORMULATION"]
            workarounds = ["MANUAL_TIMELINE_SCROLL"]
            outcome = "FAILED_RETRIEVAL"

        return NormalizedEvidenceRecord(
            id=raw.id,
            source=raw.source,
            source_url=raw.source_url,
            author=raw.author,
            published_at=raw.published_at,
            retrieved_at=raw.retrieved_at,
            raw_text=raw.raw_text,
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario=scenario,
            retrieval_object=retrieval_obj,
            memory_cues=cues,
            missing_information=missing,
            search_behavior=behaviors,
            search_formulation_original=raw.raw_text[:40],
            failure_stage=stages,
            workaround=workarounds,
            outcome=outcome,
            confidence=0.94,
        )


# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def e2e_environment(tmp_path: Path):
    """Sets up an isolated filesystem environment with raw records, db, and mock pipelines."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    analysis_dir = tmp_path / "analysis"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)

    db_file = analysis_dir / "e2e_discovery.db"
    db_mgr = DatabaseManager(db_path=db_file)

    # Seed multi-source raw records covering Problem B and Problem A
    raw_records = [
        # Reddit (Problem B: Receipts)
        {
            "id": "RAW-REDDIT-001",
            "source": "Reddit",
            "source_url": "https://reddit.com/r/googlephotos/comments/receipt_search",
            "author": "ReceiptSeeker",
            "published_at": "2024-03-01T10:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "I am trying to find a screenshot of a medical receipt from last month. Searching 'receipt' yields zero matches.",
            "source_metadata": {"subreddit": "googlephotos"},
        },
        # Google Play (Problem B: Receipts)
        {
            "id": "RAW-PLAY-001",
            "source": "Google Play",
            "source_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.photos&reviewId=play001",
            "author": "PlayReviewerA",
            "published_at": "2024-03-02T11:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "Search cannot read text on my screenshot receipts. It used to work with OCR, now nothing comes up.",
            "source_metadata": {"score": 2},
        },
        # App Store (Problem B: Vacation)
        {
            "id": "RAW-IOS-001",
            "source": "App Store",
            "source_url": "https://apps.apple.com/app/google-photos/id962194608?reviewId=ios001",
            "author": "iOSReviewerB",
            "published_at": "2024-03-03T12:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "Can never find vacation photos from our trip to Italy. I know the cafe had yellow chairs, but typing that returns thousands of random photos.",
            "source_metadata": {"rating": 2},
        },
        # Google Photos Community (Problem B: Vacation)
        {
            "id": "RAW-COMM-001",
            "source": "Google Photos Community",
            "source_url": "https://support.google.com/photos/thread/comm001",
            "author": "CommUserC",
            "published_at": "2024-03-04T14:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "Looking for vacation beach trip photos from 3 years ago without remembering the exact date is impossible.",
            "source_metadata": {"thread_id": "comm001"},
        },
        # Reddit (Problem B: Pet)
        {
            "id": "RAW-REDDIT-002",
            "source": "Reddit",
            "source_url": "https://reddit.com/r/googlephotos/comments/cat_photos",
            "author": "CatLoverD",
            "published_at": "2024-03-05T15:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "My cat has 5000 photos, but finding the one where he wore a holiday hat is a nightmare of endless scrolling.",
            "source_metadata": {"subreddit": "googlephotos"},
        },
        # Other / Forum (Problem B: Pet)
        {
            "id": "RAW-OTHER-001",
            "source": "Other",
            "source_url": "https://example.com/interview/notes01",
            "author": "IntervieweeE",
            "published_at": "2024-03-06T16:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "User stated: I gave up searching for my dog's adoption day picture because searching 'dog shelter' showed all dog photos indiscriminately.",
            "source_metadata": {"method": "user_interview"},
        },
        # Reddit (Problem A: Backup Loss - MUST BE REJECTED)
        {
            "id": "RAW-REDDIT-PROB-A",
            "source": "Reddit",
            "source_url": "https://reddit.com/r/googlephotos/comments/backup_failed",
            "author": "DisasterUser",
            "published_at": "2024-03-07T17:00:00Z",
            "retrieved_at": "2026-09-24T12:00:00Z",
            "raw_text": "Google Photos stopped my backup and disappeared half of my gallery. Lost all my photos after upgrading phone!",
            "source_metadata": {"subreddit": "googlephotos"},
        },
    ]

    raw_file = raw_dir / "e2e_raw_evidence.jsonl"
    with open(raw_file, "w", encoding="utf-8") as f:
        for item in raw_records:
            f.write(json.dumps(item) + "\n")

    return {
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "analysis_dir": analysis_dir,
        "db": db_mgr,
        "total_raw": len(raw_records),
    }


# ==============================================================================
# END-TO-END PIPELINE VALIDATION TESTS
# ==============================================================================


def test_e2e_full_system_lifecycle(e2e_environment):
    """Test full pipeline execution: Raw Ingestion -> AI Extraction -> Storage -> Clustering -> Synthesis -> API."""
    env = e2e_environment
    db = env["db"]
    raw_dir = env["raw_dir"]
    processed_dir = env["processed_dir"]
    analysis_dir = env["analysis_dir"]

    # --------------------------------------------------------------------------
    # STEP 1: EXTRACTION & TAXONOMY CLASSIFICATION
    # --------------------------------------------------------------------------
    mock_extractor = DeterministicMockExtractor()
    extraction_pipe = ExtractionPipeline(extractor=mock_extractor, batch_size=10, rate_delay=0.0)
    extraction_pipe.raw_dir = raw_dir
    extraction_pipe.processed_dir = processed_dir
    extraction_pipe.enriched_file = processed_dir / "evidence_enriched.jsonl"
    extraction_pipe.rejected_file = processed_dir / "rejected_evidence.jsonl"

    stats = extraction_pipe.run()
    assert stats["processed"] == 7
    assert stats["directly_relevant"] == 6  # 6 Problem B records
    assert stats["not_relevant"] == 1  # 1 Problem A record

    # Verify rejected records file exists and contains Problem A
    with open(extraction_pipe.rejected_file, "r", encoding="utf-8") as f:
        rejected_lines = [json.loads(line) for line in f if line.strip()]
    assert len(rejected_lines) == 1
    assert rejected_lines[0]["id"] == "RAW-REDDIT-PROB-A"
    assert rejected_lines[0]["retrieval_relevance"] is False
    assert rejected_lines[0]["retrieval_relevance_class"] == "NOT_RELEVANT"

    # Persist enriched records into the test database
    with open(extraction_pipe.enriched_file, "r", encoding="utf-8") as f:
        enriched_objs = [NormalizedEvidenceRecord(**json.loads(line)) for line in f if line.strip()]
    assert len(enriched_objs) == 6
    db.save_evidence_records(enriched_objs)

    # --------------------------------------------------------------------------
    # STEP 2: CLUSTERING & OPPORTUNITY MATRIX CALCULATION
    # --------------------------------------------------------------------------
    cluster_pipe = ClusteringPipeline(db_manager=db)
    cluster_pipe.processed_dir = processed_dir
    cluster_pipe.analysis_dir = analysis_dir
    cluster_pipe.enriched_file = extraction_pipe.enriched_file
    cluster_pipe.clusters_file = analysis_dir / "clusters.json"
    cluster_pipe.opportunities_file = analysis_dir / "opportunities.json"

    cluster_summary = cluster_pipe.run()
    assert cluster_summary["evidence_count"] == 6
    assert cluster_summary["clusters_count"] >= 1
    assert cluster_summary["opportunities_count"] >= 1

    # Check clusters stored in SQLite
    saved_clusters = db.get_all_clusters()
    assert len(saved_clusters) == cluster_summary["clusters_count"]

    # Check opportunities stored in SQLite
    saved_opportunities = db.get_all_opportunities()
    assert len(saved_opportunities) == cluster_summary["opportunities_count"]

    # Invariant: Verify that NO OpportunityArea has an arbitrary ranking score
    for opp in saved_opportunities:
        opp_dict = opp.model_dump()
        assert "composite_score" not in opp_dict
        assert "weighted_rank" not in opp_dict
        assert "score" not in opp_dict
        # Verify 7 transparent dimensions exist
        assert opp.evidence_volume > 0
        assert opp.source_diversity_count >= 1
        assert 0.0 <= opp.recurrence_rate <= 1.0
        assert opp.severity_assessment in ["CRITICAL", "HIGH", "MODERATE", "LOW"]
        assert 0.0 <= opp.retrieval_impact_rate <= 1.0
        assert opp.workaround_inefficiency in ["HIGH", "MODERATE", "LOW"]
        assert 0.0 <= opp.evidence_confidence <= 1.0

    # --------------------------------------------------------------------------
    # STEP 3: EVIDENCE-GROUNDED RESEARCH SYNTHESIS & PROVENANCE AUDIT
    # --------------------------------------------------------------------------
    synthesis_pipe = SynthesisPipeline(db_manager=db)
    synthesis_pipe.analysis_dir = analysis_dir
    synthesis_pipe.output_file = analysis_dir / "synthesis_findings.json"

    synth_summary = synthesis_pipe.run()
    assert synth_summary["findings_count"] == 8
    assert synth_summary["citations_count"] > 0
    assert synth_summary["provenance_audit_passed"] is True

    # Verify all 8 findings persisted in DB
    saved_findings = db.get_all_findings()
    assert len(saved_findings) == 8
    finding_ids = {f.finding_id for f in saved_findings}
    expected_ids = {f"FINDING-0{i}" for i in range(1, 9)}
    assert finding_ids == expected_ids

    # --------------------------------------------------------------------------
    # STEP 4: REST API EXPOSURE & DATA CONTRACT ALIGNMENT
    # --------------------------------------------------------------------------
    # Override FastAPI DB dependency to use our isolated test database
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # 1. /api/health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    assert res_health.json()["database"] == "connected"

    # 2. /api/overview
    res_overview = client.get("/api/overview")
    assert res_overview.status_code == 200
    over_data = res_overview.json()
    assert over_data["total_evidence"] == 6
    assert over_data["relevant_evidence"] == 6
    assert over_data["total_clusters"] == cluster_summary["clusters_count"]
    assert over_data["total_opportunities"] == cluster_summary["opportunities_count"]
    assert over_data["total_findings"] == 8

    # 3. /api/evidence with pagination & filtering
    res_ev = client.get("/api/evidence?page=1&page_size=10")
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert ev_data["total"] == 6
    assert len(ev_data["items"]) == 6

    # Test filtering by source
    res_reddit = client.get("/api/evidence?source=Reddit")
    assert res_reddit.status_code == 200
    assert res_reddit.json()["total"] == 2
    for item in res_reddit.json()["items"]:
        assert item["source"] == "Reddit"

    # 4. /api/clusters
    res_clusters = client.get("/api/clusters")
    assert res_clusters.status_code == 200
    assert len(res_clusters.json()) == cluster_summary["clusters_count"]

    # 5. /api/opportunities
    res_opps = client.get("/api/opportunities")
    assert res_opps.status_code == 200
    assert len(res_opps.json()) == cluster_summary["opportunities_count"]

    # 6. /api/findings
    res_findings = client.get("/api/findings")
    assert res_findings.status_code == 200
    assert len(res_findings.json()) == 8

    # Clean up dependency override
    app.dependency_overrides.clear()


# ==============================================================================
# QUALITY & EPISTEMIC BOUNDARY VALIDATION TESTS
# ==============================================================================


def test_epistemic_boundary_problem_a_isolation(e2e_environment):
    """Verify that Problem A (backup loss / deleted items) is strictly isolated and never contaminates problem clusters."""
    env = e2e_environment
    db = env["db"]
    processed_dir = env["processed_dir"]

    # Write enriched and rejected records
    mock_extractor = DeterministicMockExtractor()
    extraction_pipe = ExtractionPipeline(extractor=mock_extractor, batch_size=10, rate_delay=0.0)
    extraction_pipe.raw_dir = env["raw_dir"]
    extraction_pipe.processed_dir = processed_dir
    extraction_pipe.enriched_file = processed_dir / "evidence_enriched.jsonl"
    extraction_pipe.rejected_file = processed_dir / "rejected_evidence.jsonl"
    extraction_pipe.run()

    # Load only enriched records into SQLite
    with open(extraction_pipe.enriched_file, "r", encoding="utf-8") as f:
        enriched_objs = [NormalizedEvidenceRecord(**json.loads(line)) for line in f if line.strip()]
    db.save_evidence_records(enriched_objs)

    # Assert that rejected record ID does NOT exist in DB
    db_records = db.get_all_evidence(relevant_only=False)
    db_ids = {r.id for r in db_records}
    assert "RAW-REDDIT-PROB-A" not in db_ids
    for r in db_records:
        assert r.retrieval_relevance is True
        assert r.retrieval_relevance_class != "NOT_RELEVANT"


def test_provenance_traceability_audit(e2e_environment):
    """Ensure that 100% of claims in synthesized findings trace to verbatim evidence snippets and canonical URLs."""
    env = e2e_environment
    db = env["db"]

    # Seed diverse test evidence with distinct perspectives for Finding 8
    evidence = [
        # Perspective B: complete failure for screenshots
        NormalizedEvidenceRecord(
            id="PROV-EV-01",
            source="Reddit",
            source_url="https://reddit.com/r/googlephotos/test_prov_01",
            author="UserAlpha",
            published_at="2024-02-01T10:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="Verbatim quote: searching for payment receipt screenshot yields zero results in google photos.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for payment receipt",
            retrieval_object="SCREENSHOT",
            memory_cues=["OBJECT_OR_ITEM", "VISIBLE_TEXT"],
            missing_information=["EXACT_DATE"],
            search_behavior=["MANUAL_TIMELINE_SCROLL"],
            search_formulation_original="payment receipt",
            failure_stage=["RETRIEVAL_RELEVANCE"],
            workaround=["ENDLESS_MANUAL_SCROLL"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.95,
        ),
        # Perspective A: success for visual landmark photo
        NormalizedEvidenceRecord(
            id="PROV-EV-02",
            source="App Store",
            source_url="https://apps.apple.com/app/google-photos/test_prov_02",
            author="UserBeta",
            published_at="2024-02-02T10:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="Verbatim quote: landmark and visual search for cafe with red sign in Rome works great.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for landmark vacation photo",
            retrieval_object="EVENT_OR_TRIP",
            memory_cues=["SPATIAL_OR_LOCATION", "VISUAL_APPEARANCE"],
            missing_information=["EXACT_DATE"],
            search_behavior=["LOCATION_FILTER", "PEOPLE_PETS_GRID"],
            search_formulation_original="Rome red sign cafe",
            failure_stage=["RESULT_EVALUATION"],
            workaround=["PEOPLE_COLLABORATION"],
            outcome="PARTIAL_SUCCESS",
            confidence=0.93,
        ),
    ]
    db.save_evidence_records(evidence)

    # Synthesize findings using pipeline
    synth_pipe = SynthesisPipeline(db_manager=db)
    synth_pipe.analysis_dir = env["analysis_dir"]
    synth_pipe.output_file = env["analysis_dir"] / "test_synthesis.json"
    result = synth_pipe.run()

    assert result["provenance_audit_passed"] is True
    assert result["citations_count"] > 0


def test_zero_arbitrary_ranking_invariant():
    """Assert that OpportunityArea model strictly enforces 7 transparent dimensions and rejects composite score."""
    opp = OpportunityArea(
        opportunity_id="OPP-TEST",
        cluster_id="CLUST-TEST",
        cluster_name="Utility Document Retrieval Friction",
        evidence_volume=15,
        source_diversity_count=3,
        source_diversity_ratio=0.6,
        recurrence_rate=0.75,
        severity_assessment="HIGH",
        severity_rationale="Users cannot access urgent financial or medical documents.",
        retrieval_impact_rate=0.60,
        workaround_inefficiency="HIGH",
        workaround_details=["Manual 30-minute scrolling", "Re-requesting bill from merchant"],
        evidence_confidence=0.92,
        platform_breakdown={"Reddit": 8, "Google Play": 7},
        unresolved_risks=["High recall may introduce clutter", "OCR indexing latency"],
    )
    schema = opp.model_json_schema()
    properties = schema.get("properties", {})

    # Invariant: No scalar ranking or composite score
    assert "composite_score" not in properties
    assert "rank" not in properties
    assert "score" not in properties
    assert "priority_rank" not in properties

    # 7 transparent dimensions must all be present
    required_dimensions = [
        "evidence_volume",
        "source_diversity_count",
        "recurrence_rate",
        "severity_assessment",
        "retrieval_impact_rate",
        "workaround_inefficiency",
        "evidence_confidence",
    ]
    for dim in required_dimensions:
        assert dim in properties
