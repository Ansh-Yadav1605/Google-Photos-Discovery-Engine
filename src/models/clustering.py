"""Pydantic models for emergent problem clusters and multidimensional opportunity matrix."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ProblemCluster(BaseModel):
    """Represents an emergent retrieval problem cluster discovered from evidence."""

    cluster_id: str
    name: str
    description: str
    evidence_count: int = 0
    evidence_ids: List[str] = Field(default_factory=list)
    source_diversity: int = 0  # Number of unique platforms
    source_distribution: Dict[str, int] = Field(default_factory=dict)
    affected_failure_stages: Dict[str, int] = Field(default_factory=dict)
    dominant_retrieval_objects: List[str] = Field(default_factory=list)
    recurring_behaviors: List[str] = Field(default_factory=list)
    common_workarounds: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    representative_evidence_ids: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OpportunityArea(BaseModel):
    """Multidimensional opportunity assessment for a problem cluster.

    CRITICAL RULE: No single arbitrary 'winner' score. All dimensions are surfaced
    transparently for PM comparison.
    """

    opportunity_id: str
    cluster_id: str
    cluster_name: str

    # 7 Core Evidence Dimensions
    evidence_volume: int = 0  # Total unique evidence count (N)
    source_diversity_count: int = 0  # Number of distinct platforms represented
    source_diversity_ratio: float = 0.0  # Diversity relative to total available sources
    recurrence_rate: float = 0.0  # Proportion of unique authors across timeframes
    severity_assessment: str = "MODERATE"  # HIGH | MODERATE | LOW with factual rationale
    severity_rationale: str = ""
    retrieval_impact_rate: float = 0.0  # Proportion of queries ending in complete failure/abandonment
    workaround_inefficiency: str = "HIGH"  # HIGH | MODERATE | LOW friction of compensatory actions
    workaround_details: List[str] = Field(default_factory=list)
    evidence_confidence: float = 0.0  # Average model & source extraction confidence (0-1)

    # Detailed distributions for PM comparison
    platform_breakdown: Dict[str, int] = Field(default_factory=dict)
    temporal_span: Optional[Dict[str, Optional[str]]] = None  # min_date, max_date
    unresolved_risks: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
