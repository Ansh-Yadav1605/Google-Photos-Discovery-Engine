# Google Photos Discovery Engine — Edge Cases & Mitigation Catalog

*Status: Living Document*
*Last Updated: September 2026*

This catalog enumerates technical, behavioral, linguistic, and data-integrity edge cases encountered across the discovery pipeline, along with designated handling strategies and fallback mechanisms.

---

## 1. Network & Source Availability Edge Cases

### 1.1 Source Unavailable / Network Timeout
- **Symptom**: HTTP 500/503 from Reddit API, App Store scrapers failing due to rate limits or region blocks.
- **Impact**: Pipeline hangs or crashes mid-ingestion.
- **Mitigation**:
  - All network calls use configured timeouts (default 10s).
  - Exponential backoff with jitter (max 3 retries: 2s, 4s, 8s).
  - Individual source failure isolates gracefully; pipeline marks source as `DEGRADED` or `UNAVAILABLE` and continues processing other active adapters.

### 1.2 API Rate Limits (HTTP 429)
- **Symptom**: Reddit API or Groq LLM API returning rate limit exhaustion headers.
- **Impact**: Ingestion halted, high error rates.
- **Mitigation**:
  - Enforce token bucket rate limiting inside base adapter (`src/ingestion/base_adapter.py`).
  - Read `Retry-After` HTTP headers when present and automatically pause workers.
  - Implement batch queueing with sleep buffers for LLM inference (e.g., 20 requests/minute max).

---

## 2. Ingestion & Content Integrity Edge Cases

### 2.1 Deleted Reddit Post / Deleted Community Thread
- **Symptom**: Reddit post body reads `[deleted]` or `[removed]`, or support thread returns HTTP 404.
- **Impact**: Ingestion of empty or uninformative records.
- **Mitigation**:
  - Filter during ingestion: if `selftext` in `['[deleted]', '[removed]', '']` and `title` contains fewer than 4 meaningful words, discard record.
  - If title contains a rich descriptive query (e.g., "Cannot find pictures from 2021 where my son is wearing green shirt"), preserve title as text and flag `body_missing=True`.

### 2.2 Review Without Useful Text
- **Symptom**: User leaves 1-star review on Google Play with text: "bad", "hate update", "fix it", or single emoji.
- **Impact**: Noise in extraction and classification pipeline.
- **Mitigation**:
  - Pre-filter: Discard reviews where word count $< 4$ unless containing a specific keyword (e.g., "search broken").
  - Flag in audit log as `FILTERED_SHORT_TEXT`.

### 2.3 Extremely Long Discussions / Comment Floods
- **Symptom**: Reddit mega-thread or Help Community discussion with 200+ comments.
- **Impact**: LLM context window overflow and high token costs.
- **Mitigation**:
  - Ingest original post and top 3 highest-upvoted comments providing direct behavioral troubleshooting.
  - Truncate input text to maximum 1,500 tokens before LLM relevance classification.

### 2.4 Duplicate & Near-Duplicate Posts
- **Symptom**: The same user posts identical complaints on both Reddit and Google Photos Help Community, or syndicates across subreddits.
- **Impact**: Artificially inflates cluster frequency and evidence counts.
- **Mitigation**:
  - Compute normalized URL hash and content MinHash/SimHash.
  - If similarity $\ge 0.88$, merge records: preserve primary ID, append cross-posted source URL to `secondary_source_urls`, and increment `cross_post_count` without increasing independent evidence weight.

### 2.5 Spam, Promotional Content & Bot-Generated Posts
- **Symptom**: Links promoting third-party recovery software ("Use Dr.Fone to recover photos!"), crypto spam, or bot-generated SEO text.
- **Impact**: Poisoned retrieval findings.
- **Mitigation**:
  - Regex keyword heuristics matching commercial recovery tools (`easeus`, `dr.fone`, `stellar`, `tenorshare`, `whatsapp spy`).
  - Mark as `SPAM_EXCLUDED`.

---

## 3. Linguistic & Behavioral Ambiguity Edge Cases

### 3.1 Multilingual Content
- **Symptom**: User reviews in Spanish, Hindi, German, Portuguese, or code-mixed Hinglish ("Photo mil nahi rahi search mein").
- **Impact**: Rule-based keyword scrapers miss critical feedback or misclassify relevance.
- **Mitigation**:
  - Detect language using lightweight `langdetect` or fast LLM pass.
  - If non-English, preserve `original_language` and utilize LLM translation to normalize `english_translation` while retaining raw source text for auditability.

