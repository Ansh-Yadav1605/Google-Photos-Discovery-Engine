"""Emergent clustering engine utilizing multi-attribute representations and scikit-learn."""

from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
from src.config.logger import logger
from src.models.schema import NormalizedEvidenceRecord
from src.models.clustering import ProblemCluster

ALL_FAILURE_STAGES = [
    "MEMORY_RECALL",
    "QUERY_FORMULATION",
    "SYSTEM_UNDERSTANDING",
    "RETRIEVAL_RELEVANCE",
    "RESULT_EVALUATION",
    "SEARCH_REFINEMENT",
    "NAVIGATION_OR_DISCOVERABILITY",
    "METADATA_OR_INDEXING",
    "CONTENT_NOT_PRESENT_OR_UNAVAILABLE",
    "OTHER",
]

TOP_MEMORY_CUES = [
    "PERSON_OR_FACE",
    "SPATIAL_OR_LOCATION",
    "TEMPORAL_APPROXIMATE",
    "VISUAL_APPEARANCE",
    "OBJECT_OR_LANDMARK",
    "ACTIVITY_OR_OCCASION",
    "EMOTIONAL_OR_CONTEXTUAL",
    "VISIBLE_TEXT",
    "SOURCE_APP_OR_DEVICE",
    "ALBUM_OR_CONTAINER",
]


