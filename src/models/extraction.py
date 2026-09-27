"""Pydantic model for AI extraction output and schema validation."""

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, field_validator
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord

VALID_FAILURE_STAGES = {
    "MEMORY_RECALL",
    "QUERY_FORMULATION",
    "SYSTEM_UNDERSTANDING",
    "RETRIEVAL_RELEVANCE",
    "RESULT_EVALUATION",
    "SEARCH_REFINEMENT",
    "NAVIGATION_OR_DISCOVERABILITY",
    "METADATA_OR_INDEXING",
    "CONTENT_NOT_PRESENT_OR_UNAVAILABLE",
    "OTHER",
}

VALID_OUTCOMES = {
    "SUCCESSFUL_RETRIEVAL",
    "PARTIAL_SUCCESS",
    "FAILED_RETRIEVAL",
    "ABANDONED",
    "UNCLEAR",
}

VALID_RELEVANCE = {
    "DIRECTLY_RELEVANT",
    "INDIRECTLY_RELEVANT",
    "NOT_RELEVANT",
}


class LLMExtractionResult(BaseModel):
    """Pydantic model validating structured extraction output from the LLM."""

    retrieval_relevance_class: Literal[
        "DIRECTLY_RELEVANT", "INDIRECTLY_RELEVANT", "NOT_RELEVANT"
    ]
    retrieval_relevance_reason: str = Field(default="Unspecified")
    retrieval_scenario: Optional[str] = None
    retrieval_object: Optional[str] = None
    memory_cues: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    search_behavior: List[str] = Field(default_factory=list)
    search_formulation_original: Optional[str] = None
    search_formulation_normalized: Optional[str] = None
    failure_stage: List[str] = Field(default_factory=list)
    workaround: List[str] = Field(default_factory=list)
    user_goal: Optional[str] = None
    outcome: Optional[
        Literal[
            "SUCCESSFUL_RETRIEVAL",
            "PARTIAL_SUCCESS",
            "FAILED_RETRIEVAL",
            "ABANDONED",
            "UNCLEAR",
        ]
    ] = "UNCLEAR"
    evidence_type: Literal["USER_STATEMENT", "OBSERVED_BEHAVIOR", "UNCLEAR"] = (
        "USER_STATEMENT"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("failure_stage", mode="before")
    @classmethod
    def validate_failure_stages(cls, v):
        if not isinstance(v, list):
            return []
        cleaned = []
        for stage in v:
            stage_str = str(stage).strip().upper()
            if stage_str in VALID_FAILURE_STAGES:
                cleaned.append(stage_str)
        return cleaned

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.0

    def to_normalized_record(
        self, raw_record: RawEvidenceRecord
    ) -> NormalizedEvidenceRecord:
        """Merge LLM extraction with raw record into canonical NormalizedEvidenceRecord."""
        is_relevant = self.retrieval_relevance_class in [
            "DIRECTLY_RELEVANT",
            "INDIRECTLY_RELEVANT",
        ]

        return NormalizedEvidenceRecord(
            id=raw_record.id,
            source=raw_record.source,
            source_url=raw_record.source_url,
            title=raw_record.title,
            author=raw_record.author,
            published_at=raw_record.published_at,
            retrieved_at=raw_record.retrieved_at,
            raw_text=raw_record.raw_text,
            language=raw_record.language,
            country_or_region=raw_record.country_or_region,
            rating=raw_record.rating,
            retrieval_relevance=is_relevant,
            retrieval_relevance_class=self.retrieval_relevance_class,
            retrieval_relevance_reason=self.retrieval_relevance_reason,
            retrieval_scenario=self.retrieval_scenario if is_relevant else None,
            retrieval_object=self.retrieval_object if is_relevant else None,
            memory_cues=self.memory_cues if is_relevant else [],
            missing_information=self.missing_information if is_relevant else [],
            search_behavior=self.search_behavior if is_relevant else [],
            search_formulation_original=self.search_formulation_original
            if is_relevant
            else None,
            search_formulation_normalized=self.search_formulation_normalized
            if is_relevant
            else None,
            failure_stage=self.failure_stage if is_relevant else [],
            workaround=self.workaround if is_relevant else [],
            outcome=self.outcome,
            user_goal=self.user_goal if is_relevant else None,
            evidence_type=self.evidence_type,
            confidence=self.confidence,
        )
