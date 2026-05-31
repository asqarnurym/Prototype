# Testing & Evaluation

This guide covers the full Prototype testing and evaluation workflow:
developer tests, service smoke checks, SQLite-backed evaluation pipeline,
and paper-chart generation.

---

## Quick Reference

| Task | Command |
|------|---------|
| Run all dev tests | `.venv\Scripts\python -m pytest tests/unit tests/integration -q` |
| Smoke-test services | `.venv\Scripts\python tests/evaluation/service_smoke.py` |
| Full corpus eval | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py` |
| Force new run | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py --force-new` |
| Resume specific run | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py --resume-run run_003` |
| Eval: Russian only | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py --lang ru` |
| Eval: short videos | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py --duration short` |
| Eval: specific videos | `.venv\Scripts\python tests/evaluation/run_corpus_eval.py --vids en_short_talking_head,ru_long_screencast` |
| Seed corpus into DB | `.venv\Scripts\python scripts/seed_corpus.py` |
| Regenerate charts | `.venv\Scripts\python scripts/generate_charts.py` |

---

## Database (SQLite)

### Architecture

The system uses a hybrid persistence model: **SQLite is the primary store**,
with **JSON/CSV files kept as a read-compatible replica**.

```
                        ┌──────────────┐
                        │   SQLite DB   │ ◄── primary write target
                        │ data/proto.db │
                        └──────┬───────┘
                               │ mirror on write
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       job_meta.json    per_video.csv    evaluation_report.json
```

### Schema (7 tables)

| Table | Purpose |
|-------|---------|
| `videos` | Corpus + uploaded videos. `source` column: `"corpus"` or `"upload"`. |
| `jobs` | Processing jobs. FK → `videos(id)`. Tracked: status, timing, errors. |
| `artifacts` | Paths to generated files (subtitles, timeline, scene_index, summary). |
| `scenes` | Indexed scene descriptions with quality metrics (content_score, has_screen_text). |
| `tts_cache` | Language-scoped TTS audio paths. FK → `scenes(id)`. |
| `evaluation_runs` | Evaluation run metadata (run_name, total_videos, timestamps). |
| `evaluation_metrics` | Per-video metrics. FK → `evaluation_runs(id)`. Supports `ON CONFLICT ... UPDATE`. |

### API endpoints

```
GET  /api/runs                       list all evaluation runs
GET  /api/metrics?run_id=N           per-video metrics for run N
GET  /api/metrics?run_id=N&lang=ru  filter by language
```

### Dual-write guarantee

Every `process_video` call (via API or CLI) writes **simultaneously**:
1. `job_meta.json` in `output/{job_id}/` (legacy, for reference)
2. `jobs` + `artifacts` + `scenes` rows in SQLite (primary)

`run_corpus_eval.py` mirrors per-video metrics into `evaluation_metrics`
alongside the CSV output.

---

## Service Smoke Test

`tests/evaluation/service_smoke.py` verifies all three external services
in a single, quick pass (~30 seconds). Run it whenever you change
credentials, environment, or model versions.

```bash
.venv\Scripts\python tests/evaluation/service_smoke.py
```

**What it checks:**

| Service | Checks |
|---------|--------|
| **Whisper** | CUDA device, compute type, model size, transcription output (segments + words), word confidence ≥ 0.5, response time |
| **Gemini 2.5 Flash** | Vertex AI mode, project/location configured, no `429 RESOURCE_EXHAUSTED`, description is not a fallback/placeholder, length ≥ 20 chars, response ≤ 30s |
| **Google TTS** | Provider is `google`, output file exists, file size > 0, audio duration > 0 (both reported and probed) |

All three must pass before evaluating the corpus — otherwise your metrics
will be invalid (fallback descriptions, wrong TTS provider, CPU fallback).

---

## Corpus Evaluation (`run_corpus_eval.py`)

### Run modes

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| **Resume latest** (default) | `run_corpus_eval.py` | Resumes the most recent `run_NNN` in-place. Fills missing videos only. Creates `run_001` if no runs exist. |
| **Force new** | `--force-new` | Creates a fresh `run_NNN`. Ignores ALL cached metrics and artifacts. Reprocesses every selected video. |
| **Resume specific** | `--resume-run run_003` | Resumes a specific run in-place. Use when you need to fill gaps in a run that isn't the latest. |

### Filter flags (combine with any mode)

| Flag | Example | Effect |
|------|---------|--------|
| `--lang en` | Only English | Filters corpus_manifest.csv |
| `--duration short` | Short videos only | `short` / `medium` / `long` |
| `--content screencast` | Screencasts only | `talking_head` / `slide-centric` / `screencast` / `practical_demo` |
| `--vids a,b,c` | Specific videos | Comma-separated video IDs |
| Combined | `--lang ru --duration long` | Russian + long = 4 videos |

### Cache validation

Before processing, the script audits all selected videos:

```
[*] 3 videos need B0 (ASR-only) processing
[*] 5 videos need B1 (Full Pipeline) processing
```

A video is considered **cached** only when:
- `output/{vid_id}_B0/job_meta.json` exists with `processing_time_sec > 0`
- `output/{vid_id}_B0/` contains `subtitles.vtt` + `timeline.json`
- For B1: also `scene_index.json`
- `per_video_metrics.csv` row has valid positive values for all RTF/duration fields

If you delete `output/` but keep `evaluation/run_*/`, the script will
**detect the mismatch** and re-process those videos.

### Output files

```
evaluation/run_NNN/
├── per_video_metrics.csv        # 1 row per video, 16 columns
├── aggregate_metrics.csv        # BY LANGUAGE / BY DURATION / OVERALL
├── baseline_comparison.csv       # B0 vs B1 per scope
└── evaluation_report.json       # Machine-readable paper summary
```

---

## Paper Reproduction

### Restoring original metrics

The paper's original evaluation data lives in `evaluation/run_001/`.
It was committed as evidence artifacts and can always be restored:

```bash
git checkout f2eb859 -- evaluation/run_001
```

### Regenerating charts

```bash
.venv\Scripts\python scripts/generate_charts.py
```

Charts are saved to `figures/`:
- `fig_rtf_comparison.png` — B0 vs B1 RTF boxplots by content type
- `fig_coverage.png` — 15s scene coverage bar chart

The script reads the run pointed to by `evaluation/paper_charts_run.txt`
(`run_001` for the published paper). To use a different run:

```bash
echo run_002 > evaluation/paper_charts_run.txt
```

### Running paper extensions

Post-hoc ablation and qualitative case studies (no API calls):

```bash
.venv\Scripts\python scripts/analyze_scene_selection_ablation.py
.venv\Scripts\python scripts/extract_scene_case_notes.py
```

Outputs go to `evaluation/paper_extensions/`.

---

## Test Structure

```
tests/
├── unit/
│   ├── test_config.py              # pydantic-settings validation
│   ├── test_database.py            # SQLite schema + CRUD (18 tests)
│   ├── test_descriptor.py          # Gemini prompt construction
│   ├── test_eval_modes.py          # Run modes + filter logic (26 tests)
│   ├── test_export_openapi_script.py
│   ├── test_exporters.py           # VTT, JSON, timeline
│   ├── test_generate_charts_script.py
│   ├── test_main_process_video.py
│   ├── test_summary.py
│   ├── test_verify_environment_script.py
│   └── test_word_grouper.py
├── integration/
│   ├── test_api.py                 # FastAPI TestClient
│   └── test_database_api.py        # SQLite-backed endpoints (11 tests)
└── evaluation/
    ├── _bootstrap.py               # Path helper
    ├── run_corpus_eval.py          # Main evaluation driver
    ├── service_smoke.py            # Whisper + Gemini + TTS verification
    ├── analyze_alignment.py
    ├── analyze_api.py
    ├── analyze_pipeline.py
    ├── analyze_scenes.py
    ├── benchmark_tts_latency.py
    ├── extract_stage_latencies.py
    ├── hf_probe*.py
    └── pipeline_output_smoke.py
