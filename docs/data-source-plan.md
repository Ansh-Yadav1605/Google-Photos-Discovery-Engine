# Google Photos Discovery Engine — Data Source Acquisition Plan

## 1. Overview & Policy Principles
This data acquisition plan defines the ingestion mechanisms, compliance safeguards, query parameters, rate limits, and fallback strategies for public data sources.

### Core Safeguards
1. **Public Information Only**: Only ingest publicly available discussions, app reviews, and community threads.
2. **Zero Authentication Bypass**: Never bypass logins, paywalls, CAPTCHAs, or access barriers.
3. **Robots.txt & Terms Compliance**: Respect platform headers, rate limits, and backoff requests.
4. **Privacy Protection**: Anonymize personal handles; strip detected email addresses, telephone numbers, and sensitive personal identifiers.

---

## 2. Source-by-Source Technical Specifications

### Source 1: Reddit
- **Target Channels**: `r/googlephotos`, `r/google`, `r/Android`, `r/techsupport`
- **Access Method**:
  - *Primary*: Reddit Data API via standard HTTP / `praw` (using read-only credentials `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and descriptive user agent).
  - *Fallback*: Public Reddit JSON feeds (`https://www.reddit.com/r/googlephotos/search.json?q=...&restrict_sr=1`) with polite rate limits (1 req / 2s).
- **Query Strategy**:
  - Target terms: `can't find old photos`, `search doesn't work`, `search by description`, `search people`, `screenshot`, `find photo`, `Ask Photos`, `search date`.
- **Fields Collected**:
  - `id` (reddit submission ID)
  - `permalink` / `url`
  - `title`
  - `author` (or `[deleted]`)
  - `created_utc` (converted to ISO-8601)
  - `selftext` (raw post body)
  - `num_comments`, `score`
  - Top 3 relevant top-level comments (if providing context on workarounds or queries)
- **Rate Limits & Backoff**: Maximum 60 requests/minute. Sleep 1.0s between queries; exponential backoff on HTTP 429.
- **Known Limitations**: Reddit content skews younger, male, and more tech-savvy than typical Google Photos demographics.

---

### Source 2: Google Play Store Reviews
- **Target Package**: `com.google.android.apps.photos`
- **Access Method**:
  - `google-play-scraper` (Python library querying public Google Play web endpoints).
- **Query Strategy**:
  - Filter by ratings (1, 2, 3 stars prioritized for friction; 4-5 stars checked for feature appreciation/comparison).
  - Target keywords in search: `search`, `find photo`, `retrieve`, `memories`, `old photos`, `can't find`, `lost photo`, `where is`.
- **Fields Collected**:
  - `reviewId`
  - `userName` (anonymized)
  - `content` (review text)
  - `score` (1-5)
  - `thumbsUpCount`
  - `reviewCreatedVersion`
  - `at` (review timestamp ISO-8601)
  - `replyContent` (official Google support reply if present)
- **Rate Limits & Backoff**: Batch size 100 reviews; delay 1.5s between batches.
- **Known Limitations**: Character length is often brief (1–3 sentences); lacks deep step-by-step query debugging compared to Reddit.

---

### Source 3: Apple App Store Reviews
- **Target App ID**: `962194608` (Google Photos on iOS App Store)
- **Access Method**:
  - `app-store-scraper` / Apple iTunes RSS Customer Reviews API.
- **Query Strategy**:
  - Query English reviews (US, GB, IN, CA regions) sorting by most helpful and most recent.
  - Filter for retrieval and search keywords.
- **Fields Collected**:
  - `id`
  - `title`
  - `review` (raw text)
  - `rating` (1-5)
  - `date` (ISO-8601)
  - `userName`
- **Rate Limits & Backoff**: Maximum 20 requests/minute; delay 2.0s between regional fetches.
- **Known Limitations**: Often conflates Google Photos with Apple Photos / iCloud sync behavior; requires relevance filtering.

---

### Source 4: Google Photos Help Community
- **Target Portal**: `support.google.com/photos/threads`
- **Access Method**:
  - *Primary*: Permitted public HTML parsing of public search query results via `requests` + `BeautifulSoup4` with custom research user agent.
  - *Fallback*: Automated public search engine index queries (`site:support.google.com/photos/thread "can't find photo"`) or manual JSONL export.
- **Query Strategy**:
  - Query families: `find old photos`, `search results not matching`, `face recognition not finding`, `search date wrong`.
- **Fields Collected**:
  - `thread_id`
  - `url` (canonical thread URL)
  - `title`
  - `author`
  - `date`
  - `question_text` (original post)
  - `recommended_answer` (Google Product Expert answer if marked)
  - `upvotes` / "I have the same question" counter
- **Rate Limits & Backoff**: Strictly 1 request every 3 seconds. Respect `robots.txt`.
- **Known Limitations**: Heavy presence of Problem A (backup loss / deleted items), requiring stringent relevance filtering.

---

### Source 5: Public Tech Forums & YouTube Tech Discussions
- **Target Platforms**: XDA Developers, Android Central forums, public YouTube comments on Google Photos search tutorials and feature announcements (e.g., Ask Photos launch).
- **Access Method**:
  - *YouTube Data API v3* (using `YOUTUBE_API_KEY` for public comments on relevant video IDs).
  - *Manual CSV/JSONL Ingestion Pipeline* for audited forum exports.
- **Fields Collected**:
  - `id`, `video_id` / `forum_thread_id`, `url`, `author`, `published_at`, `raw_text`, `like_count`.
- **Rate Limits**: YouTube quota tracking (1 quota unit per comment thread list).
- **Known Limitations**: Video comments are often tangential; requires rigorous relevance classification.

---

## 3. Configurable Query Library Matrix

| Query Family | Query Strings | Target Sources |
|---|---|---|
| **Family A: Search Failure** | `"can't find old photos"`, `"Google Photos search not finding"`, `"Google Photos search doesn't work"`, `"search by description"` | Reddit, Google Play, Community, App Store |
| **Family B: Contextual Cues** | `"Google Photos search people"`, `"Google Photos search location"`, `"Google Photos search date"`, `"can't find screenshot"`, `"find document"` | Reddit, Community, App Store |
| **Family C: Retrieval Friction** | `"Google Photos remember photo can't find"`, `"irrelevant search results"`, `"scroll forever"`, `"Google Photos Ask Photos"` | Reddit, Community, YouTube |

---

## 4. Fallback & Manual Ingestion Workflow
When live network adapters encounter persistent CAPTCHAs, IP blocking, or API outages:
1. System provides `src/ingestion/adapters/manual_import.py`.
2. Researchers place verified public data files in `data/raw/manual_imports/*.jsonl` or `.csv`.
3. The normalizer processes manual files using the identical schema, verifying source URLs and publication dates.
4. **Guaranteed Zero Synthetic Data**: Manual files must contain verifiable public URLs. Synthetic or simulated text is rejected.
