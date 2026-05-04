# Testing

This guide explains how to run tests, collect metrics, and generate
reports for the Prototype system. The reports produce JSON files and
terminal output you can reference in your paper.

## Developer Tests (Atomic/Unit/Integration)

For code correctness, regression testing, and API contract verification, use the `pytest` suite. These tests are safe to run via `pytest tests` and do not require heavy GPU models or external service calls.

### Run all developer tests

```bash
# Make sure virtual environment is active
.venv\Scripts\python -m pytest tests/unit tests/integration
```

### Test structure

- `tests/unit/` — Independent component tests (logic, exporters, etc.).
- `tests/integration/` — FastAPI endpoint tests using `TestClient`.

These tests ensure that:

- ✅ **API contracts** match the OpenAPI schema.
- ✅ **Artifact formats** are consistent across the pipeline.
- ✅ **Edge cases** (like external video paths or ID mismatches) are handled.
- ✅ **Logic** (like word grouping) is numerically correct.

## Test scripts overview

All evaluation scripts are in the `tests/evaluation/` folder:

| Script                 | What it measures                        | Output file             |
| ---------------------- | --------------------------------------- | ----------------------- |
| `analyze_alignment.py` | Word timestamp accuracy, confidence     | `alignment_report.json` |
| `analyze_pipeline.py`  | Per-stage timing breakdown              | `pipeline_report.json`  |
| `analyze_scenes.py`    | Scene detection and description quality | `scenes_report.json`    |
| `analyze_api.py`       | API endpoint latency                    | `api_report.json`       |

Manual probes and benchmarks in the same folder are intentionally kept out
of pytest discovery:

- `hf_probe*.py` — ad-hoc Hugging Face dataset inspection
- `benchmark_tts_latency.py` — live TTS latency benchmark
- `pipeline_output_smoke.py` — real end-to-end pipeline smoke script

## Paper pre-submission checks (non-pytest)

These checks target manuscript readiness, not application runtime behavior.

### Sanity scan for manuscript leakage

```bash
python scripts/paper_sanity_check.py --paper-dir academic_paper
```

This script scans `.tex` sources for publication-risk markers such as:

- local paths and localhost URLs
- internal run/job IDs and repo paths
- draft markers (`TODO`, `TBD`, `FIXME`)
- placeholder citations
- log-style/internal runtime phrasing

### Reproducible PDF build guard

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_paper.ps1
```

This runs `pdflatex -> bibtex -> pdflatex -> pdflatex`, checks page count,
and fails when undefined citations/references remain in the final log.

### One-command preflight

```powershell
powershell -ExecutionPolicy Bypass -File scripts/pre_submission_check.ps1
```

This executes both the sanity scan and the PDF build checks.

### Paper extension diagnostics

These scripts regenerate the post-hoc scene-selection ablation and qualitative
case notes from saved B1 artifacts. They should not call hosted models or TTS.

```bash
python scripts/analyze_scene_selection_ablation.py
python scripts/extract_scene_case_notes.py
```

Expected outputs:

- `evaluation/paper_extensions/scene_selection_ablation_summary.csv`
- `evaluation/paper_extensions/scene_selection_ablation_per_video.csv`
- `evaluation/paper_extensions/qualitative_scene_cases.csv`
- `evaluation/paper_extensions/qualitative_scene_cases.md`

Run lint on the paper helper scripts:

```bash
ruff check scripts/analyze_scene_selection_ablation.py scripts/extract_scene_case_notes.py
```

---

## Step 1: process a video

Before running any analysis, you need at least one processed job.

```bash
python main.py --video ./input/test.mp4 --language en
```

Note the output directory (for example `output/test_1770867214`). You
will pass this path to the analysis scripts.

## Step 2: word alignment analysis

This script evaluates how accurately faster-whisper placed timestamps
on each word.

```bash
python tests/evaluation/analyze_alignment.py output/test_1770867214 --save
```

**What it reports:**

- Total words and segments transcribed
- Audio coverage (what percentage of audio has word timestamps)
- Word duration statistics (average, median, min, max)
- Confidence scores and their distribution
- Inter-word gaps and any timestamp overlaps
- List of low-confidence words (probability below 0.5)

**How to use in your paper:**

- The confidence distribution goes in the Results section to show ASR
  reliability
- Zero overlaps means timestamps are consistent (no timing conflicts)
- The low-confidence word list helps discuss limitations (proper nouns,
  brand names, and uncommon words tend to score lower)

## Step 3: pipeline performance

This script runs the full pipeline from scratch and measures each
stage individually.

```bash
python tests/evaluation/analyze_pipeline.py ./input/test.mp4
```

> This re-processes the video (takes a few minutes). It creates a new
> job in `output/` with a `pipeline_report.json` file.

**What it reports:**

- Per-stage timing: audio extraction, ASR, phoneme alignment, scene
  detection, description-service calls, export
- Percentage breakdown (which stage takes the most time)
- Realtime ratio (how many times slower than realtime the processing
  is)
- Hardware configuration (GPU vs CPU, model size, compute type)
- Scene filtering statistics (raw count vs filtered count)

**How to use in your paper:**

- The timing breakdown goes in Results as a table or bar chart
- Compare GPU vs CPU by running the script with each configuration
  (set `WHISPER_DEVICE` in `.env` or the shell environment)
- The realtime ratio shows practical viability (for example: "the system
  processes a 2-minute video in 45 seconds on GPU")

## Step 4: scene analysis

This script evaluates the quality of scene detection and scene
descriptions without re-processing the video.

```bash
python tests/evaluation/analyze_scenes.py output/test_1770867214 --save
```

**What it reports:**

- Scene count and temporal distribution
- Description length and word count statistics
- Content quality score (does the description reference screen text,
  use descriptive verbs, mention visual elements)
- Timeline visualization (shows scene distribution across the video)
- Coverage metric: what percentage of the video is within 15 seconds
  of an indexed scene

**How to use in your paper:**

- The timeline visualization shows scene distribution visually
- The "quoted screen text" percentage shows how often the description service
  successfully reads text from slides (relevant for educational video
  accessibility)
- Coverage percentage demonstrates that a user can press "describe"
  at almost any point and get a relevant description

## Step 5: API latency

This script tests all REST API endpoints and measures response time.

Start the server first, then run the test:

```bash
# Terminal 1: start the server
uvicorn api.server:app --port 8000

