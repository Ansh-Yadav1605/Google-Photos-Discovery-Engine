"""Ingestion pipeline orchestrator."""

from typing import List, Dict, Any
from pathlib import Path
import json
import time
from src.config.logger import logger

from src.ingestion.query_library import QueryLibrary
from src.ingestion.adapters.reddit_adapter import RedditAdapter
from src.ingestion.adapters.google_play_adapter import GooglePlayAdapter
from src.ingestion.adapters.app_store_adapter import AppStoreAdapter
from src.ingestion.adapters.community_adapter import CommunityAdapter
from src.ingestion.adapters.manual_import_adapter import ManualImportAdapter
from src.models.schema import RawEvidenceRecord
from src.config.settings import settings


class IngestionPipeline:
    """Orchestrates multi-source ingestion of public photo retrieval evidence."""

    def __init__(self):
        self.query_library = QueryLibrary()
        self.adapters = [
            RedditAdapter(),
            GooglePlayAdapter(),
            AppStoreAdapter(),
            CommunityAdapter(),
            ManualImportAdapter(),
        ]
        self.raw_dir = settings.DATA_RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self, query_limit: int = 15, play_limit: int = 40
    ) -> Dict[str, Any]:
        """Execute ingestion across all enabled adapters."""
        logger.info("==================================================")
        logger.info("STARTING PUBLIC DATA INGESTION RUN")
        logger.info("==================================================")

        queries = self.query_library.get_all_queries()
        logger.info(
            f"Loaded {len(queries)} query variations across {len(self.query_library.families)} families."
        )

        total_collected = 0
        source_counts: Dict[str, int] = {}
        all_records: List[RawEvidenceRecord] = []

        for adapter in self.adapters:
            try:
                logger.info(f"Running adapter: {adapter.source_name}...")
                limit = (
                    play_limit
                    if adapter.source_name == "Google Play"
                    else query_limit
                )
                records = adapter.fetch(queries=queries, limit_per_query=limit)

                if records:
                    prefix = adapter.source_name.lower().replace(" ", "_")
                    adapter.save_raw_records(records, filename_prefix=prefix)
                    total_collected += len(records)
                    source_counts[adapter.source_name] = len(records)
                    all_records.extend(records)
                else:
                    source_counts[adapter.source_name] = 0

            except Exception as e:
                logger.error(
                    f"Adapter {adapter.source_name} failed with error: {e}"
                )
                source_counts[adapter.source_name] = 0

        # Save an aggregated master raw file for this run
        timestamp = int(time.time())
        master_file = self.raw_dir / f"master_raw_ingestion_{timestamp}.jsonl"
        with open(master_file, "w", encoding="utf-8") as f:
            for rec in all_records:
                f.write(rec.model_dump_json() + "\n")

        summary = {
            "timestamp": timestamp,
            "total_records": total_collected,
            "source_distribution": source_counts,
            "master_file": str(master_file),
        }

        logger.info("==================================================")
        logger.info(f"INGESTION COMPLETE: {total_collected} total records.")
        for src, count in source_counts.items():
            logger.info(f"  - {src}: {count} records")
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run()
