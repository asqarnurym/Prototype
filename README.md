# Prototype — Accessible E-Learning Video Processor

A processing system for educational videos that improves the accessibility of e-learning content.

**Target audience:** students with ADHD, dyslexia, hearing impairments, and visual impairments.

## What Prototype does

Input: an educational video (`.mp4`) → output:

| Artifact           | Description                                                                                                      |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `subtitles.vtt`    | WebVTT subtitles by speech segments with precise segment-level timestamps                                        |
| `timeline.json`    | Structured timeline: pipeline language, detected language, segments, words, visual events                        |
| `scene_index.json` | Optional: an index of key scenes with text descriptions when the visual pipeline is enabled and scenes are found |
| `summary.json`     | Optional: video summary + chapter markers when `scene_index.json` was built                                      |
| `job_meta.json`    | Processing metadata (requested/detected language, settings, statistics)                                          |

Required artifacts:

- `subtitles.vtt`
- `timeline.json`
- `job_meta.json`

Optional artifacts:

- `scene_index.json` appears only when the visual pipeline is enabled and actually finds scenes
- `summary.json` appears only when there are scenes to summarize

### Operating mode

- **on-demand**: the video itself is not modified. The pipeline runs ASR + scene detection + text scene descriptions. The user presses a button and receives audio description for the nearest scene (TTS is generated on demand and cached).

---

## Quick start

### 1. System dependencies

#### FFmpeg (required)

FFmpeg is required for audio and video handling.

**Windows (winget):**

```bash
winget install Gyan.FFmpeg
```

**Check:**

```bash
ffmpeg -version
```

### 2. Exact Python version

```bash
py -3.12 -V
```

The project is pinned to **Python 3.12.10**. The version is recorded in `.python-version`.

### 3. Install Python dependencies

**Recommended on Windows:**

```powershell
.\scripts\bootstrap.ps1 -Dev
```

This creates `.venv`, installs dependencies from the lockfile, and runs the environment verification.

**Installation (`uv` — recommended):**

```powershell
uv sync               # runtime dependencies
uv sync --all-extras  # + dev/test/eval dependencies
uv run python scripts/verify_environment.py --profile dev
```

**Alternative (`pip`):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .                    # runtime
pip install -e ".[dev]"             # + dev/test/eval
python scripts/verify_environment.py --profile dev
```

Dependencies are defined in `pyproject.toml`:

- `[project.dependencies]` — runtime
- `[project.optional-dependencies.dev]` — test/eval/tooling
- `uv.lock` — lockfile (managed by uv)

> **For GPU acceleration**, faster-whisper requires CUDA Toolkit (12.x) and cuDNN.
> Without a GPU it still runs on CPU (slower, but functional).

### 4. Configure API keys

```powershell
Copy-Item .env.example .env
```

To use paid Gemini through Vertex AI, configure your Google Cloud project and credentials:

```env
# Paid Gemini via Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global

# Google Cloud ADC / service account JSON
GOOGLE_APPLICATION_CREDENTIALS=./path/to/service-account.json
```

If `TTS_PROVIDER` is not set, the application picks the provider automatically:

- `google` when `GOOGLE_APPLICATION_CREDENTIALS` points to an existing JSON key
- `edge` when credentials are not configured

The relative path in `GOOGLE_APPLICATION_CREDENTIALS` inside `.env` is resolved from the repository root. If you need to override the selection explicitly, set `TTS_PROVIDER=edge` or `TTS_PROVIDER=google`.

The Gemini integration uses the official `google-genai` SDK with Vertex AI (`vertexai=True`) instead of an AI Studio API key.

`global` is the safest default for Gemini on Vertex AI here because it works for this project, reduces regional availability issues, and Google recommends it when you don't need strict in-region ML processing.

The default Gemini model in this project is `gemini-3-flash-preview`, which is currently accessible for this Vertex AI project in `global`.

> Without Vertex AI project configuration, descriptions and summaries use fallback content. Without Google credentials, TTS uses free `edge-tts` (Microsoft).

### 5. Docker for the most reproducible environment

If you need the most consistent run across different machines, use Docker:

```bash
docker build -t prototype .
docker run --rm -it -p 8000:8000 --env-file .env prototype
```

This is the most reliable way to get the same environment across devices.

### 6. Update dependencies

```powershell
# Add a new dependency
uv add package-name              # runtime
uv add --dev package-name        # dev only

