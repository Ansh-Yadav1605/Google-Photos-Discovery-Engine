"""High-level evidence extraction and classification service."""

from typing import Optional
from src.config.logger import logger
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.models.extraction import LLMExtractionResult
from src.extraction.llm_adapter import GroqLLMAdapter


class EvidenceExtractor:
    """Orchestrates relevance classification and behavioral taxonomy extraction on evidence items."""

    def __init__(self, llm_adapter: Optional[GroqLLMAdapter] = None):
        self.llm_adapter = llm_adapter or GroqLLMAdapter()

    def process_record(
        self, raw_record: RawEvidenceRecord
    ) -> NormalizedEvidenceRecord:
        """Process a single raw record: classify relevance and extract structured attributes."""
        extraction_result: Optional[LLMExtractionResult] = (
            self.llm_adapter.extract(raw_record)
        )

        if extraction_result:
            normalized = extraction_result.to_normalized_record(raw_record)
            return normalized

        # Graceful fallback preserving full provenance when LLM extraction fails or is unconfigured
        logger.warning(
            f"Extraction skipped or failed for record {raw_record.id}. Preserving provenance with null extraction."
        )
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
            retrieval_relevance=None,
            retrieval_relevance_class=None,
            retrieval_relevance_reason="EXTRACTION_FAILED_OR_UNINITIALIZED",
            confidence=0.0,
        )
