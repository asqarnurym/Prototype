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
