"""Comprehensive offline unit tests validating Phase 3 Emergent Clustering & Opportunity Matrix.

All test inputs are strictly TEST_FIXTURE_ONLY.
Tests do NOT make live network calls.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.clustering.clusterer import EmergentClusterer
from src.clustering.opportunity_matrix import OpportunityMatrixCalculator
from src.clustering.pipeline import ClusteringPipeline
from src.storage.database import DatabaseManager


# ==============================================================================
# SYNTHETIC TEST FIXTURES (TEST_FIXTURE_ONLY)
# ==============================================================================


@pytest.fixture
def sample_evidence_fixtures() -> list[NormalizedEvidenceRecord]:
    """Diverse cohort of normalized evidence records across 3 distinct problem domains (TEST_FIXTURE_ONLY)."""
    return [
        # Domain 1: Screenshot & Utility Document OCR failure (High Stakes)
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
        # Domain 2: Vague Temporal Recall for Travel & Social Events (Moderate Stakes)
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
        # Domain 3: People / Face Indexing breakdown (Indirect/Direct Failure)
        NormalizedEvidenceRecord(
            id="TEST_EV_05",
            source="Google Photos Community",
            source_url="https://support.google.com/photos/thread/test_fixture_only_05",
            author="UserEpsilon",
            published_at="2024-04-01T14:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Face recognition stopped clustering photos of my grandmother. Cannot find her old photos through people search.",
            retrieval_relevance=True,
            retrieval_relevance_class="INDIRECTLY_RELEVANT",
            retrieval_scenario="People search failure due to face indexing failure",
            retrieval_object="PERSONAL_PHOTO",
            memory_cues=["PERSON_OR_FACE"],
            missing_information=["EXACT_DATE"],
            search_behavior=["PEOPLE_FILTER"],
            failure_stage=["METADATA_OR_INDEXING", "RETRIEVAL_RELEVANCE"],
            workaround=["THIRD_PARTY_GALLERY"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.85,
        ),
    ]


# ==============================================================================
# 1. FEATURE EXTRACTION & CLUSTERING TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_feature_extraction_dimension(sample_evidence_fixtures):
    """Verify joint vector construction (TF-IDF + failure stages + memory cues) (TEST_FIXTURE_ONLY)."""
    clusterer = EmergentClusterer()
    features = clusterer.extract_features(sample_evidence_fixtures)

    # Features must match sample count and have non-zero dimensions
    assert features.shape[0] == len(sample_evidence_fixtures)
    assert features.shape[1] > 20  # TF-IDF + 10 failure stages + 10 memory cues


def test_emergent_clustering_generation(sample_evidence_fixtures):
    """Verify emergent clusters are discovered without predetermined categories (TEST_FIXTURE_ONLY)."""
    clusterer = EmergentClusterer(min_cluster_size=2)
    clusters = clusterer.generate_clusters(sample_evidence_fixtures)

    assert len(clusters) >= 2
    total_assigned_evidence = sum(c.evidence_count for c in clusters)
    assert total_assigned_evidence == len(sample_evidence_fixtures)

    for c in clusters:
        assert c.cluster_id.startswith("CLUST-")
        assert len(c.name) > 5
        assert len(c.description) > 20
        assert c.source_diversity >= 1
        assert len(c.representative_evidence_ids) >= 1
        assert len(c.unresolved_questions) >= 1


# ==============================================================================
# 2. MULTIDIMENSIONAL OPPORTUNITY MATRIX TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_opportunity_matrix_transparency_and_no_single_score(sample_evidence_fixtures):
    """CRITICAL TEST: Verify all 7 dimensions exist independently with NO single composite score (TEST_FIXTURE_ONLY)."""
    clusterer = EmergentClusterer(min_cluster_size=2)
    clusters = clusterer.generate_clusters(sample_evidence_fixtures)

    calculator = OpportunityMatrixCalculator()
    opportunities = calculator.evaluate_all(clusters, sample_evidence_fixtures)

    assert len(opportunities) == len(clusters)

    for opp in opportunities:
        # 1. Volume
        assert opp.evidence_volume > 0
        # 2. Source Diversity
        assert opp.source_diversity_count >= 1
        assert 0.0 <= opp.source_diversity_ratio <= 1.0
        # 3. Recurrence
        assert 0.0 <= opp.recurrence_rate <= 1.0
        # 4. Severity Assessment & Rationale
        assert opp.severity_assessment in ["HIGH", "MODERATE", "LOW"]
        assert len(opp.severity_rationale) > 10
        # 5. Retrieval Impact
        assert 0.0 <= opp.retrieval_impact_rate <= 1.0
        # 6. Workaround Inefficiency
        assert opp.workaround_inefficiency in ["HIGH", "MODERATE", "LOW"]
        assert isinstance(opp.workaround_details, list)
        # 7. Evidence Confidence
        assert 0.0 <= opp.evidence_confidence <= 1.0

        # Anti-Pattern Check: Enforce NO arbitrary single 'composite_score' or 'rank' attribute
        opp_dict = opp.model_dump()
        assert "composite_score" not in opp_dict
        assert "rank" not in opp_dict
        assert "winner" not in opp_dict


def test_high_stakes_severity_detection(sample_evidence_fixtures):
    """Verify that financial/medical screenshots trigger HIGH severity (TEST_FIXTURE_ONLY)."""
    calculator = OpportunityMatrixCalculator()

    # Create synthetic cluster with screenshot/medical records
    cluster = ProblemCluster(
        cluster_id="CLUST-01",
        name="OCR & Entity Mismatch for Receipts",
        description="Friction in finding receipts",
        evidence_count=2,
        evidence_ids=["TEST_EV_01", "TEST_EV_02"],
        source_diversity=2,
        source_distribution={"Reddit": 1, "Google Play": 1},
        confidence=0.91,
    )

    opp = calculator.evaluate_cluster(cluster, sample_evidence_fixtures)
    assert opp.severity_assessment == "HIGH"
    assert "utility loss" in opp.severity_rationale.lower()
    assert opp.retrieval_impact_rate == 1.0  # Both failed retrieval


# ==============================================================================
# 3. PROVENANCE CHAIN & TRACEABILITY TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_full_provenance_traceability(sample_evidence_fixtures):
    """Verify unbroken chain: Opportunity -> Cluster -> Evidence ID -> Canonical Source URL -> Raw Text (TEST_FIXTURE_ONLY)."""
    clusterer = EmergentClusterer(min_cluster_size=2)
    clusters = clusterer.generate_clusters(sample_evidence_fixtures)

    calculator = OpportunityMatrixCalculator()
    opportunities = calculator.evaluate_all(clusters, sample_evidence_fixtures)

    evidence_by_id = {r.id: r for r in sample_evidence_fixtures}

    for opp in opportunities:
        matched_cluster = next((c for c in clusters if c.cluster_id == opp.cluster_id), None)
        assert matched_cluster is not None

        # Verify each linked evidence record has complete provenance
        for ev_id in matched_cluster.evidence_ids:
            ev = evidence_by_id[ev_id]
            assert ev.id == ev_id
            assert ev.source_url.startswith("https://")
            assert ev.published_at is not None
            assert len(ev.raw_text) > 10


# ==============================================================================
# 4. SQLITE DATABASE PERSISTENCE & PIPELINE TESTS (TEST_FIXTURE_ONLY)
# ==============================================================================


def test_sqlite_database_roundtrip(tmp_path, sample_evidence_fixtures):
    """Verify SQLite storage engine saves and queries evidence, clusters, and opportunities (TEST_FIXTURE_ONLY)."""
    db_file = tmp_path / "test_discovery.db"
    db = DatabaseManager(db_path=db_file)

    # 1. Save evidence
    db.save_evidence_records(sample_evidence_fixtures)
    loaded_evidence = db.get_all_evidence(relevant_only=True)
    assert len(loaded_evidence) == len(sample_evidence_fixtures)

    # 2. Cluster & save
    clusterer = EmergentClusterer(min_cluster_size=2)
    clusters = clusterer.generate_clusters(sample_evidence_fixtures)
    db.save_clusters(clusters)
    loaded_clusters = db.get_all_clusters()
    assert len(loaded_clusters) == len(clusters)

    # 3. Opportunity matrix & save
    calculator = OpportunityMatrixCalculator()
    opportunities = calculator.evaluate_all(clusters, sample_evidence_fixtures)
    db.save_opportunities(opportunities)
    loaded_opps = db.get_all_opportunities()
    assert len(loaded_opps) == len(opportunities)


def test_clustering_pipeline_orchestration(tmp_path, sample_evidence_fixtures):
    """Verify ClusteringPipeline execution and snapshot exports (TEST_FIXTURE_ONLY)."""
    db_file = tmp_path / "test_pipeline.db"
    db = DatabaseManager(db_path=db_file)

    pipeline = ClusteringPipeline(db_manager=db)
    pipeline.analysis_dir = tmp_path
    pipeline.clusters_file = tmp_path / "clusters.json"
    pipeline.opportunities_file = tmp_path / "opportunities.json"

    summary = pipeline.run(custom_records=sample_evidence_fixtures)

    assert summary["status"] == "SUCCESS"
    assert summary["clusters_count"] >= 2
    assert summary["opportunities_count"] >= 2

    # Verify JSON snapshot persistence
    assert pipeline.clusters_file.exists()
    assert pipeline.opportunities_file.exists()

    with open(pipeline.clusters_file, "r", encoding="utf-8") as f:
        saved_clusters = json.load(f)
        assert len(saved_clusters) == summary["clusters_count"]

    with open(pipeline.opportunities_file, "r", encoding="utf-8") as f:
        saved_opps = json.load(f)
        assert len(saved_opps) == summary["opportunities_count"]
