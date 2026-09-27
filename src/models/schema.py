"""Canonical schemas for evidence data models."""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class RawEvidenceRecord(BaseModel):
    """Raw record captured directly by a source adapter before normalization."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Literal[
        "Google Play",
        "App Store",
        "Reddit",
        "Google Photos Community",
        "YouTube",
        "Forum",
        "Other",
    ]
    source_url: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw_text: str
    language: Optional[str] = "en"
    country_or_region: Optional[str] = None
    rating: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedEvidenceRecord(BaseModel):
    """Standardized normalized evidence schema across all ingestion sources."""

    id: str
    source: Literal[
        "Google Play",
        "App Store",
        "Reddit",
        "Google Photos Community",
        "YouTube",
        "Forum",
        "Other",
    ]
    source_url: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str
    raw_text: str
    language: Optional[str] = "en"
    country_or_region: Optional[str] = None
    rating: Optional[float] = None

    # Relevance classification
    retrieval_relevance: Optional[bool] = None
    retrieval_relevance_class: Optional[
        Literal["DIRECTLY_RELEVANT", "INDIRECTLY_RELEVANT", "NOT_RELEVANT"]
    ] = None
    retrieval_relevance_reason: Optional[str] = None

    # Extraction taxonomy attributes
    retrieval_scenario: Optional[str] = None
    retrieval_object: Optional[str] = None
    memory_cues: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    search_behavior: List[str] = Field(default_factory=list)
    search_formulation_original: Optional[str] = None
    search_formulation_normalized: Optional[str] = None

    @property
    def search_formulation(self) -> Dict[str, Optional[str]]:
        return {
            "original_query": self.search_formulation_original,
            "normalized_query": self.search_formulation_normalized,
        }
    failure_stage: List[str] = Field(default_factory=list)
    workaround: List[str] = Field(default_factory=list)
    outcome: Optional[str] = None
    user_goal: Optional[str] = None

    # Metadata & Provenance
    evidence_type: Literal["USER_STATEMENT", "OBSERVED_BEHAVIOR", "UNCLEAR"] = (
        "USER_STATEMENT"
    )
    confidence: float = 0.0
    cluster_id: Optional[str] = None
