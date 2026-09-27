# Google Photos Discovery Engine — Context & Research Scope

## 1. Product Context
- **Product**: Google Photos
- **Team**: Core Experience
- **Lifecycle & Scale**: Google Photos manages billions of personal and shared visual assets globally across Android, iOS, and Web. While automated backup, facial grouping, and semantic search (including Gemini-powered Ask Photos rollouts) exist, retrieval failures persist for long-tail, unindexed, or vaguely remembered personal photos.

## 2. Business Goal
Increase the percentage of users who successfully retrieve a photo they remember but cannot precisely describe when they start searching.

## 3. Part 1 Objective
Build a functional, evidence-driven, AI-powered Discovery Engine that collects and analyzes authentic public user conversations regarding photo retrieval. The system extracts structured behavioral dimensions, isolates retrieval failure points, clusters emergent problem themes, and establishes an empirical foundation for prioritization in Parts 2–8 of the graduation project.

---

## 4. Research Questions
The primary research question is:
> **Why do users fail to retrieve old visual memories when they remember the photo but cannot precisely describe it?**

This breaks down into 11 investigative sub-questions:
- **A. Memory Types**: What types of photos, videos, or visual memories are hardest to retrieve (e.g., casual snapshots, screenshots, utility docs, group photos, travel moments)?
- **B. Retained Cues**: What information does the user actually remember (e.g., color, rough season, vague companion, emotional context, object fragment)?
- **C. Forgotten Attributes**: What information has the user forgotten (e.g., exact date, location name, specific filename, exact text)?
- **D. Search Clues**: What clues does the user naturally attempt to query or navigate with first?
- **E. Search Formulation**: How does the user phrase their memory (natural language, disconnected keywords, date approximations)?
- **F. Secondary Iterations**: What does the user attempt when the initial search fails (e.g., altering keywords, manual timeline scrubbing, checking Trash/Archive)?
- **G. Google Photos Capabilities Used**: Which existing features are leveraged (Search bar, People & Pets, Places, Documents, Explore tab, Search filters)?
- **H. Journey Breakdown Point**: Exactly where does the retrieval journey fail (e.g., recall, query formulation, indexing mismatch, relevance noise, lack of refinement controls)?
- **I. User Workarounds**: What compensatory mechanisms do users employ (e.g., messaging a friend for the photo, searching external chat apps, giving up)?
- **J. Recurrence**: Which retrieval failures recur consistently across independent users?
- **K. Opportunity Areas**: Which recurring problem clusters represent high-leverage opportunities for Google Photos Core Experience?

---

## 5. Public Data Sources
To ensure source diversity and avoid platform-specific bias, the discovery engine integrates:
1. **Google Play Store Reviews**: Google Photos Android app reviews focusing on search, finding photos, and retrieval issues.
2. **Apple App Store Reviews**: iOS Google Photos user reviews addressing retrieval, search sync, and album discoverability.
3. **Reddit Discussions**: Subreddits such as `r/googlephotos`, `r/google`, `r/Android`, and `r/techsupport`.
4. **Google Photos Help Community / Support Forums**: Authentic public support threads detailing multi-step search failures.
5. **Public Tech Forums & YouTube Tech Discussions**: Accessible discussions, comments, and tech community threads discussing photo discovery and search limitations.
6. **Manual / CSV Import**: Clear importer for audited external public forum posts where automated scraping is restricted.

---

## 6. Evidence Schema & Normalization
Every collected evidence record is normalized into a strict, reproducible schema:

```json
{
  "id": "string (UUID / Source-hash)",
  "source": "Google Play | App Store | Reddit | Google Photos Community | YouTube | Forum | Other",
  "source_url": "string (canonical URL)",
  "title": "string | null",
  "author": "string | null (publicly displayed handle or anonymized)",
  "published_at": "ISO-8601 string | null",
  "retrieved_at": "ISO-8601 string",
  "raw_text": "string (original text)",
  "language": "string (ISO code, e.g., 'en')",
  "country_or_region": "string | null",
  "rating": "number | null (1-5 for app store reviews)",
  "retrieval_relevance": "boolean",
  "retrieval_relevance_reason": "string",
  "retrieval_scenario": "string | null",
  "memory_cues": ["string"],
  "missing_information": ["string"],
  "search_behavior": ["string"],
  "failure_stage": ["string"],
  "workaround": ["string"],
  "user_goal": "string | null",
  "evidence_type": "USER_STATEMENT | OBSERVED_BEHAVIOR",
  "confidence": "float (0.0 to 1.0)"
}
```

