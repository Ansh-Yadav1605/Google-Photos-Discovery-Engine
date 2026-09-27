"""Comprehensive offline unit tests validating Phase 5 FastAPI REST API endpoints.

All test inputs are strictly TEST_FIXTURE_ONLY.
Tests do NOT make live network calls.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from src.api.main import app, get_db
from src.storage.database import DatabaseManager
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import FindingResult, ProvenanceCitation, ContradictoryEvidence


# ==============================================================================
# TEST FIXTURES (TEST_FIXTURE_ONLY)
# ==============================================================================


@pytest.fixture
def mock_db(tmp_path: Path):
    """Create a temporary test database populated with fixtures (TEST_FIXTURE_ONLY)."""
    db_file = tmp_path / "test_api_discovery.db"
    db = DatabaseManager(db_path=db_file)

    # 1. Seed evidence
    evidence_records = [
        NormalizedEvidenceRecord(
            id="TEST_EV_01",
            source="Reddit",
            source_url="https://reddit.com/r/googlephotos/test_fixture_01",
            author="UserAlpha",
            published_at="2024-02-01T10:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Looking for payment receipt screenshot from last month. Search shows zero results.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for payment receipt",
            retrieval_object="SCREENSHOT",
            memory_cues=["OBJECT_OR_ITEM", "TEMPORAL_APPROXIMATE"],
            missing_information=["EXACT_DATE"],
            search_behavior=["KEYWORD_SEARCH"],
            search_formulation_original="payment receipt",
            failure_stage=["RETRIEVAL_RELEVANCE", "QUERY_FORMULATION"],
            workaround=["ENDLESS_MANUAL_SCROLL"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.92,
            cluster_id="CLUST-01",
        ),
        NormalizedEvidenceRecord(
            id="TEST_EV_02",
            source="Google Play",
            source_url="https://play.google.com/store/apps/details?id=test_fixture_02",
            author="UserBeta",
            published_at="2024-02-15T11:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Search cannot find prescription receipt. Scrolling 10000 photos.",
            rating=1.0,
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Searching for medical prescription",
            retrieval_object="HEALTH_OR_MEDICAL",
            memory_cues=["OBJECT_OR_ITEM", "VISIBLE_TEXT"],
            missing_information=["EXACT_DATE"],
            search_behavior=["KEYWORD_SEARCH", "MANUAL_TIMELINE_SCROLL"],
            search_formulation_original="prescription",
            failure_stage=["RETRIEVAL_RELEVANCE", "RESULT_EVALUATION"],
            workaround=["ENDLESS_MANUAL_SCROLL"],
            outcome="FAILED_RETRIEVAL",
            confidence=0.90,
            cluster_id="CLUST-01",
        ),
        NormalizedEvidenceRecord(
            id="TEST_EV_03",
            source="Reddit",
            source_url="https://reddit.com/r/googlephotos/test_fixture_03",
            author="UserGamma",
            published_at="2024-03-01T15:00:00Z",
            retrieved_at="2026-09-24T12:00:00Z",
            raw_text="TEST_FIXTURE_ONLY: Finding cafe photo with red sign from Goa vacation.",
            retrieval_relevance=True,
            retrieval_relevance_class="DIRECTLY_RELEVANT",
            retrieval_scenario="Locating vacation cafe",
            retrieval_object="EVENT_OR_TRIP",
            memory_cues=["SPATIAL_OR_LOCATION", "VISUAL_APPEARANCE"],
            missing_information=["EXACT_DATE"],
            search_behavior=["KEYWORD_SEARCH"],
            search_formulation_original="Goa cafe red sign",
            failure_stage=["MEMORY_RECALL", "RETRIEVAL_RELEVANCE"],
            workaround=["EXTERNAL_APP_SEARCH"],
            outcome="ABANDONED",
            confidence=0.94,
            cluster_id="CLUST-02",
        ),
    ]
    db.save_evidence_records(evidence_records)

    # 2. Seed clusters
    clusters = [
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
            evidence_count=1,
            evidence_ids=["TEST_EV_03"],
            source_diversity=1,
            source_distribution={"Reddit": 1},
            confidence=0.94,
        ),
    ]
    db.save_clusters(clusters)

    # 3. Seed opportunities
    opportunities = [
        OpportunityArea(
            opportunity_id="OPP-01",
            cluster_id="CLUST-01",
            cluster_name="OCR & Text Mismatch in Utility Documents",
            evidence_volume=2,
            source_diversity_count=2,
            source_diversity_ratio=0.4,
            recurrence_rate=1.0,
            severity_assessment="HIGH",
            severity_rationale="High utility loss",
            retrieval_impact_rate=1.0,
            workaround_inefficiency="HIGH",
            evidence_confidence=0.91,
        ),
        OpportunityArea(
            opportunity_id="OPP-02",
            cluster_id="CLUST-02",
            cluster_name="Vague Temporal Anchor Friction for Travel Moments",
            evidence_volume=1,
            source_diversity_count=1,
            source_diversity_ratio=0.2,
            recurrence_rate=1.0,
            severity_assessment="MODERATE",
            severity_rationale="Moderate emotional friction",
            retrieval_impact_rate=1.0,
            workaround_inefficiency="HIGH",
            evidence_confidence=0.94,
        ),
    ]
    db.save_opportunities(opportunities)

    # 4. Seed findings
    findings = [
        FindingResult(
            finding_id="FINDING-01",
            title="Target Memory Objects & Stakes Asymmetry",
            research_question="What memories are hardest to find?",
            summary="Utility documents suffer highest friction",
            detailed_analysis="Detailed analysis on screenshots and receipts",
            citations=[
                ProvenanceCitation(
                    evidence_id="TEST_EV_01",
                    source="Reddit",
                    source_url="https://reddit.com/r/googlephotos/test_fixture_01",
                    quote_snippet="TEST_FIXTURE_ONLY: Looking for payment receipt screenshot",
                    claim_supported="Utility document retrieval breakdown",
                    confidence=0.92,
                )
            ],
            implications_for_part2="Investigate dedicated utility surface",
            confidence_score=0.92,
        ),
        FindingResult(
            finding_id="FINDING-08",
            title="Contradictory Evidence & Multi-Perspective Variance",
            research_question="Where do user reports contradict?",
            summary="Camera photos succeed under CV while screenshots fail",
            detailed_analysis="Media origin divergence",
            citations=[
                ProvenanceCitation(
                    evidence_id="TEST_EV_03",
                    source="Reddit",
                    source_url="https://reddit.com/r/googlephotos/test_fixture_03",
                    quote_snippet="TEST_FIXTURE_ONLY: Finding cafe photo with red sign",
                    claim_supported="Visual recall succeeds partially",
                    confidence=0.94,
                )
            ],
            contradictory_evidence=ContradictoryEvidence(
                topic="Search Effectiveness",
                perspective_a="Works for landmarks",
                evidence_ids_a=["TEST_EV_03"],
                perspective_b="Fails for receipts",
                evidence_ids_b=["TEST_EV_01"],
                synthesis_rationale="EXIF vs OCR divergence",
            ),
            implications_for_part2="Segment research by media origin",
            confidence_score=0.94,
        ),
    ]
    db.save_findings(findings)

    return db


@pytest.fixture
def client(mock_db: DatabaseManager):
    """TestClient overriding DatabaseManager dependency with mock_db (TEST_FIXTURE_ONLY)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# TESTS
