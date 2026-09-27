# Google Photos Discovery Engine — Extraction Taxonomy

This document establishes the precise categorization rules, definitions, and valid enums applied by the extraction and classification engine.

---

## 1. Relevance Classification
Every raw ingested record must first be categorized by relevance:

| Class | Definition | Inclusion / Treatment | Examples |
|---|---|---|---|
| `DIRECTLY_RELEVANT` | The user describes an active attempt to locate, retrieve, search, or rediscover a specific photo, video, screenshot, or visual memory. | Included in core discovery engine analysis. | "Can't find a photo of my dog from 2 years ago", "Search returns random pictures instead of my trip" |
| `INDIRECTLY_RELEVANT` | The issue does not directly detail a search event, but directly degrades retrieval capability (e.g., face tagging bugs, broken metadata, album sorting chaos, delayed indexing). | Preserved in secondary analysis; tracked for upstream retrieval dependencies. | "Google Photos stopped grouping my daughter's face", "Dates changed after migration" |
| `NOT_RELEVANT` | Unrelated to retrieval, searching, or visual discovery. | Excluded from analytical synthesis; stored in `rejected_evidence.jsonl` for auditability. | "App crashes when editing with Magic Eraser", "Google One subscription is too expensive" |

---

## 2. Retrieval Object Taxonomy
Defines *what* the user is attempting to retrieve:

- `PERSONAL_PHOTO`: Solo photos, casual candid photos of self or pets.
- `GROUP_PHOTO`: Family gatherings, social outings, weddings, reunions.
- `EVENT_OR_TRIP`: Vacations, concerts, parties, ceremonies, travel excursions.
- `SCREENSHOT`: Receipts, chats, social media captures, transient transactional info.
- `UTILITY_DOCUMENT`: Passports, IDs, physical receipts, invoices, lease agreements, handwritten notes.
- `HEALTH_OR_MEDICAL`: Photos of prescriptions, medicine packaging, vaccination cards, skin lesions.
- `VIDEO_OR_CLIP`: Video recordings, clips, motion photos.
- `MEMORY_OR_CREATION`: Collages, auto-generated "Memories", animations, cinematic photos.
- `OBJECT_OR_ITEM`: Specific belongings, car parking spot, clothing item, serial number.
- `UNKNOWN`: Target object cannot be determined from text.

---

## 3. Memory Cues Taxonomy
Identifies *what partial clues* remain accessible in user memory:

- `PERSON_OR_FACE`: Remembers who was in the picture ("my mom and brother").
- `SPATIAL_OR_LOCATION`: Remembers rough location, city, venue, or type of place ("Goa trip", "small cafe in Paris").
- `TEMPORAL_APPROXIMATE`: Remembers vague time window, season, or life chapter ("last summer", "in college", "around 2021").
- `VISUAL_APPEARANCE`: Remembers colors, lighting, clothing, framing, or distinctive visual attributes ("everyone wearing black", "sunset glow").
- `OBJECT_OR_LANDMARK`: Remembers an artifact or physical feature ("red car", "wooden table", "Eiffel tower background").
- `ACTIVITY_OR_OCCASION`: Remembers what was happening ("hiking", "eating pasta", "birthday party").
- `EMOTIONAL_OR_CONTEXTUAL`: Remembers feelings, weather, or circumstances ("it was raining", "when I was sick").
- `VISIBLE_TEXT`: Remembers words, signs, brand names, or numbers visible in the image.
- `SOURCE_APP_OR_DEVICE`: Remembers how it was acquired ("downloaded from WhatsApp", "taken on old iPhone").
- `ALBUM_OR_CONTAINER`: Remembers placing it in a folder, favorite list, or archive.

---

## 4. Forgotten Information Taxonomy
Identifies *what specific metadata* the user explicitly or implicitly lacks:

- `EXACT_DATE`: Cannot recall the exact day or month.
- `EXACT_LOCATION`: Remembers the scene but not the city, GPS location, or venue name.
- `EXACT_NAME`: Does not remember the name of the person, restaurant, or entity.
- `EXACT_TEXT`: Cannot remember specific wording on a screenshot or document.
- `EXACT_FILENAME`: Has no knowledge of the camera file string (e.g., `IMG_20230814_WA0023.jpg`).
- `ALBUM_OR_FOLDER`: Does not remember if or where it was organized.
- `ACCOUNT_OR_SYNC_STATE`: Unsure which Google account or device originated the photo.

---

## 5. Search Behavior Taxonomy
Identifies the physical actions and retrieval strategies deployed by the user:

