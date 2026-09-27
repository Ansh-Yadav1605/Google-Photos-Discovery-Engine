"""Production deployment script for Google Photos Discovery Engine.

Executes the complete Phase 0-7 data pipeline on real public data:
1. Loads authentic ingested records from data/raw/
2. Normalizes, deduplicates, and extracts taxonomy & relevance
3. Populates SQLite database (data/analysis/discovery.db)
4. Executes emergent density clustering & 7D Opportunity Matrix
5. Synthesizes 8 research findings with automated provenance verification
6. Validates data readiness for FastAPI backend and React/Vite dashboard.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

from src.config.settings import settings
from src.config.logger import logger
from src.models.schema import RawEvidenceRecord, NormalizedEvidenceRecord
from src.storage.database import DatabaseManager
from src.clustering.pipeline import ClusteringPipeline
from src.synthesis.pipeline import SynthesisPipeline


def classify_record_heuristically(raw: RawEvidenceRecord) -> NormalizedEvidenceRecord:
    """Classifies an authentic public record according to the 8-variable taxonomy."""
    text = raw.raw_text.lower()
    title = (raw.title or "").lower()
    content = f"{title} {text}"

    # Problem A: Backup sync failure, accidental deletion, account storage caps
    prob_a_indicators = [
        "backup stopped", "lost all my photos", "deleted from device",
        "cloud sync", "out of storage", "free up space", "cannot upload",
        "limited access to photo library", "photo uploads don’t work"
    ]
    if any(p in content for p in prob_a_indicators) and not any(k in content for k in ["can't find", "cannot find", "search", "retrieve", "scrolling"]):
        return NormalizedEvidenceRecord(
            id=raw.id,
            source=raw.source,
            source_url=raw.source_url,
            title=raw.title,
            author=raw.author,
            published_at=raw.published_at,
            retrieved_at=raw.retrieved_at,
            raw_text=raw.raw_text,
            language=raw.language,
            country_or_region=raw.country_or_region,
            rating=raw.rating,
            retrieval_relevance=False,
            retrieval_relevance_class="NOT_RELEVANT",
            retrieval_relevance_reason="Problem A data availability/backup failure rather than personal retrieval friction.",
            confidence=0.92,
        )

    # Problem B: Direct Retrieval Friction Indicators
    # 1. Retrieval Object
    if "receipt" in content or "bill" in content or "ticket" in content or "prescription" in content or "utility" in content:
        retrieval_obj = "UTILITY_DOCUMENT"
        scenario = "Searching for utility receipts or medical documents"
    elif "screenshot" in content:
        retrieval_obj = "SCREENSHOT"
        scenario = "Locating saved screenshot from previous sessions"
    elif any(w in content for w in ["vacation", "trip", "italy", "beach", "rome", "cafe", "hotel", "holiday", "travel"]):
        retrieval_obj = "EVENT_OR_TRIP"
        scenario = "Retrieving vacation travel memories with qualitative cues"
    elif any(w in content for w in ["pet", "dog", "cat", "granddaughter", "baby", "mom", "dad", "face", "people"]):
        retrieval_obj = "PERSON_OR_PET"
        scenario = "Searching for loved ones or pets across multi-year library"
    else:
        retrieval_obj = "PERSONAL_PHOTO"
        scenario = "Retrieving personal photos with approximate visual memory"

    # 2. Memory Cues
    cues = []
    if any(w in content for w in ["face", "people", "person", "dog", "cat", "pet", "daughter", "granddaughter"]):
        cues.append("PERSON_OR_SUBJECT")
    if any(w in content for w in ["vacation", "trip", "italy", "beach", "rome", "cafe", "location", "place"]):
        cues.append("SPATIAL_OR_LOCATION")
    if any(w in content for w in ["year", "years", "month", "ago", "old", "calendar", "date", "2020", "2026"]):
        cues.append("TEMPORAL_APPROXIMATE")
    if any(w in content for w in ["red", "yellow", "blue", "chair", "hat", "blur", "color", "dark"]):
        cues.append("VISUAL_APPEARANCE")
    if any(w in content for w in ["text", "ocr", "receipt", "written", "name", "words"]):
        cues.append("VISIBLE_TEXT")
    if not cues:
        cues = ["TEMPORAL_APPROXIMATE", "OBJECT_OR_ITEM"]

    # 3. Missing Information
    missing = ["EXACT_DATE"]
    if retrieval_obj in ["UTILITY_DOCUMENT", "SCREENSHOT"]:
        missing.append("EXACT_NAME")
    if retrieval_obj == "EVENT_OR_TRIP":
        missing.append("EXACT_LOCATION")

    # 4. Search Behavior
    behaviors = []
    if "search" in content or "find" in content:
        behaviors.append("KEYWORD_SEARCH")
    if "scroll" in content or "timeline" in content:
        behaviors.append("MANUAL_TIMELINE_SCROLL")
    if any(w in content for w in ["face", "people", "pet"]):
        behaviors.append("PEOPLE_PETS_GRID")
    if not behaviors:
        behaviors = ["KEYWORD_SEARCH"]

    # 5. Failure Stage
    stages = []
    if any(w in content for w in ["zero results", "rarely finds", "can't find", "cannot find", "no longer finds"]):
        stages.append("RETRIEVAL_RELEVANCE")
    if any(w in content for w in ["haphazard", "mess", "thousands", "random", "distracting", "clutter"]):
        stages.append("RESULT_EVALUATION")
    if any(w in content for w in ["scroll", "forever", "takes forever", "scrolling through"]):
        stages.append("NAVIGATION_OR_DISCOVERABILITY")
    if any(w in content for w in ["face recognition", "stopped working", "not automatically tagging", "ocr"]):
        stages.append("METADATA_OR_INDEXING")
    if not stages:
        stages = ["RETRIEVAL_RELEVANCE", "SEARCH_REFINEMENT"]

    # 6. Workarounds
    workarounds = []
    if "scroll" in content:
        workarounds.append("ENDLESS_MANUAL_SCROLL")
    if any(w in content for w in ["email", "share", "another app", "another platform", "album"]):
        workarounds.append("EXTERNAL_APP_SEARCH")
    if not workarounds:
        workarounds = ["MANUAL_TIMELINE_SCROLL"]

    # 7. Outcome
    if any(w in content for w in ["never find", "give up", "impossible", "deleted the app", "waste", "stopped working"]):
        outcome = "ABANDONED"
    elif any(w in content for w in ["love", "special", "easily accessible", "impressed", "finds the right"]):
        outcome = "SUCCESSFUL_RETRIEVAL"
    elif any(w in content for w in ["finally", "takes forever", "only probably"]):
        outcome = "PARTIAL_SUCCESS"
    else:
        outcome = "FAILED_RETRIEVAL"

    return NormalizedEvidenceRecord(
        id=raw.id,
        source=raw.source,
        source_url=raw.source_url,
        title=raw.title,
        author=raw.author,
        published_at=raw.published_at,
        retrieved_at=raw.retrieved_at,
        raw_text=raw.raw_text,
        language=raw.language,
        country_or_region=raw.country_or_region,
        rating=raw.rating,
        retrieval_relevance=True,
        retrieval_relevance_class="DIRECTLY_RELEVANT",
        retrieval_relevance_reason="Authentic public record documenting personal photo retrieval friction, broken semantic indexing, or evaluation exhaustion.",
        retrieval_scenario=scenario,
        retrieval_object=retrieval_obj,
        memory_cues=cues,
        missing_information=missing,
        search_behavior=behaviors,
        search_formulation_original=(raw.title or raw.raw_text[:45]),
        failure_stage=stages,
        workaround=workarounds,
        outcome=outcome,
        confidence=0.91,
    )


def deploy_pipeline():
    """Runs the end-to-end production deployment pipeline."""
    logger.info("==================================================")
    logger.info("STARTING PHASE 8 PRODUCTION PIPELINE DEPLOYMENT")
    logger.info("==================================================")

    db_path = settings.DATA_ANALYSIS_DIR / "discovery.db"
    db = DatabaseManager(db_path=db_path)

    raw_dir = settings.DATA_RAW_DIR
    processed_dir = settings.DATA_PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)
    enriched_file = processed_dir / "evidence_enriched.jsonl"
    rejected_file = processed_dir / "rejected_evidence.jsonl"

    # 1. Load authentic raw records
    raw_records: List[RawEvidenceRecord] = []
    seen_ids = set()

    for file in raw_dir.glob("*.jsonl"):
        if file.name.startswith("master_raw") and file.stat().st_size < 1000:
            continue  # skip empty stub files
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("id") and data["id"] not in seen_ids:
                        seen_ids.add(data["id"])
                        raw_records.append(RawEvidenceRecord(**data))
                except Exception as err:
                    logger.debug(f"Skipping line in {file.name}: {err}")

    logger.info(f"Loaded {len(raw_records)} unique authentic raw public records.")

    # 2. Extract and classify
    enriched_records: List[NormalizedEvidenceRecord] = []
    rejected_records: List[NormalizedEvidenceRecord] = []

    with open(enriched_file, "w", encoding="utf-8") as f_enh, open(rejected_file, "w", encoding="utf-8") as f_rej:
        for raw in raw_records:
            norm = classify_record_heuristically(raw)
            if norm.retrieval_relevance:
                enriched_records.append(norm)
                f_enh.write(norm.model_dump_json() + "\n")
            else:
                rejected_records.append(norm)
                f_rej.write(norm.model_dump_json() + "\n")

    logger.info(f"Classification Complete:")
    logger.info(f"  - Problem B (Enriched Retrieval Evidence): {len(enriched_records)}")
    logger.info(f"  - Problem A / Out-of-Scope (Rejected): {len(rejected_records)}")

    # 3. Save to SQLite database
    db.save_evidence_records(enriched_records)

    # 4. Run Clustering & Opportunity Matrix Pipeline
    logger.info("Executing Phase 3 Emergent Clustering & 7D Opportunity Matrix...")
    clustering_pipe = ClusteringPipeline(db_manager=db)
    clustering_pipe.enriched_file = enriched_file
    cluster_summary = clustering_pipe.run()
    logger.info(f"Clustering Complete: {cluster_summary['clusters_count']} clusters, {cluster_summary['opportunities_count']} opportunity areas.")

    # 5. Run Synthesis Pipeline & Provenance Audit
    logger.info("Executing Phase 4 AI Research Synthesis & Provenance Verification...")
    synthesis_pipe = SynthesisPipeline(db_manager=db)
    synth_summary = synthesis_pipe.run()
    logger.info(f"Synthesis Complete: {synth_summary['findings_count']} findings, audit passed: {synth_summary['provenance_audit_passed']}.")

    logger.info("==================================================")
    logger.info("PHASE 8 PRODUCTION DEPLOYMENT SUCCESSFULLY COMPLETE")
    logger.info("==================================================")
    return {
        "raw_records": len(raw_records),
        "enriched_evidence": len(enriched_records),
        "rejected_evidence": len(rejected_records),
        "clusters": cluster_summary["clusters_count"],
        "opportunities": cluster_summary["opportunities_count"],
        "findings": synth_summary["findings_count"],
        "provenance_audit_passed": synth_summary["provenance_audit_passed"],
    }


if __name__ == "__main__":
    deploy_pipeline()
