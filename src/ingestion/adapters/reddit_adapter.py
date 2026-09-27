"""Reddit source adapter for public retrieval discussions."""

from typing import List
import requests
import datetime
from src.config.logger import logger
from src.ingestion.base_adapter import BaseSourceAdapter
from src.models.schema import RawEvidenceRecord
from src.config.settings import settings


class RedditAdapter(BaseSourceAdapter):
    """Fetches public discussions from Reddit across key subreddits."""

    SUBREDDITS = ["googlephotos", "google", "Android", "techsupport"]

    def __init__(self, delay_seconds: float = 1.5):
        super().__init__(source_name="Reddit", delay_seconds=delay_seconds)
        self.headers = {
            "User-Agent": settings.REDDIT_USER_AGENT
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(
        self, queries: List[str], limit_per_query: int = 15
    ) -> List[RawEvidenceRecord]:
        records: List[RawEvidenceRecord] = []
        seen_urls = set()

        for subreddit in self.SUBREDDITS:
            for query in queries:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/search.json"
                    params = {
                        "q": query,
                        "restrict_sr": 1,
                        "sort": "relevance",
                        "limit": min(limit_per_query, 25),
                    }
                    logger.info(
                        f"[Reddit] Searching r/{subreddit} for: '{query}'"
                    )

                    resp = requests.get(
                        url, headers=self.headers, params=params, timeout=10
                    )

                    if resp.status_code == 429:
                        logger.warning(
                            f"[Reddit] Rate limit (429) hit on r/{subreddit}. Backing off..."
                        )
                        self.rate_limit_sleep(5.0)
                        continue

                    if resp.status_code != 200:
                        logger.warning(
                            f"[Reddit] HTTP {resp.status_code} for r/{subreddit} query '{query}'"
                        )
                        self.rate_limit_sleep()
                        continue

                    data = resp.json()
                    children = data.get("data", {}).get("children", [])

                    for child in children:
                        post = child.get("data", {})
                        permalink = post.get("permalink", "")
                        canonical_url = f"https://www.reddit.com{permalink}"

                        if (
                            canonical_url in seen_urls
                            or not permalink
                            or post.get("over_18", False)
                        ):
                            continue

                        title = post.get("title", "")
                        selftext = post.get("selftext", "")
                        combined_text = (
                            f"{title}\n\n{selftext}" if selftext else title
                        )

                        # Filter out empty or deleted posts
                        if len(combined_text.split()) < 4 or selftext in [
                            "[deleted]",
                            "[removed]",
                        ]:
                            continue

                        created_utc = post.get("created_utc")
                        published_at = None
                        if created_utc:
                            published_at = datetime.datetime.fromtimestamp(
                                created_utc, tz=datetime.timezone.utc
                            ).isoformat()

                        author = post.get("author", "[anonymous]")

                        record = RawEvidenceRecord(
                            source="Reddit",
                            source_url=canonical_url,
                            title=title,
                            author=author,
                            published_at=published_at,
                            raw_text=combined_text.strip(),
                            language="en",
                            metadata={
                                "subreddit": subreddit,
                                "score": post.get("score", 0),
                                "num_comments": post.get("num_comments", 0),
                                "search_query": query,
                            },
                        )
                        records.append(record)
                        seen_urls.add(canonical_url)

                except Exception as e:
                    logger.error(
                        f"[Reddit] Error querying r/{subreddit} for '{query}': {e}"
                    )

                self.rate_limit_sleep()

        logger.info(
            f"[Reddit] Completed fetch. Collected {len(records)} authentic records."
        )
        return records
