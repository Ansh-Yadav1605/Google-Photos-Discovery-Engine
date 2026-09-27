"""Apple App Store adapter for iOS Google Photos user reviews."""

from typing import List
import requests
import datetime
from src.config.logger import logger
from src.ingestion.base_adapter import BaseSourceAdapter
from src.models.schema import RawEvidenceRecord


class AppStoreAdapter(BaseSourceAdapter):
    """Fetches public iOS App Store reviews for Google Photos (App ID: 962194608)."""

    APP_ID = "962194608"
    REGIONS = ["us", "gb", "in", "ca"]

    def __init__(self, delay_seconds: float = 1.2):
        super().__init__(source_name="App Store", delay_seconds=delay_seconds)
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def fetch(
        self, queries: List[str], limit_per_query: int = 50
    ) -> List[RawEvidenceRecord]:
        records: List[RawEvidenceRecord] = []
        seen_ids = set()

        for region in self.REGIONS:
            for page in [1, 2]:
                try:
                    url = f"https://itunes.apple.com/{region}/rss/customerreviews/page={page}/id={self.APP_ID}/sortby=mostrecent/json"
                    logger.info(
                        f"[App Store] Fetching region={region}, page={page}..."
                    )
                    resp = requests.get(url, headers=self.headers, timeout=10)

                    if resp.status_code != 200:
                        logger.warning(
                            f"[App Store] HTTP {resp.status_code} for region {region}"
                        )
                        continue

                    data = resp.json()
                    entries = data.get("feed", {}).get("entry", [])
                    # Skip first entry if it's application metadata
                    for entry in entries[1:]:
                        rev_id = entry.get("id", {}).get("label")
                        if not rev_id or rev_id in seen_ids:
                            continue

                        title = entry.get("title", {}).get("label", "")
                        content = entry.get("content", {}).get("label", "")
                        rating_str = entry.get("im:rating", {}).get(
                            "label", "3"
                        )
                        author = entry.get("author", {}).get(
                            "name", {}
                        ).get("label", "iOS User")
                        updated = entry.get("updated", {}).get("label")

                        combined_text = (
                            f"{title}: {content}" if title else content
                        )
                        combined_lower = combined_text.lower()

                        # Retrieval filter
                        if not any(
                            kw in combined_lower
                            for kw in [
                                "search",
                                "find",
                                "found",
                                "retrieve",
                                "locate",
                                "look for",
                                "screenshot",
                                "album",
                                "missing",
                                "face",
                                "people",
                                "date",
                                "memory",
                                "memories",
                                "scroll",
                            ]
                        ):
                            continue

                        if len(combined_text.split()) < 4:
                            continue

                        canonical_url = f"https://apps.apple.com/{region}/app/google-photos/id{self.APP_ID}?reviewId={rev_id}"

                        record = RawEvidenceRecord(
                            source="App Store",
                            source_url=canonical_url,
                            title=title,
                            author=author,
                            published_at=updated,
                            raw_text=combined_text.strip(),
                            language="en",
                            country_or_region=region,
                            rating=float(rating_str)
                            if rating_str.isdigit()
                            else None,
                            metadata={"region": region, "entry_id": rev_id},
                        )
                        records.append(record)
                        seen_ids.add(rev_id)

                except Exception as e:
                    logger.error(
                        f"[App Store] Error fetching region {region} page {page}: {e}"
                    )

                self.rate_limit_sleep()

        logger.info(
            f"[App Store] Completed fetch. Found {len(records)} relevant reviews."
        )
        return records
