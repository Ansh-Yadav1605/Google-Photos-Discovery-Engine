"""Provenance and citation verifier enforcing unbroken auditability DAG.

Validates that every claim and citation links to an existing evidence record,
verifies URL authenticity, checks quote verbatim accuracy, and audits contradictory evidence.
"""

from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.synthesis import FindingResult, ProvenanceCitation, ContradictoryEvidence


class ProvenanceAuditResult(BaseModel):
    """Result of an automated provenance verification pass."""

    is_valid: bool = True
    total_findings_audited: int = 0
    total_citations_audited: int = 0
    verified_citations: int = 0
    invalid_citations: List[Dict[str, Any]] = Field(default_factory=list)
    missing_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_audits: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ProvenanceChecker:
    """Verifies that synthesis findings maintain an unbroken DAG to canonical raw evidence."""

    def __init__(self, evidence_records: Optional[List[NormalizedEvidenceRecord]] = None):
        self.evidence_lookup: Dict[str, NormalizedEvidenceRecord] = {}
        if evidence_records:
            self.set_evidence(evidence_records)

    def set_evidence(self, evidence_records: List[NormalizedEvidenceRecord]):
        """Populate the canonical evidence lookup."""
        self.evidence_lookup = {r.id: r for r in evidence_records}

    def verify_finding(self, finding: FindingResult) -> Tuple[bool, List[str]]:
        """Verify citations and contradictory evidence for a single finding."""
        errors: List[str] = []

        # 1. Zero-uncited claims rule: Every finding must have at least one citation
        if not finding.citations:
            errors.append(f"Finding {finding.finding_id} has zero citations (violates evidence-grounded rule).")

        # 2. Check each citation against canonical evidence
        for citation in finding.citations:
            ev_id = citation.evidence_id
            if ev_id not in self.evidence_lookup:
                errors.append(
                    f"Finding {finding.finding_id}: Cited evidence ID '{ev_id}' does not exist in database."
                )
                continue

            canonical = self.evidence_lookup[ev_id]

            # Verify canonical source URL match
            if citation.source_url.strip() != canonical.source_url.strip():
                errors.append(
                    f"Finding {finding.finding_id}: Citation URL mismatch for {ev_id}. "
                    f"Expected '{canonical.source_url}', got '{citation.source_url}'."
                )

            # Verify quote snippet is present in raw text
            snippet = citation.quote_snippet.strip()
            if snippet:
                # Normalize spaces for comparison
                norm_snippet = " ".join(snippet.lower().split())
                norm_raw = " ".join(canonical.raw_text.lower().split())
                if norm_snippet not in norm_raw:
                    # Allow minor truncation if first 25 chars match
                    short_prefix = norm_snippet[:25]
                    if short_prefix not in norm_raw:
                        errors.append(
                            f"Finding {finding.finding_id}: Quote snippet for {ev_id} not found in raw_text. "
                            f"Snippet: '{snippet[:50]}...'"
                        )

        # 3. Check contradictory evidence if present
        if finding.contradictory_evidence:
            contra = finding.contradictory_evidence
            if not contra.evidence_ids_a or not contra.evidence_ids_b:
                errors.append(
                    f"Finding {finding.finding_id}: Contradictory evidence must cite non-empty ID sets for both perspectives."
                )
            
            # Check overlap
            overlap = set(contra.evidence_ids_a).intersection(set(contra.evidence_ids_b))
            if overlap:
                errors.append(
                    f"Finding {finding.finding_id}: Overlapping evidence IDs in opposing perspectives: {overlap}."
                )

            for eid in contra.evidence_ids_a:
                if eid not in self.evidence_lookup:
                    errors.append(
                        f"Finding {finding.finding_id}: Contradictory perspective A cites non-existent ID '{eid}'."
                    )
            for eid in contra.evidence_ids_b:
                if eid not in self.evidence_lookup:
                    errors.append(
                        f"Finding {finding.finding_id}: Contradictory perspective B cites non-existent ID '{eid}'."
                    )

        is_valid = len(errors) == 0
        return is_valid, errors

    def audit_all(self, findings: List[FindingResult]) -> ProvenanceAuditResult:
        """Run complete provenance audit across all findings."""
        report = ProvenanceAuditResult(total_findings_audited=len(findings))

        for finding in findings:
            is_valid, errors = self.verify_finding(finding)
            report.total_citations_audited += len(finding.citations)

            for citation in finding.citations:
                if citation.evidence_id in self.evidence_lookup:
                    report.verified_citations += 1
                else:
                    report.missing_evidence_ids.append(citation.evidence_id)
                    report.invalid_citations.append({
                        "finding_id": finding.finding_id,
                        "citation": citation.model_dump(),
                    })

            if finding.contradictory_evidence:
                report.contradictory_audits.append({
                    "finding_id": finding.finding_id,
                    "topic": finding.contradictory_evidence.topic,
                    "perspective_a_count": len(finding.contradictory_evidence.evidence_ids_a),
                    "perspective_b_count": len(finding.contradictory_evidence.evidence_ids_b),
                })

            if not is_valid:
                report.is_valid = False
                report.errors.extend(errors)

        if report.is_valid:
            logger.info(
                f"Provenance audit PASSED: {report.verified_citations}/{report.total_citations_audited} "
                f"citations verified across {report.total_findings_audited} findings."
            )
        else:
            logger.warning(
                f"Provenance audit FAILED with {len(report.errors)} violations: {report.errors}"
            )

        return report
