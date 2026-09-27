"""Google Photos Help Community and public forum adapter."""

from typing import List
import requests
from bs4 import BeautifulSoup
from src.config.logger import logger
from src.ingestion.base_adapter import BaseSourceAdapter
from src.models.schema import RawEvidenceRecord


class CommunityAdapter(BaseSourceAdapter):
    """Adapter for authentic public Google Photos Help Community threads."""

    def __init__(self, delay_seconds: float = 2.0):
        super().__init__(
            source_name="Google Photos Community", delay_seconds=delay_seconds
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(
        self, queries: List[str], limit_per_query: int = 10
    ) -> List[RawEvidenceRecord]:
        records: List[RawEvidenceRecord] = []
        seen_urls = set()

        for query in queries[:4]:
            try:
                # Query public search endpoint for support.google.com/photos
                search_url = "https://html.duckduckgo.com/html/"
                data = {"q": f"site:support.google.com/photos/thread {query}"}
                logger.info(f"[Community] Searching forum threads for: '{query}'")

                resp = requests.post(
                    search_url, data=data, headers=self.headers, timeout=12
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[Community] HTTP {resp.status_code} on search query"
                    )
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.find_all("div", class_="result")

                for res in results[:limit_per_query]:
                    title_elem = res.find("a", class_="result__url")
                    snippet_elem = res.find("a", class_="result__snippet")

                    if not title_elem:
                        continue

                    raw_href = title_elem.get("href", "")
                    # Extract target url from DuckDuckGo redirect if needed
                    target_url = raw_href
                    if "uddg=" in raw_href:
                        import urllib.parse

                        parsed = urllib.parse.parse_qs(
                            urllib.parse.urlparse(raw_href).query
                        )
                        target_url = parsed.get("uddg", [raw_href])[0]

                    if (
                        target_url in seen_urls
                        or "support.google.com/photos/thread" not in target_url
                    ):
                        continue

                    title = title_elem.get_text(strip=True)
                    snippet = (
                        snippet_elem.get_text(strip=True)
                        if snippet_elem
                        else ""
                    )

                    combined_text = (
                        f"{title}\n\n{snippet}" if snippet else title
                    )
                    if len(combined_text.split()) < 4:
                        continue

                    record = RawEvidenceRecord(
                        source="Google Photos Community",
                        source_url=target_url,
                        title=title,
                        author="Community User",
                        published_at=None,
                        raw_text=combined_text,
                        language="en",
                        metadata={"search_query": query},
                    )
                    records.append(record)
                    seen_urls.add(target_url)

            except Exception as e:
                logger.error(
                    f"[Community] Error querying forum threads for '{query}': {e}"
                )

            self.rate_limit_sleep()

        logger.info(
            f"[Community] Completed fetch. Found {len(records)} forum records."
        )
        return records
