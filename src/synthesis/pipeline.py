"""Phase 4 pipeline orchestrator: AI Research Synthesis & Provenance Verification."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea
from src.models.synthesis import FindingResult, SynthesisReport
from src.storage.database import DatabaseManager
from src.synthesis.synthesizer import ResearchSynthesizer
from src.synthesis.provenance_checker import ProvenanceChecker

try:
    from src.extraction.llm_adapter import GroqLLMAdapter
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class SynthesisPipeline:
    """Orchestrates Phase 4: Grounded research synthesis, provenance auditing, and persistence."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        synthesizer: Optional[ResearchSynthesizer] = None,
        provenance_checker: Optional[ProvenanceChecker] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.synthesizer = synthesizer or ResearchSynthesizer()
        self.checker = provenance_checker or ProvenanceChecker()

        self.analysis_dir = settings.DATA_ANALYSIS_DIR
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.findings_file = self.analysis_dir / "synthesis_findings.json"

    def run(
        self,
        custom_evidence: Optional[List[NormalizedEvidenceRecord]] = None,
        custom_clusters: Optional[List[ProblemCluster]] = None,
        custom_opportunities: Optional[List[OpportunityArea]] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 4 synthesis and provenance verification."""
        logger.info("==================================================")
        logger.info("STARTING PHASE 4: AI RESEARCH SYNTHESIS & PROVENANCE")
        logger.info("==================================================")

        # 1. Load inputs
        evidence = (
            custom_evidence
            if custom_evidence is not None
            else self.db.get_all_evidence(relevant_only=True)
        )
        clusters = (
            custom_clusters
            if custom_clusters is not None
            else self.db.get_all_clusters()
        )
        opportunities = (
            custom_opportunities
            if custom_opportunities is not None
            else self.db.get_all_opportunities()
        )

        logger.info(
            f"Loaded {len(evidence)} evidence records, {len(clusters)} clusters, and {len(opportunities)} opportunities."
        )

        if not evidence:
            logger.warning("No evidence records available for synthesis.")
            return {"status": "EMPTY", "findings_count": 0, "audit_passed": False}

        # 2. Synthesize Findings 1-8
        logger.info("Synthesizing 8 core evidence-grounded research findings...")
        findings: List[FindingResult] = self.synthesizer.synthesize_all(
            evidence=evidence,
            clusters=clusters,
            opportunities=opportunities,
        )

        # 3. Provenance Audit
        logger.info("Auditing provenance chain and citations against canonical database records...")
        self.checker.set_evidence(evidence)
        audit_result = self.checker.audit_all(findings)

        if not audit_result.is_valid:
            logger.error(f"Provenance audit found {len(audit_result.errors)} violations!")
            for err in audit_result.errors:
                logger.error(f"  - {err}")
        else:
            logger.info("All assertions and citations maintain an unbroken provenance DAG.")

        # 4. Save to Database & JSON Snapshot
        self.db.save_findings(findings)

        with open(self.findings_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps([f.model_dump() for f in findings], indent=2) + "\n"
            )

        report = SynthesisReport(
            report_id="SYN-REPORT-01",
            findings=findings,
            total_evidence_analyzed=len(evidence),
            total_clusters_analyzed=len(clusters),
            provenance_audit_passed=audit_result.is_valid,
            total_citations=audit_result.total_citations_audited,
        )

        summary = {
            "status": "SUCCESS" if audit_result.is_valid else "PARTIAL",
            "findings_count": len(findings),
            "citations_count": audit_result.total_citations_audited,
            "provenance_audit_passed": audit_result.is_valid,
            "audit_errors": audit_result.errors,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "citations_count": len(f.citations),
                    "has_contradictory": f.contradictory_evidence is not None,
                    "confidence": f.confidence_score,
                }
                for f in findings
            ],
        }

        logger.info("==================================================")
        logger.info(f"PHASE 4 COMPLETE: Synthesized {len(findings)} findings.")
        for f in findings:
            logger.info(
                f"  - [{f.finding_id}] {f.title} ({len(f.citations)} citations, conf={f.confidence_score})"
            )
        logger.info("==================================================")

        return summary


if __name__ == "__main__":
    pipeline = SynthesisPipeline()
    pipeline.run()