```

---

## Typical Workflow

### 1. Verify environment

```bash
.venv\Scripts\python scripts/verify_environment.py --profile dev
```

### 2. Seed the database

```bash
.venv\Scripts\python scripts/seed_corpus.py
```

### 3. Smoke-test services

```bash
.venv\Scripts\python tests/evaluation/service_smoke.py
```

### 4. Run developer tests

```bash
.venv\Scripts\python -m pytest tests/unit tests/integration -q
```

### 5. Evaluate the corpus

```bash
# First run (creates run_001)
.venv\Scripts\python tests/evaluation/run_corpus_eval.py

# Later: fill gaps in the latest run
.venv\Scripts\python tests/evaluation/run_corpus_eval.py

# Force a completely fresh run
.venv\Scripts\python tests/evaluation/run_corpus_eval.py --force-new

# Only Russian long videos, resume latest
.venv\Scripts\python tests/evaluation/run_corpus_eval.py --lang ru --duration long
```

### 6. Generate paper artifacts

```bash
.venv\Scripts\python scripts/generate_charts.py
.venv\Scripts\python scripts/analyze_scene_selection_ablation.py
.venv\Scripts\python scripts/extract_scene_case_notes.py
```

---

## Corpus vs Upload Video Separation

| Aspect | Corpus | Upload |
|--------|--------|--------|
| **File location** | `input/{id}.mp4` | `input/_uploads/{job_id}/{filename}.mp4` |
| **SQLite `source`** | `corpus` | `upload` |
| **Job ID format** | `{vid_id}_B0` / `{vid_id}_B1` | `{filename}_{timestamp}_{uuid}` |
| **Evaluation** | Included in corpus runs | Not part of corpus evaluation |
| **API listing** | Appears in `/jobs` | Appears in `/jobs` |

Uploaded videos are tracked in SQLite with `source='upload'` and preserved
across API sessions. They do not interfere with corpus evaluation runs.
