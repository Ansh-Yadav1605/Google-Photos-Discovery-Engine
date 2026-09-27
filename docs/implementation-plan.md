# Google Photos Discovery Engine — Implementation Plan

This plan establishes a phased, sequential development roadmap for Part 1. In accordance with Antigravity Execution Rules, implementation proceeds phase-by-phase with verification gates.

---

## Phase Overview & Progress Tracker

- [x] **Phase 0: Project Setup & Baseline Documentation**
- [x] **Phase 1: Multi-Source Data Ingestion Layer**
- [x] **Phase 2: AI Relevance Classification & Behavioral Evidence Extraction**
- [x] **Phase 3: Emergent Clustering & Multidimensional Opportunity Matrix**
- [x] **Phase 4: AI Research Synthesizer & Provenance Verifier**
- [x] **Phase 5: Backend REST API (FastAPI + SQLite)**
- [ ] **Phase 6: Analytical Discovery Dashboard (React + Vite)**
- [ ] **Phase 7: End-to-End Testing & Live Quality Validation**
- [ ] **Phase 8: Deployment & Part 1 Report Generation**

---

## Detailed Phase Breakdown

### Phase 0: Project Setup & Documentation
- **Deliverables**:
  - Full documentation suite (`problemStatement.txt`, `context.md`, `architecture.md`, `research-methodology.md`, `taxonomy.md`, `data-source-plan.md`, `implementation-plan.md`, `edge-case.md`).
  - Repository structure creation (`docs/`, `data/raw/`, `data/processed/`, `data/analysis/`, `src/`, `frontend/`, `tests/`).
  - Core dependency definition in `requirements.txt` (FastAPI, Uvicorn, Pydantic, Pandas, DuckDB/SQLite, httpx, google-play-scraper, app-store-scraper, beautifulsoup4, groq, scikit-learn).
  - Environment templates (`.env.example`) and `.gitignore`.
  - Initial `README.md` with startup instructions.
- **Verification Gate**: Directory structure intact, documentation reviewed for internal consistency, Python environment functional.

---

### Phase 1: Source Ingestion
- **Deliverables**:
  - `src/ingestion/base_adapter.py`: Abstract adapter interface with rate-limiting, error logging, and schema enforcement.
  - `src/ingestion/query_library.py`: Multi-family query repository.
  - `src/ingestion/adapters/reddit_adapter.py`: Reddit API + public JSON scraper.
  - `src/ingestion/adapters/google_play_adapter.py`: Scrapes targeted Google Photos reviews.
  - `src/ingestion/adapters/app_store_adapter.py`: Scrapes iOS App Store reviews.
  - `src/ingestion/adapters/community_adapter.py`: Scrapes public Google Photos Help Community threads.
  - `src/ingestion/adapters/manual_import_adapter.py`: Validated CSV/JSONL importer.
  - `src/ingestion/pipeline.py`: Orchestrator writing raw immutable records to `data/raw/*.jsonl`.
- **Verification Gate**: Running the ingestion pipeline collects authentic, non-synthetic public records into `data/raw/` with verifiable URLs and timestamps.

---

### Phase 2: AI Relevance Classification & Behavioral Extraction
- **Deliverables**:
  - `src/extraction/prompts/extraction_prompt.py`: System and user extraction prompts enforcing strict evidence boundaries and Problem B vs Problem A distinction.
  - `src/models/extraction.py`: Pydantic V2 extraction model (`LLMExtractionResult`) with validators for failure stages and confidence clamping.
  - `src/extraction/llm_adapter.py`: Groq API client adapter supporting JSON-mode completions, exponential backoff (2s, 4s, 8s) on HTTP 429, timeout handling, and markdown stripping.
  - `src/extraction/extractor.py`: Single-record classification and taxonomy extractor with fault-isolated provenance fallback.
  - `src/extraction/pipeline.py`: Batch extraction orchestrator with idempotency, batching, and separation of enriched vs rejected records.
  - `docs/phase2-validation.md`: Complete validation report.
- **Verification Gate**: All 20 tests pass cleanly; zero hallucinations; strictly enforces taxonomy enums; preserves raw user text.

---

### Phase 3: Emergent Clustering & Multidimensional Opportunity Matrix
- **Deliverables**:
  - `src/models/clustering.py`: Pydantic models for `ProblemCluster` and `OpportunityArea`.
  - `src/storage/database.py`: Embedded SQLite database manager (`data/analysis/discovery.db`) with tables for `evidence`, `clusters`, and `opportunity_matrix`.
  - `src/clustering/clusterer.py`: Emergent clustering engine (TF-IDF + categorical multi-hot representations + native scikit-learn HDBSCAN with Agglomerative fallback).
  - `src/clustering/opportunity_matrix.py`: Evaluator computing the 7 independent evidence dimensions without single composite scores or rankings.
  - `src/clustering/pipeline.py`: Phase 3 orchestrator saving SQLite records and JSON snapshots (`clusters.json`, `opportunities.json`).
  - `docs/phase3-validation.md`: Comprehensive validation report.
