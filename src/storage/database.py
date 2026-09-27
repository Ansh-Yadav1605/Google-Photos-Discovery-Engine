"""SQLite analytical database storage engine."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import FindingResult


class DatabaseManager:
    """Manages SQLite storage for normalized evidence, problem clusters, and opportunity matrix."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = db_path
        else:
            db_url = settings.DATABASE_URL
            if db_url.startswith("sqlite:///"):
                clean_path = db_url.replace("sqlite:///", "")
                self.db_path = Path(clean_path)
            else:
                self.db_path = settings.DATA_ANALYSIS_DIR / "discovery.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Create tables for evidence, clusters, and opportunities with provenance indices."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Evidence table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    published_at TEXT,
                    retrieved_at TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    language TEXT,
                    country_or_region TEXT,
                    rating REAL,
                    retrieval_relevance INTEGER,
                    retrieval_relevance_class TEXT,
                    retrieval_relevance_reason TEXT,
                    retrieval_scenario TEXT,
                    retrieval_object TEXT,
                    memory_cues TEXT,
                    missing_information TEXT,
                    search_behavior TEXT,
                    search_formulation_original TEXT,
                    search_formulation_normalized TEXT,
                    failure_stage TEXT,
                    workaround TEXT,
                    outcome TEXT,
                    user_goal TEXT,
                    evidence_type TEXT,
                    confidence REAL,
                    cluster_id TEXT
                )
            """
            )

            # 2. Clusters table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clusters (
                    cluster_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    source_diversity INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """
            )

            # 3. Opportunity Matrix table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_matrix (
                    opportunity_id TEXT PRIMARY KEY,
                    cluster_id TEXT NOT NULL,
                    cluster_name TEXT NOT NULL,
                    evidence_volume INTEGER NOT NULL,
                    source_diversity_count INTEGER NOT NULL,
                    source_diversity_ratio REAL NOT NULL,
                    recurrence_rate REAL NOT NULL,
                    severity_assessment TEXT NOT NULL,
                    retrieval_impact_rate REAL NOT NULL,
                    workaround_inefficiency TEXT NOT NULL,
                    evidence_confidence REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (cluster_id) REFERENCES clusters (cluster_id)
                )
            """
            )

            # 4. Synthesis Findings table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS synthesis_findings (
                    finding_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    research_question TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """
            )

            # Create provenance and lookup indices
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_cluster ON evidence(cluster_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_relevance ON evidence(retrieval_relevance_class)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_opp_cluster ON opportunity_matrix(cluster_id)"
            )
            conn.commit()

    def save_evidence_records(self, records: List[NormalizedEvidenceRecord]):
        """Upsert normalized evidence records into the database."""
        if not records:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for r in records:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO evidence (
                        id, source, source_url, title, author, published_at, retrieved_at,
                        raw_text, language, country_or_region, rating, retrieval_relevance,
                        retrieval_relevance_class, retrieval_relevance_reason, retrieval_scenario,
                        retrieval_object, memory_cues, missing_information, search_behavior,
                        search_formulation_original, search_formulation_normalized, failure_stage,
                        workaround, outcome, user_goal, evidence_type, confidence, cluster_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        r.id,
                        r.source,
                        r.source_url,
                        r.title,
                        r.author,
                        r.published_at,
                        r.retrieved_at,
                        r.raw_text,
                        r.language,
                        r.country_or_region,
                        r.rating,
                        1 if r.retrieval_relevance else 0,
                        r.retrieval_relevance_class,
                        r.retrieval_relevance_reason,
                        r.retrieval_scenario,
                        r.retrieval_object,
                        json.dumps(r.memory_cues),
                        json.dumps(r.missing_information),
                        json.dumps(r.search_behavior),
                        r.search_formulation_original,
                        r.search_formulation_normalized,
                        json.dumps(r.failure_stage),
                        json.dumps(r.workaround),
                        r.outcome,
                        r.user_goal,
                        r.evidence_type,
                        r.confidence,
                        r.cluster_id,
                    ),
                )
            conn.commit()
            logger.info(
                f"Saved/Updated {len(records)} evidence records in SQLite database."
            )

    def save_clusters(self, clusters: List[ProblemCluster]):
        """Save discovered problem clusters and update evidence cluster_id foreign keys."""
        if not clusters:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for c in clusters:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO clusters (
                        cluster_id, name, description, evidence_count,
                        source_diversity, confidence, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        c.cluster_id,
                        c.name,
                        c.description,
                        c.evidence_count,
                        c.source_diversity,
                        c.confidence,
                        c.model_dump_json(),
                        c.created_at,
                    ),
                )

                # Update linked evidence rows
                for ev_id in c.evidence_ids:
                    cursor.execute(
                        "UPDATE evidence SET cluster_id = ? WHERE id = ?",
                        (c.cluster_id, ev_id),
                    )

            conn.commit()
            logger.info(
                f"Saved {len(clusters)} clusters and linked evidence IDs."
            )

    def save_opportunities(self, opportunities: List[OpportunityArea]):
        """Save multidimensional opportunity assessments."""
        if not opportunities:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for opp in opportunities:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO opportunity_matrix (
                        opportunity_id, cluster_id, cluster_name, evidence_volume,
                        source_diversity_count, source_diversity_ratio, recurrence_rate,
                        severity_assessment, retrieval_impact_rate, workaround_inefficiency,
                        evidence_confidence, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        opp.opportunity_id,
                        opp.cluster_id,
                        opp.cluster_name,
                        opp.evidence_volume,
                        opp.source_diversity_count,
                        opp.source_diversity_ratio,
                        opp.recurrence_rate,
                        opp.severity_assessment,
                        opp.retrieval_impact_rate,
                        opp.workaround_inefficiency,
                        opp.evidence_confidence,
                        opp.model_dump_json(),
                        opp.created_at,
                    ),
                )
            conn.commit()
            logger.info(
                f"Saved {len(opportunities)} opportunity matrix evaluations."
            )

    def _row_to_evidence(self, row: sqlite3.Row) -> NormalizedEvidenceRecord:
        """Convert a database row into a NormalizedEvidenceRecord."""
        return NormalizedEvidenceRecord(
            id=row["id"],
            source=row["source"],
            source_url=row["source_url"],
            title=row["title"],
            author=row["author"],
            published_at=row["published_at"],
            retrieved_at=row["retrieved_at"],
            raw_text=row["raw_text"],
            language=row["language"],
            country_or_region=row["country_or_region"],
            rating=row["rating"],
            retrieval_relevance=bool(row["retrieval_relevance"]),
            retrieval_relevance_class=row["retrieval_relevance_class"],
            retrieval_relevance_reason=row["retrieval_relevance_reason"],
            retrieval_scenario=row["retrieval_scenario"],
            retrieval_object=row["retrieval_object"],
            memory_cues=json.loads(row["memory_cues"] or "[]"),
            missing_information=json.loads(row["missing_information"] or "[]"),
            search_behavior=json.loads(row["search_behavior"] or "[]"),
            search_formulation_original=row["search_formulation_original"],
            search_formulation_normalized=row["search_formulation_normalized"],
            failure_stage=json.loads(row["failure_stage"] or "[]"),
            workaround=json.loads(row["workaround"] or "[]"),
            outcome=row["outcome"],
            user_goal=row["user_goal"],
            evidence_type=row["evidence_type"] or "USER_STATEMENT",
            confidence=row["confidence"] or 0.0,
            cluster_id=row["cluster_id"],
        )

    def get_all_evidence(
        self, relevant_only: bool = True
    ) -> List[NormalizedEvidenceRecord]:
        """Fetch evidence records from SQLite."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if relevant_only:
                cursor.execute(
                    "SELECT * FROM evidence WHERE retrieval_relevance = 1"
                )
            else:
                cursor.execute("SELECT * FROM evidence")

            rows = cursor.fetchall()
            return [self._row_to_evidence(r) for r in rows]

    def get_evidence_by_id(self, evidence_id: str) -> Optional[NormalizedEvidenceRecord]:
        """Fetch a single evidence record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_evidence(row)
            return None

    def query_evidence(
        self,
        page: int = 1,
        page_size: int = 20,
        relevant_only: Optional[bool] = None,
        source: Optional[str] = None,
        failure_stage: Optional[str] = None,
        memory_cue: Optional[str] = None,
        outcome: Optional[str] = None,
        cluster_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[NormalizedEvidenceRecord], int]:
        """Query evidence with filtering and pagination."""
        clauses = []
        params = []

        if relevant_only is True:
            clauses.append("retrieval_relevance = 1")
        elif relevant_only is False:
            clauses.append("retrieval_relevance = 0")

        if source:
            clauses.append("source = ?")
            params.append(source)

        if cluster_id:
            clauses.append("cluster_id = ?")
            params.append(cluster_id)

        if outcome:
            clauses.append("outcome = ?")
            params.append(outcome)

        if failure_stage:
            clauses.append("failure_stage LIKE ?")
            params.append(f'%"{failure_stage}"%')

        if memory_cue:
            clauses.append("memory_cues LIKE ?")
            params.append(f'%"{memory_cue}"%')

        if search:
            clauses.append("(raw_text LIKE ? OR title LIKE ? OR retrieval_scenario LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term, term])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM evidence {where_sql}", params)
            total = cursor.fetchone()[0]

            limit = max(1, min(100, page_size))
            offset = max(0, (page - 1) * limit)
            query_sql = f"SELECT * FROM evidence {where_sql} ORDER BY retrieved_at DESC LIMIT ? OFFSET ?"
            cursor.execute(query_sql, params + [limit, offset])
            rows = cursor.fetchall()
            items = [self._row_to_evidence(r) for r in rows]

            return items, total

    def get_all_clusters(self) -> List[ProblemCluster]:
        """Fetch all stored problem clusters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM clusters")
            rows = cursor.fetchall()
            return [
                ProblemCluster.model_validate_json(r["payload_json"])
                for r in rows
            ]

    def get_all_opportunities(self) -> List[OpportunityArea]:
        """Fetch all stored opportunity area evaluations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM opportunity_matrix")
            rows = cursor.fetchall()
            return [
                OpportunityArea.model_validate_json(r["payload_json"])
                for r in rows
            ]

    def save_findings(self, findings: List[FindingResult]):
        """Upsert research findings into the database."""
        if not findings:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for f in findings:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO synthesis_findings (
                        finding_id, title, research_question, summary,
                        confidence_score, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        f.finding_id,
                        f.title,
                        f.research_question,
                        f.summary,
                        f.confidence_score,
                        f.model_dump_json(),
                        f.created_at,
                    ),
                )
            conn.commit()
            logger.info(f"Saved {len(findings)} research findings to SQLite database.")

    def get_all_findings(self) -> List[FindingResult]:
        """Fetch all stored research findings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM synthesis_findings ORDER BY finding_id ASC")
            rows = cursor.fetchall()
            return [
                FindingResult.model_validate_json(r["payload_json"])
                for r in rows
            ]

    def get_finding(self, finding_id: str) -> Optional[FindingResult]:
        """Fetch a specific research finding by finding_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM synthesis_findings WHERE finding_id = ?", (finding_id,))
            row = cursor.fetchone()
            if row:
                return FindingResult.model_validate_json(row["payload_json"])
            return None

    def get_cluster_by_id(self, cluster_id: str) -> Optional[ProblemCluster]:
        """Fetch a specific problem cluster by cluster_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM clusters WHERE cluster_id = ?", (cluster_id,))
            row = cursor.fetchone()
            if row:
                return ProblemCluster.model_validate_json(row["payload_json"])
            return None

    def get_opportunity_by_id(self, opportunity_id: str) -> Optional[OpportunityArea]:
        """Fetch a specific opportunity area by opportunity_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM opportunity_matrix WHERE opportunity_id = ?", (opportunity_id,))
            row = cursor.fetchone()
            if row:
                return OpportunityArea.model_validate_json(row["payload_json"])
            return None

    def get_overview_stats(self) -> Dict[str, Any]:
        """Aggregate high-level overview metrics across evidence, clusters, and findings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM evidence")
            total_evidence = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM evidence WHERE retrieval_relevance = 1")
            relevant_evidence = cursor.fetchone()[0]
            irrelevant_evidence = total_evidence - relevant_evidence

            cursor.execute("SELECT source, COUNT(*) FROM evidence GROUP BY source")
            source_breakdown = dict(cursor.fetchall())

            cursor.execute("SELECT MIN(published_at), MAX(published_at) FROM evidence WHERE published_at IS NOT NULL")
            min_pub, max_pub = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) FROM clusters")
            total_clusters = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM opportunity_matrix")
            total_opportunities = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM synthesis_findings")
            total_findings = cursor.fetchone()[0]

            return {
                "total_evidence": total_evidence,
                "relevant_evidence": relevant_evidence,
                "irrelevant_evidence": irrelevant_evidence,
                "relevance_rate": round(relevant_evidence / total_evidence, 3) if total_evidence > 0 else 0.0,
                "source_distribution": source_breakdown,
                "temporal_span": {"earliest": min_pub, "latest": max_pub},
                "total_clusters": total_clusters,
                "total_opportunities": total_opportunities,
                "total_findings": total_findings,
            }