# Update everything to the latest compatible versions
uv lock --upgrade
uv sync --all-extras

# Verify
uv run python scripts/verify_environment.py --profile dev
```

---

## Usage

### CLI (command line)

```bash
# On-demand mode
python main.py --video ./input/lecture.mp4 --language en

# Subtitles and timeline only (without the visual pipeline)
python main.py --video ./input/lecture.mp4 --no-visual

# Russian language
python main.py --video ./input/lecture.mp4 --language ru
```

### REST API + Web UI

```bash
# Start the server
uvicorn api.server:app --port 8000

# Web UI: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

**API endpoints:**

| Method | Path                        | Description                                                           |
| ------ | --------------------------- | --------------------------------------------------------------------- |
| `POST` | `/process`                  | Process a video (ASR + scene index + summary)                         |
| `GET`  | `/jobs`                     | List processed videos                                                 |
| `GET`  | `/jobs/{id}/meta`           | Job metadata (language, settings, statistics)                         |
| `GET`  | `/jobs/{id}/scenes`         | List of scenes with descriptions                                      |
| `POST` | `/jobs/{id}/describe`       | On-demand TTS for a scene (lazy + cache)                              |
| `GET`  | `/jobs/{id}/tts/{scene_id}` | Cached TTS audio file                                                 |
| `GET`  | `/jobs/{id}/summary`        | Summary + chapter markers (ADHD/dyslexia support)                     |
| `GET`  | `/jobs/{id}/words`          | Word-level timestamps for karaoke highlighting and the interactive UI |
| `GET`  | `/jobs/{id}/video`          | Original video                                                        |
| `GET`  | `/jobs/{id}/subtitles`      | VTT subtitles by speech segments                                      |
| `GET`  | `/health`                   | Server status                                                         |
| `GET`  | `/`                         | Web UI                                                                |

---

## Corpus preparation for the paper

For conference evaluation, the corpus manifest and run results are stored in
`evaluation/`, and helper preparation scripts live in `scripts/`.

Step by step:

1. Collect/update the manifest: `python scripts/fetch_finevideo.py`
2. Extend the corpus from YouTube: `python scripts/build_youtube_corpus.py`
3. Normalize names and clean the corpus: `python scripts/clean_and_rename_corpus.py`
4. Final manifest rebuild: `python scripts/final_cleanup.py`
5. Run the evaluation: `python tests/evaluation/run_corpus_eval.py`

**Target corpus balance (Bilingual Multimodal Corpus):**

- **24 videos** (12 EN + 12 RU).
- Balanced across 3 duration buckets (short, medium, long): 8 videos per bucket.
- Balanced across 4 content types (6 videos per type): `talking_head`, `slide-centric`, `screencast`, `practical_demo`.
- Matrix formula: `2 languages × 3 durations × 4 content types = 24 videos`.
- Source of truth for corpus composition: `evaluation/corpus_manifest.csv`.

## Evaluation

Technical evaluation results are saved to `evaluation/` with automatic run versioning:

- `evaluation/run_XXX/`

Each report includes RTF (Real-Time Factor), ASR Confidence, and visual-scene coverage metrics (Coverage 15s).

---

## Project structure