- **Verification Gate**: All 27 tests pass cleanly; clusters reflect emergent retrieval friction patterns without arbitrary bucketing; opportunity dimensions are completely transparent with zero winner ranking.

---

### Phase 4: AI Research Synthesizer & Provenance Verifier
- **Deliverables**:
  - `src/models/synthesis.py`: Pydantic models for `ProvenanceCitation`, `ContradictoryEvidence`, `FindingResult`, and `SynthesisReport`.
  - `src/storage/database.py`: Added `synthesis_findings` table with query and persistence methods (`save_findings`, `get_all_findings`, `get_finding`).
  - `src/synthesis/synthesizer.py`: Synthesizes answers to Findings 1–8 strictly from database evidence, clusters, and opportunity dimensions.
  - `src/synthesis/provenance_checker.py`: Verifies that every assertion links to valid evidence IDs and canonical URLs, auditing verbatim quote snippets.
  - `src/synthesis/pipeline.py`: Orchestrates Phase 4 execution, automated provenance audit, SQLite persistence, and JSON snapshot exports (`data/analysis/synthesis_findings.json`).
  - `docs/phase4-validation.md`: Comprehensive validation report.
- **Verification Gate**: All 34 tests pass cleanly; zero uncited claims; contradictory perspectives explicitly reported; unbroken DAG from findings to raw immutable records.

---

### Phase 5: Backend REST API (FastAPI + SQLite) — COMPLETED
- **Deliverables**:
  - `src/api/main.py`: FastAPI application with CORS, pagination, filtering, OpenAPI documentation (`/docs`), and pipeline orchestration.
  - Endpoints: `/api/health`, `/api/overview`, `/api/evidence`, `/api/evidence/{id}`, `/api/clusters`, `/api/clusters/{id}`, `/api/opportunities`, `/api/findings`, `/api/ingest`, `/api/analyze`.
  - Static frontend serving with Windows MIME registration for `.jsx`.
  - `tests/test_phase5_api.py`: 10 comprehensive endpoint tests.
  - `docs/phase5-validation.md`: Validation report for all API endpoints.
- **Verification Gate**: All endpoints return valid JSON matching front-end contracts; 10/10 tests pass.

---

### Phase 6: Discovery Dashboard (React + Vite) — COMPLETED
- **Deliverables**:
  - Modern, responsive SPA in `frontend/` (`package.json`, `vite.config.js`, `index.html`, `src/App.jsx`, `src/main.jsx`, `src/index.css`).
  - High-density dark-mode Obsidian design system built with custom Vanilla CSS.
  - 6 analytical views: Overview KPI cards, Interactive Evidence Explorer with side drawer, Problem Clusters, 7-dimensional Opportunity Matrix comparison, AI Synthesis with expandable citations and contradictory evidence, Research Methodology & Sampling Bias Audits.
  - Dual-mode serving: runs with Vite dev server (`npm run dev`) or directly served by FastAPI at `http://127.0.0.1:8000/`.
  - Automated browser E2E test verification via browser subagent.
  - `docs/phase6-validation.md`: Validation report with DOM assertions and screenshot captures.
- **Verification Gate**: Clean UI build, zero console errors, interactive filtering, all 6 views and side drawer verified.

---

### Phase 7: Testing & Quality Validation — COMPLETED
- **Deliverables**:
  - `tests/test_phase7_e2e_pipeline.py`: Comprehensive end-to-end integration and quality validation tests.
  - Verification of complete system lifecycle: raw ingestion -> taxonomy extraction -> SQLite storage -> emergent clustering -> 7D opportunity matrix -> research synthesis -> REST API exposure.
  - Epistemic invariants verified: Problem A (backup loss) isolation, zero arbitrary ranking scores, 100% provenance traceability, and contradictory evidence verification.
  - Total test suite coverage expanded to 48 tests across 7 test files.
  - `docs/phase7-validation.md`: Comprehensive validation report.
- **Verification Gate**: All 48 tests pass cleanly (`pytest` in 10.23s).

---

### Phase 8: Deployment & Final Part 1 Report — COMPLETED
- **Deliverables**:
  - `scripts/deploy_production_pipeline.py`: Automated production deployment orchestrator executing Phases 0–7 on authentic public records.
  - Deployment populated `data/analysis/discovery.db` with 72 authentic retrieval evidence records, 17 emergent clusters, 17 opportunity areas, and 8 research findings with 19 verified provenance citations.
  - `docs/part1-discovery-report.md`: Comprehensive, authoritative 18-part final research and discovery report covering problem space, methodology, taxonomy, clusters, 7D opportunity matrix, findings, contradictions, and Part 2 implications.
  - Operational FastAPI backend (`http://127.0.0.1:8000/`) and React/Vite dashboard.
  - Full test suite passing: 48/48 tests in 10.24s.
- **Verification Gate**: Complete verifiable artifact ready for Part 2 graduation project phase; all links, endpoints, and data contracts verified.
