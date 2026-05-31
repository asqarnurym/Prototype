# TODO

## Completed (2026-05 — SQLite integration sprint)

- SQLite persistence layer (`core/database.py`, 7 tables)
- Dual-write: JSON + SQLite mirror for all job state
- `GET /api/metrics`, `GET /api/runs` analytics endpoints
- Seed corpus from CSV (`scripts/seed_corpus.py`)
- Service smoke test: Whisper CUDA + Gemini Vertex + Google TTS
- Evaluation run modes: default (resume latest), `--force-new`, `--resume-run`
- Filter flags: `--lang`, `--duration`, `--content`, `--vids`, `--limit`
- Blank frame detection (black screen → skip)
- Gemini rate-limit retry with exponential backoff
- Stronger description prompt (forbid generic phrases)
- `run_meta.json` per-run metadata file
- 5 extended traceability metrics: `avg_content_score`, `has_screen_text_pct`,
  `avg_description_chars`, `generic_description_pct`, `blank_scenes_skipped`
- Documentation sync: README.md, USAGE.md, TESTING.md updated
- 65 unit+integration tests passing

---

## Active — v2 Pipeline Improvements

### 1. Transcription-anchored scene sampling
**Problem:** Uniform 30s sampling on talking-head videos produces near-identical
frames. Gemini responds with "A new visual element..." because it can't
distinguish them. Coverage is only ~77% for long talking-head content.
**Solution:** Use ASR transcript to anchor scenes at topic-change boundaries
(sentence ends, long pauses, keyword shifts). Describe what's being said AND
what's shown at that moment.

### 2. Content-type adaptive PySceneDetect thresholds
**Problem:** `ContentDetector(thr=27)` is optimised for screencasts. Talking-head
and slide-centric videos have fundamentally different visual change patterns.
**Solution:** Set threshold per `content_type`: 27 for screencast/slide-centric,
18 for talking-head, 22 for practical-demo.

### 3. Few-shot + chain-of-thought prompting for Gemini
**Problem:** Gemini sometimes ignores prompt instructions ("NEVER use generic
phrases") when frames are very similar.
**Solution:** Include 2-3 example descriptions in the prompt. Add a secondary
"difference from previous frame" analysis step before generating final text.

### 4. Content-aware blank frame detection (v2)
**Problem:** Not just black screens — static slide frames, title cards with
no change, watermark-only frames also waste API calls.
**Solution:** Compare consecutive frames for pixel difference. If <2% change
and no new screen text detected, skip.

### 5. Scene-to-transcript alignment for audio description quality
**Problem:** Scene descriptions are purely visual. For talking-head content,
the *topic* matters more than the *visual*.
**Solution:** After scene indexing, find the nearest transcript segment and
enrich the scene with a `spoken_context` field. On-demand TTS can then
prepend "Speaker is discussing X while..." before the visual description.

### 6. Rate-limit exhaust latency accumulation
**Problem:** v1.1 added exponential backoff (2s→4s→8s→16s, max 4 retries).
For a 24-video corpus with ~50 scenes each, worst-case retry exhaust could
add (2+4+8+16) × 50 × 24 = 36,000s = 10 hours of pure retry wait time.
**Risk:** This makes B1 pipeline latency non-deterministic and environment-dependent.
**Mitigation:** Monitor retry rate per-run via `run_meta.json`. If >5% of
descriptions trigger retries, flag the run as degraded. For v2, consider:
(a) per-location quota pre-check before batch processing,
(b) adaptive concurrency (reduce workers on first 429),
(c) multi-region fallback (try us-central1 → europe-west4 → asia-southeast1).

### 7. Optimal Vertex AI location for Kazakhstan (Astana)
**Status:** Probed 2026-05-31 via `tests/evaluation/location_probe.py`.
**Results** (gemini-2.5-flash, 5 measured requests per location):

| Location | Median | Min | Max | OK/Fail | Notes |
|----------|--------|-----|-----|---------|-------|
| `europe-west1` (Belgium) | **423ms** | 407ms | 463ms | 7/8 | **RECOMMENDED** |
| `europe-west4` (Netherlands) | 460ms | 358ms | 473ms | 8/8 | Most reliable (0 failures), good fallback |
| `us-east4` (Virginia) | 600ms | 571ms | 859ms | 8/8 | Higher latency |
| `asia-southeast1` (Singapore) | 792ms | 792ms | 792ms | 4/8 | Quota exhaustion |
| `asia-northeast1` (Tokyo) | — | — | — | 0/8 | 429 RESOURCE_EXHAUSTED |
| `us-central1` (Iowa) | — | — | — | 0/8 | 429 RESOURCE_EXHAUSTED |

**Decision:** `GOOGLE_CLOUD_LOCATION=europe-west1` applied in `.env`.
**Rationale:** Lowest median latency (423ms) with acceptable reliability.
`europe-west4` is the backup if quota becomes an issue on europe-west1.
**Note:** `us-central1` was rate-limited — likely because `global` was
routing there and our evaluation runs exhausted its quota. This explains
the 429 errors seen during earlier runs.

---

## Candidate Ideas

- Latency breakdown for on-demand audio description (lookup + cache + TTS)
- Focused benchmark: cold cache vs warm cache for TTS
- Quality rubric for scene descriptions: usefulness, specificity, absence of fallback
- Regression guard: fail evaluation if >10% scenes are generic
- Replace `output/*/job_meta.json` as primary store — migrate fully to SQLite

---

## Key Files

- Current article: `academic_paper/paper.tex` (entrypoint: `academic_paper/main.tex`)
- Evaluation driver: `tests/evaluation/run_corpus_eval.py`
- Database: `core/database.py` → `data/prototype.db`
- Corpus manifest: `evaluation/corpus_manifest.csv`
- Paper metrics: `evaluation/run_001/`
- Service smoke test: `tests/evaluation/service_smoke.py`

---

## Version history

| Version | Changes |
|---------|---------|
| v1 (paper) | ASR + PySceneDetect + Gemini + TTS, 24-video bilingual corpus, adaptive indexing, on-demand AD |
| v1.1 (current) | SQLite persistence, dual-write, eval run modes, filters, blank frame detection, rate-limit retry, traceability metrics |
| v2 (planned) | Transcription-anchored scenes, adaptive thresholds, few-shot prompting, content-aware blank detection |
