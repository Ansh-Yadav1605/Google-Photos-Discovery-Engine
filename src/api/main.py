"""FastAPI Backend REST API for Google Photos Discovery Engine.

Exposes endpoints for:
- System health and overview KPIs
- Paginated & filtered evidence exploration
- Emergent problem clusters & cluster deep dive
- 7-dimensional Opportunity Matrix
- Evidence-grounded AI research findings & citations
- On-demand ingestion and analytical pipeline execution
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
import math
import mimetypes
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure Windows recognizes .jsx and modern web MIME types
mimetypes.add_type("application/javascript", ".jsx")
mimetypes.add_type("text/javascript", ".jsx")
mimetypes.add_type("application/javascript", ".js")

from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import FindingResult
from src.storage.database import DatabaseManager
from src.clustering.pipeline import ClusteringPipeline
from src.synthesis.pipeline import SynthesisPipeline
from src.ingestion.pipeline import IngestionPipeline


# ==============================================================================
# SCHEMAS FOR API REQUESTS & RESPONSES
# ==============================================================================


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    groq_configured: bool


class PaginatedEvidenceResponse(BaseModel):
    items: List[NormalizedEvidenceRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClusterDetailResponse(BaseModel):
    cluster: ProblemCluster
    evidence_count: int
    evidence_records: List[NormalizedEvidenceRecord]


class IngestRequest(BaseModel):
    query_limit: int = Field(default=5, ge=1, le=50)
    play_limit: int = Field(default=10, ge=1, le=100)


class AnalysisResponse(BaseModel):
    status: str
    evidence_count: int
    clusters_count: int
    opportunities_count: int
    findings_count: int
    provenance_audit_passed: bool
    summary: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# FASTAPI APPLICATION SETUP
# ==============================================================================

app = FastAPI(
    title="Google Photos Discovery Engine API",
    description=(
        "Empirical research and evidence discovery engine for Google Photos Core Experience. "
        "Provides grounded user evidence, emergent problem clusters, transparent opportunity comparison, "
        "and verifiable research findings."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend applications (e.g. Vite on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> DatabaseManager:
    """Dependency provider for database manager."""
    return DatabaseManager()


# ==============================================================================
# SYSTEM & OVERVIEW ENDPOINTS
# ==============================================================================


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def get_health(db: DatabaseManager = Depends(get_db)):
    """Check system health, database connectivity, and LLM configuration."""
    db_status = "connected"
    try:
        with db.get_connection() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service="Google Photos Discovery Engine API",
        version="1.0.0",
        database=db_status,
        groq_configured=bool(settings.GROQ_API_KEY),
    )


@app.get("/api/overview", tags=["Overview"])
def get_overview(db: DatabaseManager = Depends(get_db)):
    """Retrieve high-level overview metrics across evidence, sources, clusters, and findings."""
    return db.get_overview_stats()


# ==============================================================================
# EVIDENCE EXPLORER ENDPOINTS
# ==============================================================================


@app.get("/api/evidence", response_model=PaginatedEvidenceResponse, tags=["Evidence"])
def list_evidence(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    relevant_only: Optional[bool] = Query(None, description="Filter for retrieval relevance"),
    source: Optional[str] = Query(None, description="Filter by source platform (e.g. Reddit, Google Play)"),
    failure_stage: Optional[str] = Query(None, description="Filter by failure stage"),
    memory_cue: Optional[str] = Query(None, description="Filter by memory cue"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (e.g. FAILED_RETRIEVAL, ABANDONED)"),
    cluster_id: Optional[str] = Query(None, description="Filter by assigned cluster ID"),
    search: Optional[str] = Query(None, description="Search term in raw text, title, or scenario"),
    db: DatabaseManager = Depends(get_db),
):
    """Retrieve paginated, filterable evidence records."""
    items, total = db.query_evidence(
        page=page,
        page_size=page_size,
        relevant_only=relevant_only,
        source=source,
        failure_stage=failure_stage,
        memory_cue=memory_cue,
        outcome=outcome,
        cluster_id=cluster_id,
        search=search,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedEvidenceResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/evidence/{evidence_id}", response_model=NormalizedEvidenceRecord, tags=["Evidence"])
def get_evidence_item(evidence_id: str, db: DatabaseManager = Depends(get_db)):
    """Retrieve a single evidence record by ID with full provenance metadata."""
    record = db.get_evidence_by_id(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")
    return record


# ==============================================================================
# PROBLEM CLUSTERS ENDPOINTS
# ==============================================================================


@app.get("/api/clusters", response_model=List[ProblemCluster], tags=["Clusters"])
def list_clusters(db: DatabaseManager = Depends(get_db)):
    """Retrieve all discovered emergent problem clusters."""
    return db.get_all_clusters()


@app.get("/api/clusters/{cluster_id}", response_model=ClusterDetailResponse, tags=["Clusters"])
def get_cluster_detail(cluster_id: str, db: DatabaseManager = Depends(get_db)):
    """Retrieve detailed metadata and linked member evidence records for a cluster."""
    cluster = db.get_cluster_by_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found.")

    all_evidence = db.get_all_evidence(relevant_only=False)
    cluster_recs = [r for r in all_evidence if r.id in cluster.evidence_ids or r.cluster_id == cluster_id]

    return ClusterDetailResponse(
        cluster=cluster,
        evidence_count=len(cluster_recs),
        evidence_records=cluster_recs,
    )


# ==============================================================================
# OPPORTUNITY MATRIX ENDPOINTS
# ==============================================================================


@app.get("/api/opportunities", response_model=List[OpportunityArea], tags=["Opportunity Matrix"])
def list_opportunities(db: DatabaseManager = Depends(get_db)):
    """Retrieve comparative multidimensional opportunity evaluations (No single arbitrary rank)."""
    return db.get_all_opportunities()


@app.get("/api/opportunities/{opportunity_id}", response_model=OpportunityArea, tags=["Opportunity Matrix"])
def get_opportunity_detail(opportunity_id: str, db: DatabaseManager = Depends(get_db)):
    """Retrieve a specific opportunity area evaluation."""
    opp = db.get_opportunity_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity area '{opportunity_id}' not found.")
    return opp


# ==============================================================================
# RESEARCH FINDINGS & SYNTHESIS ENDPOINTS
# ==============================================================================


@app.get("/api/findings", response_model=List[FindingResult], tags=["Synthesis"])
def list_findings(db: DatabaseManager = Depends(get_db)):
    """Retrieve the 8 structured research findings with citations and contradictory viewpoints."""
    return db.get_all_findings()


@app.get("/api/findings/{finding_id}", response_model=FindingResult, tags=["Synthesis"])
def get_finding_detail(finding_id: str, db: DatabaseManager = Depends(get_db)):
    """Retrieve a specific synthesized research finding by ID."""
    finding = db.get_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail=f"Research finding '{finding_id}' not found.")
    return finding


# ==============================================================================
# PIPELINE EXECUTION ENDPOINTS
# ==============================================================================


@app.post("/api/ingest", tags=["Pipeline Execution"])
def trigger_ingest(
    request: Optional[IngestRequest] = None,
):
    """Trigger an on-demand public data ingestion run across enabled source adapters."""
    req = request or IngestRequest()
    try:
        pipeline = IngestionPipeline()
        summary = pipeline.run(query_limit=req.query_limit, play_limit=req.play_limit)
        return {
            "status": "SUCCESS",
            "message": f"Ingestion completed: {summary['total_records']} records collected.",
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Error during on-demand ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion run failed: {str(e)}")


@app.post("/api/analyze", response_model=AnalysisResponse, tags=["Pipeline Execution"])
def trigger_analysis(
    db: DatabaseManager = Depends(get_db),
):
    """Trigger Phase 3 Clustering and Phase 4 Research Synthesis on database evidence."""
    try:
        # 1. Run Phase 3: Clustering & Opportunity Matrix
        cluster_pipe = ClusteringPipeline(db_manager=db)
        cluster_summary = cluster_pipe.run()

        # 2. Run Phase 4: Synthesis & Provenance Audit
        synth_pipe = SynthesisPipeline(db_manager=db)
        synth_summary = synth_pipe.run()

        evidence_count = cluster_summary.get("evidence_count", 0)
        clusters_count = cluster_summary.get("clusters_count", 0)
        opportunities_count = cluster_summary.get("opportunities_count", 0)
        findings_count = synth_summary.get("findings_count", 0)
        provenance_audit_passed = synth_summary.get("provenance_audit_passed", False)

        return AnalysisResponse(
            status="SUCCESS",
            evidence_count=evidence_count,
            clusters_count=clusters_count,
            opportunities_count=opportunities_count,
            findings_count=findings_count,
            provenance_audit_passed=provenance_audit_passed,
            summary={
                "clustering": cluster_summary,
                "synthesis": synth_summary,
            },
        )
    except Exception as e:
        logger.error(f"Error during analysis pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline execution failed: {str(e)}")


# ==============================================================================
# STATIC FRONTEND SERVING
# ==============================================================================
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
