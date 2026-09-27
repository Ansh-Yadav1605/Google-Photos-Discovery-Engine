"""Batch extraction pipeline orchestrator with idempotency and fault isolation."""

from typing import List, Dict, Set, Optional, Any
from pathlib import Path
import json
import time
from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.extraction.extractor import EvidenceExtractor
from src.extraction.llm_adapter import GroqLLMAdapter


class ExtractionPipeline:
    """Orchestrates batch AI relevance classification and behavioral extraction."""

    def __init__(
        self,
        extractor: Optional[EvidenceExtractor] = None,
        batch_size: int = 10,
        rate_delay: float = 0.5,
    ):
        self.extractor = extractor or EvidenceExtractor()
        self.batch_size = batch_size
        self.rate_delay = rate_delay

        self.raw_dir = settings.DATA_RAW_DIR
        self.processed_dir = settings.DATA_PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.enriched_file = self.processed_dir / "evidence_enriched.jsonl"
        self.rejected_file = self.processed_dir / "rejected_evidence.jsonl"

    def get_processed_ids(self) -> Set[str]:
        """Return the set of already processed record IDs for idempotency."""
        processed_ids = set()
        for filepath in [self.enriched_file, self.rejected_file]:
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if "id" in data:
                                processed_ids.add(data["id"])
                        except Exception:
                            continue
        return processed_ids

    def load_raw_records(self) -> List[RawEvidenceRecord]:
        """Load all raw records from data/raw/ directory, eliminating immediate duplicates by ID."""
        records: List[RawEvidenceRecord] = []
        seen_ids = set()

        raw_files = list(self.raw_dir.glob("*.jsonl"))
        if not raw_files:
            logger.warning(f"No raw .jsonl files found in {self.raw_dir}.")
            return records

        for file_path in raw_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            rec = RawEvidenceRecord(**data)
                            if rec.id not in seen_ids:
                                records.append(rec)
                                seen_ids.add(rec.id)
                        except Exception as parse_err:
                            logger.error(
                                f"Failed to parse line in {file_path.name}: {parse_err}"
                            )
            except Exception as e:
                logger.error(f"Error reading file {file_path.name}: {e}")

        logger.info(
            f"Loaded {len(records)} unique raw records across {len(raw_files)} files."
        )
        return records

    def run(
        self, limit: Optional[int] = None, force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """Execute extraction pipeline over raw evidence."""
        logger.info("==================================================")
        logger.info("STARTING PHASE 2 AI EXTRACTION & CLASSIFICATION")
        logger.info("==================================================")

        raw_records = self.load_raw_records()
        if not raw_records:
            logger.warning("No raw records available to extract.")
            return {"status": "EMPTY", "processed": 0}

        if limit:
            raw_records = raw_records[:limit]

        processed_ids = set() if force_reprocess else self.get_processed_ids()
        logger.info(
            f"Found {len(processed_ids)} already processed records (Idempotency active)."
        )

        records_to_process = [
            r for r in raw_records if r.id not in processed_ids
        ]
        logger.info(
            f"Queued {len(records_to_process)} records for AI extraction (Batch size: {self.batch_size})."
        )

        stats = {
            "total_queued": len(records_to_process),
            "processed": 0,
            "directly_relevant": 0,
            "indirectly_relevant": 0,
            "not_relevant": 0,
            "extraction_failed": 0,
        }

        # Process in batches
        for i in range(0, len(records_to_process), self.batch_size):
            batch = records_to_process[i : i + self.batch_size]
            logger.info(
                f"Processing batch {i // self.batch_size + 1}/{(len(records_to_process) - 1) // self.batch_size + 1} ({len(batch)} records)..."
            )

            for raw_record in batch:
                try:
                    normalized = self.extractor.process_record(raw_record)
                    stats["processed"] += 1

                    if (
                        normalized.retrieval_relevance_class
                        == "DIRECTLY_RELEVANT"
                    ):
                        stats["directly_relevant"] += 1
                        self._append_to_file(self.enriched_file, normalized)
                    elif (
                        normalized.retrieval_relevance_class
                        == "INDIRECTLY_RELEVANT"
                    ):
                        stats["indirectly_relevant"] += 1
                        self._append_to_file(self.enriched_file, normalized)
                    elif (
                        normalized.retrieval_relevance_class == "NOT_RELEVANT"
                    ):
                        stats["not_relevant"] += 1
                        self._append_to_file(self.rejected_file, normalized)
                    else:
                        stats["extraction_failed"] += 1
                        self._append_to_file(self.rejected_file, normalized)

                except Exception as rec_err:
                    logger.error(
                        f"Failure processing record {raw_record.id}: {rec_err}"
                    )
                    stats["extraction_failed"] += 1

                if self.rate_delay > 0:
                    time.sleep(self.rate_delay)

        logger.info("==================================================")
        logger.info(f"PHASE 2 EXTRACTION FINISHED: {stats['processed']} records.")
        logger.info(f"  - Directly Relevant: {stats['directly_relevant']}")
        logger.info(f"  - Indirectly Relevant: {stats['indirectly_relevant']}")
        logger.info(f"  - Not Relevant: {stats['not_relevant']}")
        logger.info(f"  - Extraction Failed: {stats['extraction_failed']}")
        logger.info("==================================================")

        return stats

    def _append_to_file(
        self, filepath: Path, record: NormalizedEvidenceRecord
    ):
        """Append a validated normalized record to destination JSONL."""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")


if __name__ == "__main__":
    pipeline = ExtractionPipeline()
    pipeline.run()
