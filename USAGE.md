# Prototype usage guide

This guide covers three ways to use Prototype: the command line (CLI),
the REST API, and the web interface.

## Before you start

Make sure you have:

1. Python virtual environment activated:

   ```bash
   .venv\Scripts\activate
   ```

2. A `.env` file with your scene-description service key (see `.env.example`).
3. FFmpeg installed and available in your PATH.
4. A video file placed in the `input/` folder.

---

## CLI (command line)

The CLI processes a video file and saves results to the `output/` folder.

### Basic usage

Run the pipeline on a video:

```bash
python main.py --video ./input/lecture.mp4 --language en
```

This always produces these core files in `output/<job_id>/`:

- `subtitles.vtt` -- segment-level WebVTT subtitles
- `timeline.json` -- full structured timeline (`language`, `detected_language`, `segments`, `words`)
- `job_meta.json` -- persisted processing metadata

Optional files:

- `scene_index.json` -- list of key scenes with text descriptions, only when the visual branch runs and scenes are found
- `summary.json` -- summary points and chapters, only when `scene_index.json` exists

### Options

| Flag              | Short | Description                            |
|-------------------|-------|----------------------------------------|
| `--video PATH`    | `-v`  | Path to input video (required)         |
| `--language CODE` | `-l`  | Language: `en` or `ru` (default: `en`) |
| `--no-visual`     |       | Skip scene detection and descriptions  |
| `--output DIR`    | `-o`  | Custom output folder                   |

### Examples

Process a Russian-language lecture:

```bash
python main.py --video ./input/lecture_ru.mp4 --language ru
```

Skip the visual pipeline (subtitles only, faster):

```bash
python main.py --video ./input/lecture.mp4 --no-visual
```

---

## REST API

The API server lets you process videos and request scene descriptions
over HTTP.

### Start the server

```bash
uvicorn api.server:app --port 8000
```

The server runs at `http://localhost:8000`. Interactive API docs
(Swagger UI) are available at `http://localhost:8000/docs`.

### Endpoints

#### Check server health

```bash
curl http://localhost:8000/health
```

Returns the current runtime configuration summary (speech model, device,
description mode, TTS provider).

#### Process a video

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"video_path": "./input/lecture.mp4", "language": "en"}'
```

This starts the processing in the background and returns a `job_id` and `status="queued"` immediately.
The call is **asynchronous** — it does not block. You can check the job status later in the `output/` directory or by listing jobs.

**Request body:**

| Field           | Type   | Default    | Description                  |
|-----------------|--------|------------|------------------------------|
| `video_path`    | string | (required) | Path to the video file       |
| `language`      | string | `"en"`     | Language code (`en` or `ru`) |
| `enable_visual` | bool   | `true`     | Enable scene detection       |

#### List processed jobs

```bash
curl http://localhost:8000/jobs
```

Returns a list of all processed videos with their `job_id` values.

#### Get scene index

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/scenes
```

Returns all indexed scenes with their timestamps and text descriptions.

#### Request a scene description (on-demand TTS)

```bash
curl -X POST http://localhost:8000/jobs/YOUR_JOB_ID/describe \
  -H "Content-Type: application/json" \
  -d '{"time": 30.0, "language": "en"}'
```

This finds the nearest scene to `time` (in seconds), generates TTS
audio for it, and returns:

- `scene_id` -- which scene was matched
- `description` -- the text description
- `tts_audio_url` -- URL to the audio file
- `tts_duration_sec` -- audio length in seconds

The TTS audio is cached after the first request. Subsequent requests
for the same scene return instantly from cache.

#### Download TTS audio

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/tts/4 --output scene.mp3
```

Returns the MP3 audio file for a specific scene (must be generated
first via `/describe`).

#### Download subtitles

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/subtitles --output subs.vtt
```

#### Stream video

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/video --output video.mp4
```

Serves the original video file for playback.

#### Get job metadata

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/meta
```

Returns job metadata: language, processing settings, word/scene counts,
timing statistics, and both requested/detected language values saved during pipeline execution.