---

## 7. Extraction Taxonomy
Extracted attributes strictly map to predefined analytical dimensions:
- **Retrieval Object**: Personal photo, group photo, event/milestone, travel, screenshot, utility document/receipt, medicine/prescription, video, collage/Memory, unknown.
- **Memory Cues**: Person/face, spatial/place, temporal/approximate time, visual feature/color, object/landmark, activity, emotional context, text visible in photo, source app/device.
- **Forgotten Information**: Exact date, exact location, proper name, exact transcribed text, album/folder name, exact filename.
- **Search Behavior**: Keyword search, natural language sentence, people filter, location filter, date filter, manual timeline scrubbing, folder browsing, archive/trash check, repeated keyword swapping, abandonment.
- **Search Formulation**: Preserves `original_query` exactly as reported by the user, alongside `normalized_query`.
- **Failure Stages**: 
  1. `MEMORY_RECALL`
  2. `QUERY_FORMULATION`
  3. `SYSTEM_UNDERSTANDING`
  4. `RETRIEVAL_RELEVANCE`
  5. `RESULT_EVALUATION`
  6. `SEARCH_REFINEMENT`
  7. `NAVIGATION_OR_DISCOVERABILITY`
  8. `METADATA_OR_INDEXING`
  9. `CONTENT_NOT_PRESENT_OR_UNAVAILABLE`
  10. `OTHER`
- **Workarounds**: External messaging search (WhatsApp/iMessage), asking a friend, scrolling endlessly, external gallery apps, abandoning the search.
- **Outcome**: `SUCCESSFUL_RETRIEVAL`, `PARTIAL_SUCCESS`, `FAILED_RETRIEVAL`, `ABANDONED`, `UNCLEAR`.

---

## 8. Problem B vs. Problem A Distinction
A vital heuristic enforced throughout the engine:
- **Problem A (Data Availability / Backup Loss)**: "The photo was never backed up, deleted permanently, or lost during device migration."
- **Problem B (Retrieval Failure)**: "The photo is confirmed or known to exist in Google Photos, but the user cannot locate it due to imprecise memory, query mismatch, or system UX friction."
*Rule*: The engine isolates Problem B as the core research focus while isolating Problem A into a distinct audit category to analyze user perception and discoverability boundaries.

---

## 9. Clustering & Opportunity Framework
- **Clustering**: Emergent clustering powered by semantic similarity and multi-dimensional behavioral patterns (Scenario × Memory Cue × Failure Stage). No forced taxonomy clusters.
- **Opportunity Matrix**: Rather than generating a single arbitrary "opportunity score", each cluster is evaluated on a multidimensional matrix:
  1. *Evidence Volume* (absolute count of relevant items)
  2. *Source Diversity* (number of distinct platforms represented)
  3. *Recurrence* (pattern frequency across independent authors)
  4. *Severity* (user frustration, time spent, emotional value of visual memory)
  5. *Retrieval Impact* (complete failure vs. friction)
  6. *Existing Workaround Strength* (low/clunky vs. seamless)
  7. *Evidence Confidence* (traceability and source credibility)

---

## 10. Quality Controls & Anti-Hallucination Guarantees
1. **Zero Synthetic Reviews**: Real evidence only. Production datasets reject synthetic or simulated user posts.
2. **Traceability**: Every insight, finding, and cluster links directly to evidence records with valid source URLs and dates.
3. **Contradictory Evidence Preservation**: Conflicting user experiences (e.g., successful NLP search vs. failed NLP search) are highlighted side-by-side.
4. **Epistemic Labeling**: The UI and reports strictly demarcate `Evidence`, `User Quote`, `Observed Behavior`, `Inference`, `Hypothesis`, and `Opportunity Area`.

---

## 11. Constraints, Assumptions & Non-Goals
### Assumptions
- Public discussions reflect genuine user pain points but over-represent high-friction vocal users.
- Automated API and web data retrieval must comply with platform terms, rate limits, and public accessibility (no authentication bypass).

### Non-Goals for Part 1
- **Do NOT** jump to an MVP or final product solution.
- **Do NOT** mandate conversational AI or semantic search as the predetermined answer.
- **Do NOT** select the final target segment or single problem statement (reserved for Parts 2–4).
- **Do NOT** engineer heavy multi-cloud distributed infrastructure.
