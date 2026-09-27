"""Google Play Store source adapter for Google Photos user reviews."""

from typing import List, Optional
import datetime
from src.config.logger import logger
from src.ingestion.base_adapter import BaseSourceAdapter
from src.models.schema import RawEvidenceRecord

try:
    from google_play_scraper import Sort, reviews
    PLAY_SCRAPER_AVAILABLE = True
except ImportError:
    PLAY_SCRAPER_AVAILABLE = False


class GooglePlayAdapter(BaseSourceAdapter):
    """Ingests reviews for Google Photos (com.google.android.apps.photos) from Google Play."""

    PACKAGE_NAME = "com.google.android.apps.photos"

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(source_name="Google Play", delay_seconds=delay_seconds)

    def fetch(
        self, queries: List[str], limit_per_query: int = 50
    ) -> List[RawEvidenceRecord]:
        records: List[RawEvidenceRecord] = []
        if not PLAY_SCRAPER_AVAILABLE:
            logger.warning(
                "[Google Play] google-play-scraper not installed. Returning empty."
            )
            return records

        seen_ids = set()
        # Collect across ratings 1, 2, 3 (high friction) and 4-5 (feature feedback)
        for score in [1, 2, 3, 4]:
            try:
                logger.info(
                    f"[Google Play] Fetching reviews with rating={score}..."
                )
                result, _ = reviews(
                    self.PACKAGE_NAME,
                    lang="en",
                    country="us",
                    sort=Sort.MOST_RELEVANT,
                    count=min(limit_per_query * 2, 150),
                    filter_score_with=score,
                )

                for rev in result:
                    rev_id = rev.get("reviewId")
                    if not rev_id or rev_id in seen_ids:
                        continue

                    content = rev.get("content", "").strip()
                    # Filter for retrieval/search relevance keywords
                    content_lower = content.lower()
                    if not any(
                        kw in content_lower
                        for kw in [
                            "search",
                            "find",
                            "found",
                            "retrieve",
                            "locate",
                            "look for",
                            "screenshot",
                            "old photo",
                            "face",
                            "people",
                            "date",
                            "memory",
                            "memories",
                            "lost",
                        ]
                    ):
                        continue

                    # Filter trivial short reviews
                    if len(content.split()) < 5:
                        continue

                    at_time = rev.get("at")
                    published_at = None
                    if isinstance(at_time, datetime.datetime):
                        published_at = at_time.replace(
                            tzinfo=datetime.timezone.utc
                        ).isoformat()

                    user_name = rev.get("userName", "Google Play User")
                    source_url = f"https://play.google.com/store/apps/details?id={self.PACKAGE_NAME}&reviewId={rev_id}"

                    record = RawEvidenceRecord(
                        source="Google Play",
                        source_url=source_url,
                        title=None,
                        author=user_name,
                        published_at=published_at,
                        raw_text=content,
                        language="en",
                        country_or_region="us",
                        rating=float(rev.get("score", score)),
                        metadata={
                            "thumbsUpCount": rev.get("thumbsUpCount", 0),
                            "appVersion": rev.get("reviewCreatedVersion"),
                        },
                    )
                    records.append(record)
                    seen_ids.add(rev_id)

            except Exception as e:
                logger.error(
                    f"[Google Play] Error fetching rating={score} reviews: {e}"
                )

            self.rate_limit_sleep()

        logger.info(
            f"[Google Play] Completed fetch. Found {len(records)} relevant reviews."
        )
        return records