#### Get video summary (ADHD/dyslexia)

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/summary
```

Returns a structured summary with 3-5 key points and 3-7 chapter
markers. Generated from scene descriptions. The result is
cached in `summary.json` after the first call.

#### Get word-level timestamps (karaoke subtitles)

```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID/words
```

Returns word-level timestamps grouped by segments. Used by the Web UI
for karaoke-style word-by-word subtitle highlighting. Each segment
contains an array of words with precise `start`/`end` times.

Important nuance:

- `timeline.json.words` and `/jobs/{job_id}/words` are the word-level source used by the player.
- `subtitles.vtt` is still exported in segment mode by default.
- Phoneme alignment is not active in the MVP unless MFA is explicitly enabled.

---

## Web UI

The web interface is the easiest way to use Prototype. It provides a
video player with on-demand scene descriptions and accessibility
features for users with ADHD, dyslexia, and vision/hearing impairments.

### Start the web UI

1. Start the API server:

   ```bash
   uvicorn api.server:app --port 8000
   ```

2. Open your browser and go to:

   ```http
   http://localhost:8000
   ```

### How to use it

1. Select a processed job from the dropdown at the top. The video and
   subtitles load automatically.
2. Play the video. Subtitles appear at the bottom.
3. Press the **Describe Scene** button (or press `D` on your keyboard)
   at any point. The system:
   - Pauses the video
   - Finds the nearest indexed scene
   - Generates TTS audio (or uses cache)
   - Plays the audio description
   - Resumes the video when the description finishes
4. Press `S` to stop a playing description early.

### Keyboard shortcuts

| Key     | Action                 |
|---------|------------------------|
| `D`     | Describe current scene |
| `S`     | Stop description audio |
| `Space` | Play / pause video     |

### Scene list

The bottom panel shows all indexed scenes. Click any scene to jump to
that point in the video and hear its description.

### Accessibility settings

The Web UI includes an **Accessibility Settings** panel with features
for different user groups:

#### ADHD / dyslexia

- **Word-by-Word subtitles** -- karaoke-style highlighting where the
  current word is shown in yellow (bold, glow), previous words fade,
  and upcoming words are dimmed. Toggle on/off in settings (enabled by
  default).
- **Summary tab** -- 3-5 key points about the video content. Helps
  understand structure before watching.
- **Chapters tab** -- 3-7 logical chapter markers for quick navigation.
- **Playback speed** -- 0.5x to 2x dropdown. Slowing down helps with
  information processing.
- **OpenDyslexic font** -- toggle for a dyslexia-friendly typeface with
  increased letter and word spacing.
- **Font size** -- A-/A/A+ buttons (70% to 160%, step 15%).
- **Wide line spacing** -- toggle for line-height 2.0.

#### Vision impairment

- **High contrast mode** -- black and white theme with increased
  contrast. Subtitle colors adapt automatically.
- **On-demand audio description** -- press `D` to hear a TTS
  description of the nearest scene.

#### Hearing impairment

- **Subtitles** -- standard segment-level WebVTT for playback.
- **Karaoke mode** -- visual word highlighting helps follow along with
  speech even without audio, using `/jobs/{job_id}/words`.

---

## Typical workflow

A typical session looks like this:

1. Place your video in `input/`.
2. Run the CLI to process it:

   ```bash
   python main.py --video ./input/my_lecture.mp4 --language en
   ```

3. Start the API server:

   ```bash
   uvicorn api.server:app --port 8000
   ```

4. Open `http://localhost:8000` in your browser.
5. Select your job from the dropdown, watch the video, and press `D`
   whenever you want a scene description.

---

## Building a paper evaluation corpus

For conference-grade evaluation, keep the corpus manifest and run outputs in
`evaluation/` and use the helper scripts in `scripts/`.

### Target corpus balance

- 24 videos total
- 12 EN and 12 RU
- 8 short, 8 medium, 8 long
- 6 per content type: `talking_head`, `slide-centric`, `screencast`,
  `practical_demo`
- Matrix formula: `2 languages × 3 duration buckets × 4 content types = 24`
- Source of truth: `evaluation/corpus_manifest.csv`

### Corpus workflow

1. Seed or refresh the bilingual manifest in `evaluation/corpus_manifest.csv`:

   ```bash
   python scripts/fetch_finevideo.py
   ```

2. Fill remaining slots from YouTube if needed:

   ```bash
   python scripts/build_youtube_corpus.py
   python scripts/fill_missing.py
   python scripts/fill_missing_last.py
   ```

3. Normalize semantic filenames and rebuild the manifest:

   ```bash
   python scripts/clean_and_rename_corpus.py
   python scripts/final_cleanup.py
   ```

4. Run the end-to-end evaluation:

   ```bash
   python tests/evaluation/run_corpus_eval.py
   ```

This produces versioned results under `evaluation/run_XXX/`.
