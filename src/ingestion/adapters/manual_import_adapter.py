"""Manual import adapter for verified public discussions from YouTube, forums, and exports."""

from typing import List
from pathlib import Path
import json
import csv
from src.config.logger import logger
from src.ingestion.base_adapter import BaseSourceAdapter
from src.models.schema import RawEvidenceRecord
from src.config.settings import settings


class ManualImportAdapter(BaseSourceAdapter):
    """Imports verified, non-synthetic public records from local files in data/raw/manual_imports/."""

    def __init__(self):
        super().__init__(source_name="Manual/Audited Import", delay_seconds=0.0)
        self.import_dir = settings.DATA_RAW_DIR / "manual_imports"
        self.import_dir.mkdir(parents=True, exist_ok=True)

    def fetch(
        self, queries: List[str] = None, limit_per_query: int = 100
    ) -> List[RawEvidenceRecord]:
        records: List[RawEvidenceRecord] = []
        import_files = list(self.import_dir.glob("*.jsonl")) + list(
            self.import_dir.glob("*.csv")
        )

        if not import_files:
            logger.info(
                f"[Manual Import] No import files found in {self.import_dir}."
            )
            return records

        for file_path in import_files:
            try:
                logger.info(f"[Manual Import] Ingesting {file_path.name}...")
                if file_path.suffix == ".jsonl":
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            data = json.loads(line)
                            record = RawEvidenceRecord(**data)
                            records.append(record)

                elif file_path.suffix == ".csv":
                    with open(file_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            record = RawEvidenceRecord(
                                source=row.get("source", "Forum"),
                                source_url=row.get("source_url", ""),
                                title=row.get("title"),
                                author=row.get("author"),
                                published_at=row.get("published_at"),
                                raw_text=row.get("raw_text", ""),
                                language=row.get("language", "en"),
                                country_or_region=row.get("country_or_region"),
                                rating=float(row["rating"])
                                if row.get("rating")
                                else None,
                                metadata=json.loads(row.get("metadata", "{}")),
                            )
                            records.append(record)

            except Exception as e:
                logger.error(
                    f"[Manual Import] Error parsing {file_path.name}: {e}"
                )

        logger.info(
            f"[Manual Import] Successfully imported {len(records)} verified records."
        )
        return records
