"""Pydantic data models for AI research synthesis, citations, and provenance verification."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ProvenanceCitation(BaseModel):
    """Verifiable citation linking an assertion directly to a canonical evidence record."""

    evidence_id: str
    source: str
    source_url: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    quote_snippet: str
    claim_supported: str
    confidence: float = 0.0


class ContradictoryEvidence(BaseModel):
    """Explicitly highlights conflicting user perspectives without smoothing over variance."""

    topic: str
    perspective_a: str
    evidence_ids_a: List[str] = Field(default_factory=list)
    perspective_b: str
    evidence_ids_b: List[str] = Field(default_factory=list)
    synthesis_rationale: str


class FindingResult(BaseModel):
    """Structured research finding answering one of the 8 core product research questions."""

    finding_id: str  # e.g. FINDING-01 to FINDING-08
    title: str
    research_question: str
    summary: str
    detailed_analysis: str
    primary_metrics: Dict[str, Any] = Field(default_factory=dict)
    citations: List[ProvenanceCitation] = Field(default_factory=list)
    contradictory_evidence: Optional[ContradictoryEvidence] = None
    implications_for_part2: str
    confidence_score: float = 0.0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SynthesisReport(BaseModel):
    """Complete synthesized research findings report with provenance validation summary."""

    report_id: str
    title: str = "Google Photos Retrieval Friction — Empirical Research Findings Synthesis"
    findings: List[FindingResult] = Field(default_factory=list)
    total_evidence_analyzed: int = 0
    total_clusters_analyzed: int = 0
    provenance_audit_passed: bool = True
    total_citations: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