# Terminal 2: run the test
python tests/evaluation/analyze_api.py --save
```

You can also specify a particular job:

```bash
python tests/evaluation/analyze_api.py --job test_1770867214 --save
```

**What it reports:**

- Response time for each endpoint (health, jobs, scenes, describe,
  TTS audio, subtitles, video, web UI)
- Cold vs cached TTS latency (first request generates audio, second
  returns from cache)
- Pass/fail status for each endpoint
- Overall latency summary (average, min, max)

**How to use in your paper:**

- The cold vs cached TTS comparison demonstrates the caching strategy
- Overall latency shows the on-demand response time a user experiences
- Use the pass/fail count to state system reliability

---

## Comparing GPU vs CPU performance

To get both data points for your paper, run the pipeline benchmark
twice.

**GPU run** (default if CUDA is detected):

```bash
python tests/evaluation/analyze_pipeline.py ./input/test.mp4
```

**CPU run** (set overrides in `.env` or the shell temporarily):

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Then run the benchmark again with those overrides active:

```bash
python tests/evaluation/analyze_pipeline.py ./input/test.mp4
```

Remove or unset those overrides after testing to restore auto-detection.

---

## Running all tests at once

Process a video and run all analysis scripts in sequence:

```bash
python main.py --video ./input/test.mp4 --language en

# Find the job directory (most recent)
# Then run all analyses:
python tests/evaluation/analyze_alignment.py output/YOUR_JOB_ID --save
python tests/evaluation/analyze_scenes.py output/YOUR_JOB_ID --save

# For API tests, start the server first:
uvicorn api.server:app --port 8000
# In another terminal:
python tests/evaluation/analyze_api.py --job YOUR_JOB_ID --save
```

After running all scripts, your job folder contains:

```text
output/YOUR_JOB_ID/
├── subtitles.vtt
├── timeline.json
├── scene_index.json
├── alignment_report.json    <-- word alignment metrics
├── scenes_report.json       <-- scene quality metrics
├── api_report.json          <-- API latency metrics
└── tts_cache/               <-- generated TTS audio files
```

## Where each report helps in a paper

| Paper section | Report to reference                                         |
| ------------- | ----------------------------------------------------------- |
| Methodology   | `pipeline_report.json` (system configuration, stages)       |
| Methodology   | `alignment_report.json` (how ASR quality is measured)       |
| Results       | `pipeline_report.json` (timing breakdown, GPU vs CPU)       |
| Results       | `alignment_report.json` (confidence distribution, accuracy) |
| Results       | `scenes_report.json` (scene coverage, description quality)  |
| Results       | `api_report.json` (response latency, cold vs cached)        |
| Discussion    | `alignment_report.json` (low-confidence words, limitations) |
| Discussion    | `scenes_report.json` (content score, coverage gaps)         |
