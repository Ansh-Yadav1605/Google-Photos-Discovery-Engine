"""Phase 3 pipeline orchestrator: Emergent Clustering + Multidimensional Opportunity Matrix."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.clustering.clusterer import EmergentClusterer
from src.clustering.opportunity_matrix import OpportunityMatrixCalculator
from src.storage.database import DatabaseManager


class ClusteringPipeline:
    """Orchestrates Phase 3: Emergent clustering and multidimensional opportunity analysis."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        clusterer: Optional[EmergentClusterer] = None,
        opp_calculator: Optional[OpportunityMatrixCalculator] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.clusterer = clusterer or EmergentClusterer()
        self.opp_calculator = opp_calculator or OpportunityMatrixCalculator()

        self.processed_dir = settings.DATA_PROCESSED_DIR
        self.analysis_dir = settings.DATA_ANALYSIS_DIR
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

        self.enriched_file = self.processed_dir / "evidence_enriched.jsonl"
        self.clusters_file = self.analysis_dir / "clusters.json"
        self.opportunities_file = self.analysis_dir / "opportunities.json"

    def load_enriched_evidence(self) -> List[NormalizedEvidenceRecord]:
        """Load enriched evidence from JSONL file or fallback to SQLite."""
        records: List[NormalizedEvidenceRecord] = []
        if self.enriched_file.exists():
            with open(self.enriched_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        rec = NormalizedEvidenceRecord(**data)
                        records.append(rec)
                    except Exception as e:
                        logger.error(f"Error parsing enriched record: {e}")
        else:
            # Fallback to database
            records = self.db.get_all_evidence(relevant_only=True)

        logger.info(f"Loaded {len(records)} enriched evidence records.")
        return records

    def run(
        self, custom_records: Optional[List[NormalizedEvidenceRecord]] = None
    ) -> Dict[str, Any]:
        """Execute Phase 3 clustering and opportunity evaluation."""
        logger.info("==================================================")
        logger.info(
            "STARTING PHASE 3: EMERGENT CLUSTERING & OPPORTUNITY MATRIX"
        )
        logger.info("==================================================")

        records = (
            custom_records
            if custom_records is not None
            else self.load_enriched_evidence()
        )
        if not records:
            logger.warning("No enriched evidence records found to cluster.")
            return {"status": "EMPTY", "clusters": 0, "opportunities": 0}

        # 1. Ensure records are synced to SQLite
        self.db.save_evidence_records(records)

        # 2. Run Emergent Clustering
        logger.info(
            f"Clustering {len(records)} records across behavioral and semantic vectors..."
        )
        clusters: List[ProblemCluster] = self.clusterer.generate_clusters(
            records
        )
        logger.info(
            f"Discovered {len(clusters)} emergent retrieval problem clusters."
        )

        # Update evidence records in memory and database with assigned cluster_ids
        for cluster in clusters:
            for rec in records:
                if rec.id in cluster.evidence_ids:
                    rec.cluster_id = cluster.cluster_id

        # 3. Calculate Multidimensional Opportunity Matrix
        logger.info(
            "Evaluating multidimensional opportunity matrix (No arbitrary single score)..."
        )
        opportunities: List[OpportunityArea] = (
            self.opp_calculator.evaluate_all(clusters, records)
        )

        # 4. Persist to Database & JSON Snapshots
        self.db.save_clusters(clusters)
        self.db.save_opportunities(opportunities)
        self.db.save_evidence_records(records)

        with open(self.clusters_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps([c.model_dump() for c in clusters], indent=2) + "\n"
            )

        with open(self.opportunities_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps([o.model_dump() for o in opportunities], indent=2)
                + "\n"
            )

        # 5. Summarize Results
        summary = {
            "status": "SUCCESS",
            "evidence_count": len(records),
            "clusters_count": len(clusters),
            "opportunities_count": len(opportunities),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "count": c.evidence_count,
                    "source_diversity": c.source_diversity,
                    "confidence": c.confidence,
                }
                for c in clusters
            ],
            "opportunities": [
                {
                    "opportunity_id": o.opportunity_id,
                    "cluster_name": o.cluster_name,
                    "volume": o.evidence_volume,
                    "source_diversity": o.source_diversity_count,
                    "severity": o.severity_assessment,
                    "impact_rate": o.retrieval_impact_rate,
                    "workaround_inefficiency": o.workaround_inefficiency,
                }
                for o in opportunities
            ],
        }

        logger.info("==================================================")
        logger.info(f"PHASE 3 COMPLETE: Discovered {len(clusters)} clusters.")
        for c in clusters:
            logger.info(
                f"  - [{c.cluster_id}] {c.name} (N={c.evidence_count}, Sources={c.source_diversity}, Conf={c.confidence})"
            )
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = ClusteringPipeline()
    pipeline.run()
