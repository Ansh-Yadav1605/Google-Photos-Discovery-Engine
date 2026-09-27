# Google Photos AI-Powered Discovery Engine

> **NextLeap Product Management Graduation Project — Part 1**  
> **Product**: Google Photos (Core Experience Team)  
> **Business Goal**: Increase the percentage of users who successfully retrieve a photo they remember but cannot precisely describe when they start searching.

---

## 1. Project Overview

The **Google Photos Discovery Engine** is an evidence-driven research system designed to discover, extract, compare, and surface real-world photo retrieval problem areas from public user conversations.

Instead of jumping prematurely into conversational search, AI chat, or pre-determined features, this engine ingests authentic feedback across multiple public platforms (Reddit, Google Play, Apple App Store, Google Photos Help Community, and public forums), strictly separates facts from inferences, and clusters emergent retrieval failure points.

---

## 2. Implementation Status

| Stage / Component | Status | Details |
|---|---|---|
| **Phase 0: Scaffolding & Docs** | **COMPLETED** | Context, architecture, methodology, taxonomy, data-source plan, edge cases, schemas, and configurations. |
| **Phase 1: Ingestion Layer** | **COMPLETED** | Multi-query library, 5 source adapters (Reddit, Google Play, App Store, Help Community, Manual Import), polite throttling, and raw JSONL audit persistence. |
| **Phase 2: AI Relevance & Extraction** | **COMPLETED** | Groq LLM adapter, structured taxonomy extraction, Pydantic validation, idempotency, rate-limit backoff, and separation of enriched vs rejected records. |
| **Phase 3: Clustering & Opportunity** | **COMPLETED** | Native scikit-learn HDBSCAN / Agglomerative clustering, SQLite persistence, and 7-dimensional transparent opportunity comparison matrix (no arbitrary ranking). |
| **Phase 4: Research Synthesis** | **COMPLETED** | Evidence-grounded synthesis of 8 core research findings, contradictory evidence auditing, and unbroken provenance verification chain. |
| **Phase 5: Backend API** | **COMPLETED** | FastAPI REST API endpoints serving SQLite analytical database with CORS, pagination, filtering, OpenAPI, and pipeline triggers. |
| **Phase 6: Discovery Dashboard** | **COMPLETED** | React + Vite PM research interface (`frontend/`) with 6 core views, side-drawer inspector, 7-dimensional Opportunity Matrix, and dual-mode serving. |
| **Phase 7: Validation Suite** | **COMPLETED** | Comprehensive end-to-end integration and quality validation tests (`tests/test_phase7_e2e_pipeline.py`); 48/48 tests passing. |
| **Phase 8: Final Part 1 Report** | **COMPLETED** | Complete 18-part formal graduation research report (`docs/part1-discovery-report.md`) with empirical findings and full provenance. |

---

## 3. Core Repository Structure

```
google-photos-discovery-engine/
├── docs/
│   ├── problemStatement.txt        # Concise problem statement & graduation brief
│   ├── context.md                  # Project context, research questions, non-goals
│   ├── architecture.md             # Detailed system architecture with Mermaid diagrams
│   ├── research-methodology.md     # Epistemology, sampling strategy, and bias audits
│   ├── taxonomy.md                 # 8 behavioral dimensions and 10 failure stages
│   ├── data-source-plan.md         # Source specifications, access methods, rate limits
│   ├── implementation-plan.md      # Phased implementation roadmap
│   ├── edge-case.md                # Network, linguistic, AI, and privacy mitigations
│   ├── phase0-phase1-review.md     # Formal validation and review report
│   └── part1-discovery-report.md   # Final synthesized research report (Planned)
│
├── data/
│   ├── raw/                        # Immutable raw source payloads (JSONL)
│   ├── processed/                  # Normalized, deduplicated, and classified evidence (Planned)
│   └── analysis/                   # Analytical SQLite database (discovery.db) (Planned)
│
├── src/
│   ├── config/                     # Typed configuration & settings
│   ├── models/                     # Canonical Pydantic data schemas
│   ├── ingestion/                  # Source-specific adapters & query library (Implemented)
│   ├── extraction/                 # Relevance classifier & Groq LLM extractor (Planned)
│   ├── clustering/                 # Emergent clustering (Planned)
│   ├── synthesis/                  # Research findings synthesizer (Planned)
│   ├── storage/                    # Database models and persistence layer (Planned)
│   └── api/                        # FastAPI REST endpoints (Planned)
│
├── frontend/                       # React + Vite Analytical Discovery Dashboard (Planned)
├── tests/                          # Automated unit and integration test suite (Implemented)
├── .env.example                    # Environment variable template
├── requirements.txt                # Python backend dependencies
└── README.md                       # Project guide
```

---

## 4. Current Setup & Verified Execution

### Prerequisites
- Python 3.10+
- Groq API Key (required for upcoming Phase 3 extraction)

### Installation & Verification

1. **Verify Automated Unit Tests (Offline / Mocked)**:
   ```bash
   python -m pytest tests/
   ```

2. **Run Phase 1 Ingestion Run (Authentic Public Records)**:
   ```bash
   python -m src.ingestion.pipeline
   ```
   Raw records are preserved in `data/raw/` with verifiable URLs, timestamps, and full text for complete provenance.

3. **Launch Discovery Engine API & Dashboard**:
   ```bash
   python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   ```
   - Open browser at `http://127.0.0.1:8000/` to access the **Analytical Discovery Dashboard**.
   - Interactive Swagger API docs are accessible at `http://127.0.0.1:8000/docs`.

4. **Run with Vite Dev Server (Optional / Node environments)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 5. Key Epistemic Principles
- **Zero Hallucinated Evidence**: Real public records only. Production analysis strictly forbids synthetic quotes or simulated reviews.
- **Problem B Focus**: Isolates retrieval UX failures (photo exists, but user cannot retrieve it) from Problem A (backup loss / deleted assets).
- **Multi-Factor Opportunity Matrix**: Evaluates and compares problem areas across 7 distinct dimensions without creating a single biased ranking score.
- **Traceability**: Every finding links directly to canonical source URLs, timestamps, and raw text.