class EmergentClusterer:
    """Discovers emergent retrieval problem clusters from normalized evidence."""

    def __init__(self, min_cluster_size: int = 2):
        self.min_cluster_size = min_cluster_size
        self.vectorizer = TfidfVectorizer(
            stop_words="english", max_features=40, lowercase=True
        )

    def extract_features(
        self, records: List[NormalizedEvidenceRecord]
    ) -> np.ndarray:
        """Construct joint feature matrix combining text TF-IDF and categorical vectors."""
        text_corpus = []
        for r in records:
            scenario = r.retrieval_scenario or ""
            goal = r.user_goal or ""
            text = f"{scenario} {goal} {r.raw_text}"
            text_corpus.append(text)

        # 1. Text TF-IDF features
        try:
            tfidf_mat = self.vectorizer.fit_transform(text_corpus).toarray()
        except ValueError:
            # Fallback if vocabulary is empty
            tfidf_mat = np.zeros((len(records), 5))

        # 2. Multi-hot failure stages (weight: 1.5 to emphasize failure mechanisms)
        stage_mat = np.zeros((len(records), len(ALL_FAILURE_STAGES)))
        for i, r in enumerate(records):
            for stage in r.failure_stage:
                if stage in ALL_FAILURE_STAGES:
                    idx = ALL_FAILURE_STAGES.index(stage)
                    stage_mat[i, idx] = 1.5

        # 3. Multi-hot memory cues (weight: 1.0)
        cue_mat = np.zeros((len(records), len(TOP_MEMORY_CUES)))
        for i, r in enumerate(records):
            for cue in r.memory_cues:
                if cue in TOP_MEMORY_CUES:
                    idx = TOP_MEMORY_CUES.index(cue)
                    cue_mat[i, idx] = 1.0

        # Combine into joint feature space
        features = np.hstack([tfidf_mat, stage_mat, cue_mat])
        return features

    def fit_predict(
        self, records: List[NormalizedEvidenceRecord]
    ) -> List[int]:
        """Cluster records into emergent labels. Falls back gracefully on small samples."""
        n_samples = len(records)
        if n_samples < 2:
            return [0] * n_samples

        features = self.extract_features(records)

        # 1. Attempt HDBSCAN clustering
        try:
            clusterer = HDBSCAN(
                min_cluster_size=min(self.min_cluster_size, n_samples),
                min_samples=1,
                metric="euclidean",
                copy=True,
            )
            labels = clusterer.fit_predict(features)

            # If all labeled as noise (-1) or single cluster with noise, fallback to Agglomerative
            unique_labels = set(labels) - {-1}
            if len(unique_labels) >= 2:
                # Merge noise points to nearest cluster if possible
                labels = self._assign_noise_points(features, labels)
                return labels.tolist()

        except Exception as e:
            logger.warning(
                f"HDBSCAN clustering did not converge, falling back to Agglomerative: {e}"
            )

        # 2. Fallback: Hierarchical Agglomerative Clustering
        n_clusters = max(2, min(5, n_samples // 2))
        agg = AgglomerativeClustering(
            n_clusters=n_clusters, metric="euclidean", linkage="ward"
        )
        labels = agg.fit_predict(features)
        return labels.tolist()

    def _assign_noise_points(
        self, features: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        """Assign noise points (-1) to the closest cluster centroid."""
        clean_labels = labels.copy()
        non_noise = [lbl for lbl in set(labels) if lbl != -1]
        if not non_noise:
            return np.zeros_like(labels)

        centroids = {}
        for lbl in non_noise:
            centroids[lbl] = features[labels == lbl].mean(axis=0)

        for i, lbl in enumerate(labels):
            if lbl == -1:
                # Find closest centroid
                dists = {
                    c_lbl: np.linalg.norm(features[i] - c_vec)
                    for c_lbl, c_vec in centroids.items()
                }
                clean_labels[i] = min(dists, key=dists.get)

        return clean_labels

    def generate_clusters(
        self, records: List[NormalizedEvidenceRecord]
    ) -> List[ProblemCluster]:
        """Cluster evidence records and generate narrative descriptors for each cluster."""
        relevant_records = [
            r for r in records if r.retrieval_relevance is True
        ]
        if not relevant_records:
            logger.warning("No relevant records provided for clustering.")
            return []

        labels = self.fit_predict(relevant_records)

        # Group records by cluster label
        clusters_map: Dict[int, List[NormalizedEvidenceRecord]] = {}
        for label, record in zip(labels, relevant_records):
            clusters_map.setdefault(label, []).append(record)

        problem_clusters: List[ProblemCluster] = []

        for idx, (label, cluster_recs) in enumerate(
            sorted(clusters_map.items(), key=lambda x: len(x[1]), reverse=True)
        ):
            cluster_id = f"CLUST-{idx + 1:02d}"
            cluster = self._build_cluster_descriptor(cluster_id, cluster_recs)
            problem_clusters.append(cluster)

        return problem_clusters

    def _build_cluster_descriptor(
        self, cluster_id: str, records: List[NormalizedEvidenceRecord]
    ) -> ProblemCluster:
        """Synthesize rich metadata and narrative descriptors for a cluster."""
        ev_ids = [r.id for r in records]
        sources = [r.source for r in records]
        source_counts = dict(Counter(sources))

        # Count failure stages
        stages = []
        for r in records:
            stages.extend(r.failure_stage)
        stage_counts = dict(Counter(stages))
        top_stages = [
            s[0] for s in Counter(stages).most_common(2) if s[0] != "OTHER"
        ]

        # Count retrieval objects
        objects = [r.retrieval_object for r in records if r.retrieval_object]
        top_objects = [
            o[0] for o in Counter(objects).most_common(2) if o[0] != "UNKNOWN"
        ]

        # Count memory cues and workarounds
        cues = [c for r in records for c in r.memory_cues]
        top_cues = [c[0] for c in Counter(cues).most_common(2)]

        workarounds = [w for r in records for w in r.workaround]
        common_workarounds = [w[0] for w in Counter(workarounds).most_common(3)]

        behaviors = [b for r in records for b in r.search_behavior]
        recurring_behaviors = [b[0] for b in Counter(behaviors).most_common(3)]

        avg_conf = (
            float(np.mean([r.confidence for r in records])) if records else 0.0
        )

        # Select up to 3 representative evidence IDs (prioritizing high confidence)
        sorted_recs = sorted(records, key=lambda x: x.confidence, reverse=True)
        rep_ids = [r.id for r in sorted_recs[:3]]

        # Generate emergent narrative title & description
        name, description, open_questions = self._synthesize_cluster_narrative(
            top_stages=top_stages,
            top_objects=top_objects,
            top_cues=top_cues,
            sample_recs=records,
        )

        return ProblemCluster(
            cluster_id=cluster_id,
            name=name,
            description=description,
            evidence_count=len(records),
            evidence_ids=ev_ids,
            source_diversity=len(source_counts),
            source_distribution=source_counts,
            affected_failure_stages=stage_counts,
            dominant_retrieval_objects=top_objects,
            recurring_behaviors=recurring_behaviors,
            common_workarounds=common_workarounds,
            confidence=round(avg_conf, 2),
            representative_evidence_ids=rep_ids,
            unresolved_questions=open_questions,
        )

    def _synthesize_cluster_narrative(
        self,
        top_stages: List[str],
        top_objects: List[str],
        top_cues: List[str],
        sample_recs: List[NormalizedEvidenceRecord],
    ) -> Tuple[str, str, List[str]]:
        """Formulate an emergent descriptive title, mechanism explanation, and open questions."""
        primary_stage = top_stages[0] if top_stages else "RETRIEVAL_RELEVANCE"
        primary_obj = top_objects[0] if top_objects else "Visual Memories"
        primary_cue = top_cues[0] if top_cues else "Partial Context"

        # Format clean human readable strings
        obj_clean = primary_obj.replace("_", " ").title()
        stage_clean = primary_stage.replace("_", " ").title()
        cue_clean = primary_cue.replace("_", " ").title()

        name = f"{stage_clean} Friction in Retrieving {obj_clean}"
        description = (
            f"Users attempting to locate {obj_clean.lower()} rely heavily on {cue_clean.lower()} "
            f"cues, but experience breakdown at the {stage_clean.lower()} stage. "
            f"The system struggles to map fragmentary user memory anchors onto indexed metadata, "
            f"resulting in search friction or retrieval abandonment."
        )

        open_questions = [
            f"How frequently do users abandon {obj_clean.lower()} retrieval vs resorting to external chat apps?",
            f"What refinement controls could bridge the gap when {stage_clean.lower()} fails on initial query?",
            f"Are existing metadata tags sufficient to resolve {cue_clean.lower()} without manual timeline scrubbing?",
        ]

        return name, description, open_questions