- `KEYWORD_SEARCH`: Enters 1–3 disconnected descriptive words ("beach dog sunset").
- `NATURAL_LANGUAGE_QUERY`: Enters a conversational sentence ("show me photos of my dog at the beach last year").
- `PEOPLE_FILTER`: Taps a face in the People & Pets cluster.
- `LOCATION_FILTER`: Uses the Places map or city filter.
- `DATE_FILTER`: Enters a year, month, or uses date picker.
- `DOCUMENT_CATEGORY_BROWSE`: Checks the Documents tab (Receipts, IDs, Notes).
- `MANUAL_TIMELINE_SCROLL`: Manually scrubs up and down the infinite main timeline.
- `FOLDER_OR_ALBUM_BROWSE`: Navigates into Albums or Library tab.
- `ARCHIVE_OR_TRASH_CHECK`: Inspects Archive or Trash bins.
- `QUERY_REFINEMENT`: Repeatedly adjusts, adds, or swaps keywords after empty/poor results.
- `SEARCH_ABANDONMENT`: Stops searching due to frustration or exhaustion.

---

## 6. Failure Stage Taxonomy (10 Standardized Categories)

```
[1. MEMORY RECALL]
       ↓
[2. QUERY FORMULATION]
       ↓
[3. SYSTEM UNDERSTANDING]
       ↓
[4. RETRIEVAL RELEVANCE]
       ↓
[5. RESULT EVALUATION]
       ↓
[6. SEARCH REFINEMENT]
       ↓
[7. NAVIGATION / DISCOVERABILITY]
       ↓
[8. METADATA / INDEXING]
       ↓
[9. CONTENT NOT PRESENT (Problem A)]
       ↓
[10. OTHER]
```

1. `MEMORY_RECALL`: The user's internal memory is too degraded or distorted to produce any viable search anchor.
2. `QUERY_FORMULATION`: The user has cues in mind but struggles to translate them into words or filters Google Photos can understand.
3. `SYSTEM_UNDERSTANDING`: The user holds a mismatched mental model of how Google Photos indexes, searches, or sorts visual data.
4. `RETRIEVAL_RELEVANCE`: The search engine returns results, but they are completely irrelevant, noisy, or overwhelm the target photo.
5. `RESULT_EVALUATION`: The system returns hundreds of similar photos without useful visual sorting, thumbnails, or highlight cues, forcing exhaustive manual inspection.
6. `SEARCH_REFINEMENT`: The user attempts to narrow down bad results, but the system lacks compositional filters (e.g., "in Goa AND with Mom AND sunset").
7. `NAVIGATION_OR_DISCOVERABILITY`: The feature or photo exists, but is buried in obscure nested sub-menus (Locked Folder, Archive, Utilities, Device Folders).
8. `METADATA_OR_INDEXING`: Exif metadata is incorrect, missing, stripped (e.g., from WhatsApp/social media), or search indexing is delayed.
9. `CONTENT_NOT_PRESENT_OR_UNAVAILABLE`: The photo was never uploaded, deleted, or stored on another unsynced account (Problem A).
10. `OTHER`: Unclassified technical or edge-case failure.

---

## 7. Workarounds Taxonomy
Compensatory behaviors users adopt when Google Photos retrieval fails:

- `EXTERNAL_APP_SEARCH`: Searching WhatsApp, Instagram DMs, iMessage, or email where the photo was originally shared.
- `PEOPLE_COLLABORATION`: Asking a friend, spouse, or family member to re-send the photo.
- `ENDLESS_MANUAL_SCROLL`: Spending 15–45 minutes scrolling through months or years of timeline thumbnails.
- `THIRD_PARTY_GALLERY`: Using Samsung Gallery, Apple Photos, or specialized desktop tools (DigiKam, Lightroom).
- `RE-PHOTOGRAPHING`: Taking a new photo of a physical receipt, document, or object rather than finding the old one.
- `TOTAL_ABANDONMENT`: Resigning to the loss of the memory or document.

---

## 8. Outcome Taxonomy
- `SUCCESSFUL_RETRIEVAL`: Photo found through search or navigation.
- `PARTIAL_SUCCESS`: Found a related photo, but not the specific memory desired.
- `FAILED_RETRIEVAL`: Photo confirmed present in account but unfindable via search.
- `ABANDONED`: User gave up after friction.
- `UNCLEAR`: Insufficient text in the review/post to determine outcome.

---

## 9. Evidence Type & Confidence Scoring
- `USER_STATEMENT`: Direct assertion of user experience or opinion.
- `OBSERVED_BEHAVIOR`: Concrete behavioral trajectory documented step-by-step.
- `CONFIDENCE_SCORE` (0.0 to 1.0):
  - **0.90 – 1.00**: High detail, explicit query, clear failure point, timestamped source.
  - **0.70 – 0.89**: Clear symptom with at least 2 behavioral attributes identifiable.
  - **0.50 – 0.69**: Brief statement with inferred context.
  - **< 0.50**: Flagged for human review or rejected from cluster analysis.
