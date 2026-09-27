# Phase 2 Validation Report — AI Relevance Classification & Behavioral Extraction

## 1. Objective
The objective of Phase 2 is to process ingested public user evidence from Phase 1, classify its retrieval relevance, and extract structured behavioral taxonomy attributes using the Groq LLM inference adapter while enforcing strict schema validation, provenance preservation, and anti-hallucination constraints.

---

## 2. Implementation Summary
Phase 2 establishes the end-to-end extraction and classification layer:
- **Prompt Isolation (`src/extraction/prompts/extraction_prompt.py`)**:
  - Contains `SYSTEM_PROMPT` and `EXTRACTION_USER_PROMPT`.
  - Establishes strict behavioral definitions, epistemic boundaries, and rules forbidding fabrication or assuming unmentioned details are forgotten.
  - Distinguishes Problem B (retrieval UX failure) from Problem A (data loss / missing backup).
- **Extraction Model & Validation (`src/models/extraction.py`)**:
  - `LLMExtractionResult`: Pydantic V2 schema with validators for failure stage sanitization, confidence clamping (0.0 to 1.0), and conversion into the canonical `NormalizedEvidenceRecord`.
- **Groq LLM Client Adapter (`src/extraction/llm_adapter.py`)**:
  - Operates behind an abstract interface using `GROQ_API_KEY` and `GROQ_MODEL`.
  - Features JSON-mode completions, exponential backoff (2s, 4s, 8s) on HTTP 429 (`RateLimitError`), request timeout handling (`APITimeoutError`), and markdown fence stripping.
- **Single-Record Extractor (`src/extraction/extractor.py`)**:
  - Orchestrates classification and extraction.
  - Fault-isolated fallback: If an LLM call fails or is unconfigured, the raw record is preserved with full provenance and labeled with `EXTRACTION_FAILED_OR_UNINITIALIZED`.
- **Batch Processing Pipeline (`src/extraction/pipeline.py`)**:
  - Stream-loads raw JSONL records from `data/raw/`.
  - Configurable batch size (`batch_size=10`) with polite rate throttling.
  - **Idempotency**: Maintains a set of already processed record IDs from `data/processed/`, preventing redundant API calls and expense.
  - **Separation of Concerns**: Directly and indirectly relevant evidence is routed to `data/processed/evidence_enriched.jsonl`, while irrelevant and failed records are routed to `data/processed/rejected_evidence.jsonl`.

---

## 3. Extraction Taxonomy Implemented

Each relevant evidence item is mapped across 11 structured dimensions:
1. `retrieval_relevance_class`: `DIRECTLY_RELEVANT`, `INDIRECTLY_RELEVANT`, `NOT_RELEVANT`.
2. `retrieval_object`: `PERSONAL_PHOTO`, `GROUP_PHOTO`, `EVENT_OR_TRIP`, `SCREENSHOT`, `UTILITY_DOCUMENT`, `HEALTH_OR_MEDICAL`, `VIDEO_OR_CLIP`, `MEMORY_OR_CREATION`, `OBJECT_OR_ITEM`, `UNKNOWN`.
3. `memory_cues`: Retained partial cues (`PERSON_OR_FACE`, `SPATIAL_OR_LOCATION`, `TEMPORAL_APPROXIMATE`, `VISUAL_APPEARANCE`, `OBJECT_OR_LANDMARK`, `ACTIVITY_OR_OCCASION`, `EMOTIONAL_OR_CONTEXTUAL`, `VISIBLE_TEXT`, `SOURCE_APP_OR_DEVICE`, `ALBUM_OR_CONTAINER`).
4. `missing_information`: Explicitly forgotten/unknown details (`EXACT_DATE`, `EXACT_LOCATION`, `EXACT_NAME`, `EXACT_TEXT`, `EXACT_FILENAME`, `ALBUM_OR_FOLDER`, `ACCOUNT_OR_SYNC_STATE`).
5. `search_behavior`: Physical retrieval actions (`KEYWORD_SEARCH`, `NATURAL_LANGUAGE_QUERY`, `PEOPLE_FILTER`, `LOCATION_FILTER`, `DATE_FILTER`, `DOCUMENT_CATEGORY_BROWSE`, `MANUAL_TIMELINE_SCROLL`, `FOLDER_OR_ALBUM_BROWSE`, `ARCHIVE_OR_TRASH_CHECK`, `QUERY_REFINEMENT`, `SEARCH_ABANDONMENT`).
6. `search_formulation`: Verbatim `original_query` alongside cleaned `normalized_query`.
7. `failure_stage`: 10 standardized categories (`MEMORY_RECALL`, `QUERY_FORMULATION`, `SYSTEM_UNDERSTANDING`, `RETRIEVAL_RELEVANCE`, `RESULT_EVALUATION`, `SEARCH_REFINEMENT`, `NAVIGATION_OR_DISCOVERABILITY`, `METADATA_OR_INDEXING`, `CONTENT_NOT_PRESENT_OR_UNAVAILABLE`, `OTHER`).
8. `workaround`: Compensatory user actions (`EXTERNAL_APP_SEARCH`, `PEOPLE_COLLABORATION`, `ENDLESS_MANUAL_SCROLL`, `THIRD_PARTY_GALLERY`, `RE_PHOTOGRAPHING`, `TOTAL_ABANDONMENT`).
9. `user_goal`: Concise articulation of user objective.
10. `outcome`: `SUCCESSFUL_RETRIEVAL`, `PARTIAL_SUCCESS`, `FAILED_RETRIEVAL`, `ABANDONED`, `UNCLEAR`.
11. `confidence`: Model confidence score (0.0 to 1.0).