### 3.2 Sarcasm & Rhetorical Hyperbole
- **Symptom**: "Oh wonderful, Google Photos thinks my wedding was a picture of a dog!" or "Brilliant search, found literally everything except what I asked for."
- **Impact**: Naive sentiment analysis classifies as positive praise.
- **Mitigation**:
  - Structured extraction prompt instructs model to differentiate between literal compliment and sarcastic failure description by checking `outcome` and `retrieval_relevance`.

### 3.3 Vague or Indeterminate Complaints
- **Symptom**: "I can never find anything in this app anymore."
- **Impact**: Lacks specific retrieval cues, memory objects, or failure stages.
- **Mitigation**:
  - Tagged as `DIRECTLY_RELEVANT`, but fields `memory_cues` and `missing_information` remain empty arrays `[]`.
  - Confidence scored at $0.50$ (marginal). Excluded from granular feature-level clusters; included only in macro-level sentiment distributions.

### 3.4 Conflation of Problem A (Missing Data) and Problem B (Retrieval Failure)
- **Symptom**: "All my photos from 2022 are gone, I can't find them anywhere."
- **Impact**: Mixing account sync or data-loss bugs with search UX failures.
- **Mitigation**:
  - Explicit classification check: Did the user lose backup access, delete photos, or switch accounts?
  - If ambiguous, classify failure stage as `METADATA_OR_INDEXING` or `CONTENT_NOT_PRESENT_OR_UNAVAILABLE` and segregate from Core UX Retrieval clusters.

---

## 4. AI & Extraction Edge Cases

### 4.1 Malformed LLM Response / Schema Violation
- **Symptom**: LLM returns invalid JSON, markdown wrappers (` ```json `), or truncates mid-object.
- **Impact**: Parsing error crashes pipeline.
- **Mitigation**:
  - JSON parser strips markdown backticks and validates against Pydantic schema (`EvidenceExtraction`).
  - If validation fails, initiate automated repair retry with temperature 0.0. If second attempt fails, record raw text and tag `EXTRACTION_FAILED` for offline inspection.

### 4.2 Hallucinated Quotes & Unsupported Claims
- **Symptom**: LLM produces an executive synthesis containing fabricated quotes not present in the ingested raw text.
- **Impact**: Destroys research integrity.
- **Mitigation**:
  - Automated Substring Verification: Every quote rendered in the synthesis is programmatically checked against `raw_text` of the cited `evidence_id`.
  - If quote is not found verbatim, flag as `AI-generated paraphrase` and reject direct quotation marks.

### 4.3 Conflicting / Contradictory Evidence
- **Symptom**: One cohort of users reports "Ask Photos finds obscure things using complex sentences", while another cohort reports "Descriptive search is completely useless and shows unrelated garbage".
- **Impact**: Oversimplified synthesis claims false consensus.
- **Mitigation**:
  - The Synthesis Engine has an explicit `Contradictory Evidence` module.
  - When variance exceeds threshold across sentiment/outcome for similar queries, both viewpoints are presented alongside their respective source distributions.

### 4.4 Insufficient Evidence
- **Symptom**: Only 1 or 2 evidence items found for an obscure query (e.g., "search medicine packaging").
- **Impact**: Risk of creating spurious problem clusters or unjustified roadmap recommendations.
- **Mitigation**:
  - Hard constraint: Clusters require a minimum of 3 independent items and minimum 2 distinct authors.
  - Clusters with $N < 3$ are placed in `EMERGING_SIGNALS_UNCONFIRMED` and excluded from the prioritized Opportunity Matrix.

---

## 5. Privacy & Sensitive Content Edge Cases

### 5.1 Privacy-Sensitive User Content
- **Symptom**: A user accidentally posts private details in a forum (e.g., full name, phone number, email address, home address, medical condition).
- **Impact**: Ethical breach and privacy violation.
- **Mitigation**:
  - Pre-processing regex sanitization scrubs email patterns (`[\w\.-]+@[\w\.-]+\.\w+`), phone numbers, and street addresses before saving to `data/processed/`.
  - Display author handles with partial masking (e.g., `u/j***9`) if requested.
