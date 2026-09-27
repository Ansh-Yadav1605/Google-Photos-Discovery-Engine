"""Configurable query library for discovering photo retrieval discussions."""

from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class QueryFamily:
    name: str
    description: str
    queries: List[str] = field(default_factory=list)


class QueryLibrary:
    """Central repository of retrieval-focused search query families."""

    def __init__(self):
        self.families: Dict[str, QueryFamily] = {
            "search_failure": QueryFamily(
                name="Search Failure & Frustration",
                description="Queries indicating general failure to locate photos or broken search capabilities",
                queries=[
                    "can't find old photos",
                    "can't find a photo Google Photos",
                    "Google Photos search not finding",
                    "Google Photos search old photos",
                    "Google Photos search doesn't work",
                    "Google Photos search broken",
                    "Google Photos cannot locate picture",
                ],
            ),
            "imprecise_memory": QueryFamily(
                name="Imprecise Memory & Vague Recall",
                description="Queries where users remember partial visual, emotional, or temporal clues",
                queries=[
                    "Google Photos remember photo can't find",
                    "Google Photos search by description",
                    "Google Photos find memory",
                    "Google Photos find photo don't know date",
                    "Google Photos search what I remember",
                    "Google Photos natural language search failed",
                ],
            ),
            "entity_context": QueryFamily(
                name="Entity & Contextual Queries",
                description="Queries targeting specific entities (people, places, dates, documents, screenshots)",
                queries=[
                    "Google Photos search people",
                    "Google Photos search location",
                    "Google Photos search date",
                    "Google Photos can't find screenshot",
                    "Google Photos can't find document",
                    "Google Photos search receipt",
                    "Google Photos search medicine",
                ],
            ),
            "relevance_and_noise": QueryFamily(
                name="Relevance & Result Evaluation",
                description="Queries where search produced irrelevant results or too much noise",
                queries=[
                    "Google Photos relevant search results",
                    "Google Photos search wrong pictures",
                    "Google Photos search shows random photos",
                    "Google Photos Ask Photos irrelevant",
                    "Google Photos search filter missing",
                ],
            ),
        }

    def get_all_queries(self) -> List[str]:
        """Return a flat unique list of all queries across all families."""
        queries = []
        for family in self.families.values():
            queries.extend(family.queries)
        return list(dict.fromkeys(queries))

    def get_queries_by_family(self, family_name: str) -> List[str]:
        """Return queries for a specific family."""
        if family_name in self.families:
            return self.families[family_name].queries
        return []

    def get_keywords_for_app_reviews(self) -> List[str]:
        """High-signal keywords for searching within app store reviews."""
        return [
            "search",
            "find photo",
            "can't find",
            "retrieve",
            "screenshot",
            "old photos",
            "face",
            "memories",
            "filter",
        ]