```text
Prototype/
├── main.py                      # CLI + pipeline orchestrator
├── pyproject.toml               # Dependencies + tool config (ruff, pytest)
├── uv.lock                      # Lockfile (managed by uv)
├── .python-version              # Pinned Python version
├── .env.example                 # API key template
├── Dockerfile                   # Portable CPU environment
├── Prototype.md                 # Project reference document
├── README.md                    # ← you are here
│
├── core/
│   └── config.py                # Single config layer (models, APIs, paths)
│
├── pipeline/
│   ├── audio/
│   │   ├── extractor.py         # MP4 → WAV (ffmpeg)
│   │   ├── transcriber.py       # ASR via faster-whisper
│   │   └── aligner.py           # MFA phoneme alignment (stub)
│   ├── visual/
│   │   ├── scene_detect.py      # Scene-change detection (PySceneDetect)
│   │   ├── scene_indexer.py     # Scene filtering + indexing
│   │   ├── descriptor.py        # Scene descriptions
│   │   └── tts.py               # TTS (Google Cloud / edge-tts)
│   ├── exporters/
│   │   ├── vtt.py               # WebVTT subtitles
│   │   └── json_export.py       # timeline.json export
│   ├── summary.py               # Summary + chapter markers
│   └── word_grouper.py          # Group words into segments (karaoke)
│
├── api/
│   └── server.py                # FastAPI REST API
├── static/
│   └── index.html               # Web UI (video player + accessibility)
├── evaluation/                  # Corpus manifest and evaluation results
├── scripts/                     # Bootstrap, environment verification, corpus prep
│
├── input/                       # Input videos
├── output/                      # Output artifacts
└── temp/                        # Intermediate files
```

---

## Technical stack

| Component       | Technology                  | Purpose                                           |
| --------------- | --------------------------- | ------------------------------------------------- |
| ASR             | faster-whisper              | Speech recognition + word-level timestamps        |
| Scene detection | PySceneDetect               | Find key frames                                   |
| Description     | Hosted description service  | Text descriptions of scenes and on-screen content |
| TTS             | Google Cloud TTS / edge-tts | Spoken descriptions (on-demand, lazy + cache)     |
| Video           | FFmpeg                      | Audio extraction and media processing             |
| API             | FastAPI + uvicorn           | REST API + Web UI                                 |
| Format          | WebVTT, JSON                | Subtitles and timeline                            |

Current speech-alignment level:

- `timeline.json.words` and `/jobs/{id}/words` use Whisper word-level timestamps.
- `subtitles.vtt` is exported as segment-level WebVTT by default.
- `phonemes` remain empty when MFA is not enabled: phoneme alignment is not currently an active part of the MVP.

---

## Accessibility features (Web UI)

### For ADHD / dyslexia

| Feature               | Description                                                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Karaoke subtitles** | Word-by-word highlighting: the current word is yellow, previous words fade, upcoming words are muted. ~60fps via `requestAnimationFrame`. |
| **Video summary**     | 3-5 key content points. Helps the user understand the structure before watching.                                                          |
| **Chapter markers**   | Navigation across 3-7 logical video chapters.                                                                                             |
| **Playback speed**    | 0.5x–2x. Slower playback can help with information processing.                                                                            |
| **OpenDyslexic font** | Toggle for a dyslexia-friendly font with increased letter/word spacing.                                                                   |
| **Font size**         | A-/A/A+ (70%–160%, 15% step).                                                                                                             |
| **Wide line spacing** | Toggle for `line-height: 2.0`.                                                                                                            |

### For low-vision users

| Feature               | Description                                                            |
| --------------------- | ---------------------------------------------------------------------- |
| **High contrast**     | Black-and-white mode with increased contrast.                          |
| **Audio description** | On-demand TTS scene description triggered by a button press (key `D`). |

### For hard-of-hearing users

| Feature          | Description                                                      |
| ---------------- | ---------------------------------------------------------------- |
| **Subtitles**    | WebVTT by speech segments for the standard subtitle mode.        |
| **Karaoke mode** | Visual highlighting of the current word helps follow the speech. |

### ARIA accessibility

- `aria-live` regions for screen readers
- `role`, `tabindex`, `focus-visible` for keyboard navigation
- Keys: `D` — scene description, `S` — stop, `Space` — pause

---

## Hardware requirements

- **GPU**: NVIDIA with CUDA (an RTX 3050 4GB is sufficient). Without a GPU, CPU fallback is used.
- **RAM**: minimum 8 GB
- **Python**: 3.12.10
- **OS**: Windows 10/11 for native setup, Docker for the most portable run
