"""Multidimensional Opportunity Matrix evaluator.

Enforces strict PM research rules:
- No single arbitrary composite 'winner' score.
- Exposes 7 transparent evidence dimensions independently for product discovery comparison.
"""

from typing import List, Dict, Optional
import numpy as np
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster, OpportunityArea

TOTAL_KNOWN_PLATFORMS = 5  # Reddit, Google Play, App Store, Community, Forums/Manual


class OpportunityMatrixCalculator:
    """Calculates multidimensional comparative evidence vectors for problem clusters."""

    def evaluate_cluster(
        self,
        cluster: ProblemCluster,
        evidence_records: List[NormalizedEvidenceRecord],
    ) -> OpportunityArea:
        """Calculate the 7 transparent evidence dimensions for a given cluster."""
        cluster_recs = [
            r for r in evidence_records if r.id in cluster.evidence_ids
        ]
        n_records = len(cluster_recs)

        # 1. Evidence Volume
        volume = n_records

        # 2. Source Diversity
        unique_sources = len(cluster.source_distribution)
        diversity_ratio = round(
            min(1.0, unique_sources / TOTAL_KNOWN_PLATFORMS), 2
        )

        # 3. Recurrence Rate (Unique authors over total records)
        authors = [r.author for r in cluster_recs if r.author]
        unique_authors = len(set(authors))
        recurrence = (
            round(unique_authors / n_records, 2) if n_records > 0 else 0.0
        )

        # 4. Severity Assessment (Qualitative + Factual Rationale)
        severity, severity_rationale = self._assess_severity(cluster_recs)

        # 5. Retrieval Impact (Proportion ending in FAILED_RETRIEVAL or ABANDONED)
        severe_outcomes = [
            r
            for r in cluster_recs
            if r.outcome in ["FAILED_RETRIEVAL", "ABANDONED"]
        ]
        impact_rate = (
            round(len(severe_outcomes) / n_records, 2)
            if n_records > 0
            else 0.0
        )

        # 6. Workaround Inefficiency
        workaround_level, workaround_details = self._assess_workarounds(
            cluster_recs
        )

        # 7. Evidence Confidence
        conf_scores = [r.confidence for r in cluster_recs if r.confidence]
        avg_confidence = (
            round(float(np.mean(conf_scores)), 2) if conf_scores else 0.0
        )

        # Temporal Span
        published_dates = [
            r.published_at for r in cluster_recs if r.published_at
        ]
        temporal_span = None
        if published_dates:
            temporal_span = {
                "earliest": min(published_dates),
                "latest": max(published_dates),
            }

        opp_id = f"OPP-{cluster.cluster_id.replace('CLUST-', '')}"

        return OpportunityArea(
            opportunity_id=opp_id,
            cluster_id=cluster.cluster_id,
            cluster_name=cluster.name,
            evidence_volume=volume,
            source_diversity_count=unique_sources,
            source_diversity_ratio=diversity_ratio,
            recurrence_rate=recurrence,
            severity_assessment=severity,
            severity_rationale=severity_rationale,
            retrieval_impact_rate=impact_rate,
            workaround_inefficiency=workaround_level,
            workaround_details=workaround_details,
            evidence_confidence=avg_confidence,
            platform_breakdown=cluster.source_distribution,
            temporal_span=temporal_span,
            unresolved_risks=[
                "Requires validation through primary user interviews in Part 2",
                "Assumes public review complaints correlate with mobile session abandonment",
            ],
        )

    def evaluate_all(
        self,
        clusters: List[ProblemCluster],
        evidence_records: List[NormalizedEvidenceRecord],
    ) -> List[OpportunityArea]:
        """Evaluate all clusters into comparable opportunity areas."""
        opportunities = []
        for cluster in clusters:
            opp = self.evaluate_cluster(cluster, evidence_records)
            opportunities.append(opp)
        return opportunities

    def _assess_severity(
        self, records: List[NormalizedEvidenceRecord]
    ) -> (str, str):
        """Evaluate severity based on target object stakes and user sentiment."""
        high_stakes_objects = {
            "HEALTH_OR_MEDICAL",
            "UTILITY_DOCUMENT",
            "SCREENSHOT",
        }
        emotional_objects = {"EVENT_OR_TRIP", "GROUP_PHOTO"}

        objects = [r.retrieval_object for r in records if r.retrieval_object]
        has_high_stakes = any(obj in high_stakes_objects for obj in objects)
        has_emotional = any(obj in emotional_objects for obj in objects)

        # Count low star ratings if app reviews
        low_ratings = [
            r.rating
            for r in records
            if r.rating is not None and r.rating in [1.0, 2.0]
        ]

        if has_high_stakes:
            return (
                "HIGH",
                "High utility loss: Involves critical transaction documents, prescriptions, or receipts required for urgent verification.",
            )
        elif has_emotional and len(low_ratings) >= 2:
            return (
                "HIGH",
                "High emotional stakes: Irreplaceable milestone or family gathering memories inaccessible to the user.",
            )
        elif has_emotional:
            return (
                "MODERATE",
                "Moderate emotional friction: Discretionary personal or travel memories with significant user effort spent browsing.",
            )
        else:
            return (
                "LOW",
                "Low to moderate friction: General catalog retrieval or casual snapshot discovery.",
            )

    def _assess_workarounds(
        self, records: List[NormalizedEvidenceRecord]
    ) -> (str, List[str]):
        """Evaluate the friction and inefficiency of user workarounds."""
        workarounds = [w for r in records for w in r.workaround if w]
        details = list(set(workarounds))

        if any(
            w in ["EXTERNAL_APP_SEARCH", "PEOPLE_COLLABORATION"]
            for w in workarounds
        ):
            return (
                "HIGH",
                details
                or [
                    "Users forced to rely on external platforms (WhatsApp/messages) or ask other people"
                ],
            )
        elif any(
            w in ["ENDLESS_MANUAL_SCROLL", "THIRD_PARTY_GALLERY"]
            for w in workarounds
        ):
            return (
                "MODERATE",
                details
                or [
                    "Users resort to exhausting 15-45 minute manual timeline scrubbing or third-party gallery apps"
                ],
            )
        elif "TOTAL_ABANDONMENT" in workarounds:
            return (
                "HIGH",
                details
                or [
                    "Users resign to permanent retrieval abandonment after search failure"
                ],
            )
        else:
            return (
                "LOW",
                details
                or ["Minor query adjustment or immediate alternative browse"],
            )
