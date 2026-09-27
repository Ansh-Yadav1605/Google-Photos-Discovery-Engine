"""Base class for all data source adapters."""

from abc import ABC, abstractmethod
from typing import List, Optional
import time
from pathlib import Path
import json
from src.config.logger import logger
from src.models.schema import RawEvidenceRecord
from src.config.settings import settings


class BaseSourceAdapter(ABC):
    """Abstract Base Class for public data source ingestion."""

    def __init__(self, source_name: str, delay_seconds: float = 1.0):
        self.source_name = source_name
        self.delay_seconds = delay_seconds
        self.raw_dir = settings.DATA_RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch(
        self, queries: List[str], limit_per_query: int = 15
    ) -> List[RawEvidenceRecord]:
        """Fetch raw evidence items matching the given query list."""
        pass

    def rate_limit_sleep(self, custom_delay: Optional[float] = None):
        """Sleep politely to respect source rate limits."""
        duration = (
            custom_delay if custom_delay is not None else self.delay_seconds
        )
        time.sleep(duration)

    def save_raw_records(
        self, records: List[RawEvidenceRecord], filename_prefix: str
    ) -> Path:
        """Persist raw records directly to immutable JSONL audit files."""
        if not records:
            logger.warning(
                f"[{self.source_name}] No records to save for {filename_prefix}."
            )
            return self.raw_dir

        out_path = self.raw_dir / f"{filename_prefix}_{int(time.time())}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")

        logger.info(
            f"[{self.source_name}] Saved {len(records)} raw records to {out_path}."
        )
        return out_path