# ==============================================================================


def test_api_health(client: TestClient):
    """Verify /api/health endpoint returns 200 with service and database status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == "1.0.0"
    assert "groq_configured" in data


def test_api_overview(client: TestClient):
    """Verify /api/overview aggregates metrics from SQLite database."""
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_evidence"] == 3
    assert data["relevant_evidence"] == 3
    assert data["total_clusters"] == 2
    assert data["total_opportunities"] == 2
    assert data["total_findings"] == 2
    assert "Reddit" in data["source_distribution"]


def test_api_evidence_list_and_pagination(client: TestClient):
    """Verify /api/evidence pagination, total count, and page sizing."""
    # Page 1, size 2
    response = client.get("/api/evidence?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2

    # Page 2, size 2
    response_p2 = client.get("/api/evidence?page=2&page_size=2")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert len(data_p2["items"]) == 1


def test_api_evidence_filtering(client: TestClient):
    """Verify /api/evidence filters by source, failure_stage, and search string."""
    # Filter by source
    resp_source = client.get("/api/evidence?source=Google%20Play")
    assert resp_source.status_code == 200
    data_source = resp_source.json()
    assert data_source["total"] == 1
    assert data_source["items"][0]["id"] == "TEST_EV_02"

    # Filter by search string
    resp_search = client.get("/api/evidence?search=prescription")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert data_search["total"] == 1
    assert data_search["items"][0]["id"] == "TEST_EV_02"

    # Filter by failure_stage
    resp_stage = client.get("/api/evidence?failure_stage=QUERY_FORMULATION")
    assert resp_stage.status_code == 200
    data_stage = resp_stage.json()
    assert data_stage["total"] == 1
    assert data_stage["items"][0]["id"] == "TEST_EV_01"


def test_api_evidence_detail_and_404(client: TestClient):
    """Verify /api/evidence/{id} returns record or 404 for invalid ID."""
    # Existing record
    response = client.get("/api/evidence/TEST_EV_01")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TEST_EV_01"
    assert data["retrieval_object"] == "SCREENSHOT"
    assert "https://reddit.com" in data["source_url"]

    # Non-existent record
    resp_404 = client.get("/api/evidence/NON_EXISTENT_ID")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_api_clusters_list_and_detail(client: TestClient):
    """Verify /api/clusters returns list and /api/clusters/{id} returns cluster with member evidence."""
    # List clusters
    response = client.get("/api/clusters")
    assert response.status_code == 200
    clusters = response.json()
    assert len(clusters) == 2
    assert clusters[0]["cluster_id"] == "CLUST-01"

    # Cluster detail with evidence
    detail_resp = client.get("/api/clusters/CLUST-01")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["cluster"]["cluster_id"] == "CLUST-01"
    assert detail["evidence_count"] == 2
    assert len(detail["evidence_records"]) == 2

    # Cluster 404
    resp_404 = client.get("/api/clusters/CLUST-999")
    assert resp_404.status_code == 404


def test_api_opportunities_list_and_detail(client: TestClient):
    """Verify /api/opportunities returns evaluations with all 7 dimensions and no arbitrary rank."""
    # List opportunities
    response = client.get("/api/opportunities")
    assert response.status_code == 200
    opps = response.json()
    assert len(opps) == 2
    assert opps[0]["opportunity_id"] == "OPP-01"
    assert "severity_assessment" in opps[0]
    assert "retrieval_impact_rate" in opps[0]
    assert "rank" not in opps[0]
    assert "composite_score" not in opps[0]

    # Opportunity detail
    detail_resp = client.get("/api/opportunities/OPP-01")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["cluster_id"] == "CLUST-01"

    # 404
    resp_404 = client.get("/api/opportunities/OPP-999")
    assert resp_404.status_code == 404


def test_api_findings_list_and_detail(client: TestClient):
    """Verify /api/findings returns research findings with citations and contradictory viewpoints."""
    # List findings
    response = client.get("/api/findings")
    assert response.status_code == 200
    findings = response.json()
    assert len(findings) == 2
    assert findings[0]["finding_id"] == "FINDING-01"

    # Finding detail
    detail_resp = client.get("/api/findings/FINDING-08")
    assert detail_resp.status_code == 200
    f8 = detail_resp.json()
    assert f8["finding_id"] == "FINDING-08"
    assert f8["contradictory_evidence"] is not None
    assert len(f8["citations"]) >= 1

    # 404
    resp_404 = client.get("/api/findings/FINDING-999")
    assert resp_404.status_code == 404


def test_api_docs_openapi(client: TestClient):
    """Verify OpenAPI specification and interactive documentation endpoints."""
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "Google Photos Discovery Engine API"
    assert "/api/health" in schema["paths"]
    assert "/api/evidence" in schema["paths"]
    assert "/api/clusters" in schema["paths"]
    assert "/api/opportunities" in schema["paths"]
    assert "/api/findings" in schema["paths"]
    assert "/api/ingest" in schema["paths"]
    assert "/api/analyze" in schema["paths"]


def test_api_analyze_trigger(client: TestClient):
    """Verify /api/analyze triggers Phase 3 and Phase 4 pipelines on database evidence."""
    response = client.post("/api/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["evidence_count"] >= 2
    assert data["clusters_count"] >= 1
    assert data["opportunities_count"] >= 1
    assert data["findings_count"] == 8
    assert data["provenance_audit_passed"] is True