---

## 4. Validation & Error Handling
- **Anti-Hallucination & Provenance**:
  - The pipeline never fabricates queries or quotes.
  - "Not mentioned" is explicitly enforced as NOT meaning "forgotten".
  - If a user does not mention typing a query, `search_formulation_original` is kept as `None`.
  - Every normalized record maintains an unbroken chain of custody to `id`, `source`, `source_url`, `published_at`, and `raw_text`.
- **Fault Isolation & Resilience**:
  - Invalid JSON from the model triggers retry loops; persistent failures fall back cleanly without terminating batch execution.
  - Invalid enums or hallucinated stages are filtered out via Pydantic validators (`validate_failure_stages`).
  - Rate limits (HTTP 429) back off with exponential sleep delays.

---

## 5. Offline Tests & Results
All tests were executed offline using mocked LLM fixtures marked `# TEST_FIXTURE_ONLY`:
- `test_directly_relevant_classification`: Validates medical receipt retrieval scenario and taxonomy mapping.
- `test_indirectly_relevant_classification`: Validates indexing / face grouping failure mapping.
- `test_not_relevant_classification`: Validates exclusion of editing tool crash.
- `test_missing_optional_fields_no_hallucination`: Validates that unmentioned details are not flagged as forgotten.
- `test_problem_a_vs_problem_b_distinction`: Validates segregation of `CONTENT_NOT_PRESENT_OR_UNAVAILABLE` from search relevance friction.
- `test_multiple_failure_stages_and_workarounds`: Validates multi-stage failure arrays (`MEMORY_RECALL`, `RESULT_EVALUATION`, `SEARCH_REFINEMENT`) and compensatory workarounds.
- `test_invalid_enum_sanitization`: Validates filtering of invalid enum values and confidence clamping.
- `test_malformed_json_fallback`: Validates recovery and fallback when LLM returns broken JSON.
- `test_rate_limit_and_timeout_resilience`: Validates exponential backoff and recovery on `RateLimitError`.
- `test_pipeline_idempotency`: Validates that already-processed record IDs are skipped during batch runs.

**Total Test Suite Results**:
`20 passed in 7.92s` (10 Phase 0/1 tests + 10 Phase 2 tests, 0 failures, 0 warnings).

---

## 6. Known Limitations
1. **Public Review Density**: App store reviews are often brief (1–2 sentences), resulting in sparse behavioral arrays (`memory_cues` may contain only 1 cue or query string may be omitted).
2. **Groq TPM/RPM Quotas on Large Batches**: When running production inference across hundreds of records on free-tier Groq API keys, batch sizes must be throttled with rate delays (`rate_delay=0.5s`) to avoid burst limits.
3. **Subjectivity in Ambiguous Queries**: Extremely vague complaints ("can't find my stuff") default to `confidence=0.5` and `UNCLEAR` outcomes.

---

## 7. Phase 3 Readiness
**READY**  
Phase 2 is structurally complete, fully tested, and ready to feed clean, validated normalized records into Phase 3 (Clustering & Multidimensional Opportunity Matrix) when requested.
