"""FastAPI application for Prototype.

Endpoints:
    POST /process                 - preprocess a video into persisted artifacts
    GET  /health                  - report current runtime configuration
    GET  /jobs                    - list persisted jobs from output/
    GET  /jobs/{job_id}/scenes    - return scene_index.json content
    POST /jobs/{job_id}/describe  - synthesize on-demand TTS for the nearest scene

Run with:
    uvicorn api.server:app --reload --port 8000
"""

import asyncio
import json
import logging
import mimetypes
import re
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from core.config import settings
from core.job_state import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_QUEUED,
    build_job_artifacts,
    create_job_id,
    infer_job_status,
    read_job_meta,
    update_job_meta,
    update_json_file,
    utc_now_iso,
)
from core.logging_config import setup_logging
from main import process_video
from pipeline.summary import generate_summary
from pipeline.visual.scene_indexer import find_nearest_scene, load_scene_index
from pipeline.visual.tts import synthesize_speech_async
from pipeline.word_grouper import group_words_by_segments

setup_logging()

logger = logging.getLogger(__name__)


def _requested_server_port(argv: list[str]) -> int:
    """Return the requested uvicorn port, defaulting to 8000."""
    for index, arg in enumerate(argv):
        if arg == "--port" and index + 1 < len(argv):
            try:
                return int(argv[index + 1])
            except ValueError:
                return 8000
        if arg.startswith("--port="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                return 8000
    return 8000


def _exit_if_requested_port_is_unavailable() -> None:
    """Abort import early when the requested local server port is already occupied."""
    if "pytest" in sys.modules:
        return

    port = _requested_server_port(sys.argv)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            message = (
                f"\n{'=' * 78}\n"
                f"ERROR: Port {port} is already in use by another process.\n"
                "Please stop the existing process before starting the server.\n"
                f"{'=' * 78}\n"
            )
            print(f"\033[91m{message}\033[0m", file=sys.stderr)
            raise SystemExit(1)


_exit_if_requested_port_is_unavailable()

# API version declared in one place.
API_VERSION = "0.2.0"
VIDEO_MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}
VIDEO_OPENAPI_CONTENT = {media_type: {} for media_type in dict.fromkeys(VIDEO_MEDIA_TYPES.values())}
_ASYNC_LOCKS_GUARD = threading.Lock()
_ASYNC_TTS_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}

# ── Suppress noisy Windows connection resets ──────────────────────
# Browsers use Range requests while buffering video and may drop the
# connection during seeks. Windows ProactorEventLoop logs that as an
# error even though the request flow is otherwise healthy.
_orig_connection_lost = None


def _suppress_connection_reset():
    """Suppress WinError 10054 noise in the Windows Proactor event loop."""
    import sys
    from contextlib import suppress

    if sys.platform != "win32":
        return

    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport

        global _orig_connection_lost
        _orig_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def _silent_connection_lost(self, exc):
            with suppress(ConnectionResetError, OSError):
                _orig_connection_lost(self, exc)

        _ProactorBasePipeTransport._call_connection_lost = _silent_connection_lost
    except (ImportError, AttributeError):
        pass


_suppress_connection_reset()

# Thread pool for blocking work such as ASR and FFmpeg.
_executor = ThreadPoolExecutor(max_workers=2)

# ── FastAPI initialization ────────────────────────────────────────
app = FastAPI(
    title="Prototype API",
    description=(
        "API for preprocessing educational videos into accessibility artifacts. "
        "Scene descriptions are generated during preprocessing, while TTS audio "
        "is synthesized on demand when the user requests it."
    ),
    version=API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────


class ProcessVideoRequest(BaseModel):
    """Request body for starting asynchronous video preprocessing."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_path": "./input/lecture.mp4",
                "language": "en",
                "enable_visual": True,
            }
        }
    )

    video_path: str = Field(..., description="Path to the input video file")
    language: str = Field(default="en", description="Requested output language (en/ru)")
    enable_visual: bool = Field(default=True, description="Enable the visual pipeline")


class ProcessVideoResponse(BaseModel):
    """Immediate response returned after a job is queued."""

    job_id: str
    status: str
    processing_time_sec: float | None = None
    artifacts: dict[str, str | None]


class DescribeRequest(BaseModel):
    """Request body for on-demand scene description playback."""

    time: float = Field(..., description="Current playback time in seconds")
    language: str = Field(default="en", description="TTS language (en/ru)")


class DescribeResponse(BaseModel):
    """Response payload for the nearest described scene and cached TTS URL."""

    scene_id: int
    time: float
    description: str
    tts_audio_url: str | None = None
    tts_duration_sec: float | None = None


def _sanitize_uploaded_filename(filename: str | None) -> str:
    candidate = Path((filename or "uploaded-video.mp4").strip()).name
    return candidate or "uploaded-video.mp4"


def _queue_process_job(
    *,
    video: Path,
    language: str,
    enable_visual: bool,
    background_tasks: BackgroundTasks,
) -> ProcessVideoResponse:
    if not video.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {video}",
        )

    if language not in settings.supported_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{language}' is not supported. Available: {settings.supported_languages}",
        )

    job_id = create_job_id(video.stem)
    job_dir = _job_dir(job_id)
    output_dir = str(job_dir)
    update_job_meta(
        job_dir,
        **_build_queued_job_meta(
            job_id=job_id,
            video=video,
            language=language,
            enable_visual=enable_visual,
        ),
    )

    try:
        background_tasks.add_task(
            _run_process_job,
            job_id=job_id,
            video_path=str(video),
            language=language,
            enable_visual=enable_visual,
            output_dir=output_dir,
        )

        return ProcessVideoResponse(
            job_id=job_id,
            status=JOB_STATUS_QUEUED,
            processing_time_sec=None,
            artifacts={},
        )
    except Exception as exc:
        logger.error("Failed to queue job: %s", exc, exc_info=True)
        _finalize_failed_job(job_dir, exc, elapsed=0.0)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue job: {exc}",
        ) from exc


def _detect_media_type(file_path: Path) -> str:
    """Return a stable media type for an artifact based on its suffix."""
    suffix = file_path.suffix.lower()
    if suffix in VIDEO_MEDIA_TYPES:
        return VIDEO_MEDIA_TYPES[suffix]

    guessed_type, _ = mimetypes.guess_type(str(file_path))
    return guessed_type or "application/octet-stream"


def _video_file_response(video_path: Path) -> FileResponse:
    """Build a FileResponse whose media type matches the real file."""
    return FileResponse(
        path=str(video_path),
        media_type=_detect_media_type(video_path),
        filename=video_path.name,
    )


def _job_dir(job_id: str) -> Path:
    return settings.output_dir / job_id


def _safe_read_job_meta(job_dir: Path) -> dict:
    try:
        return read_job_meta(job_dir)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to read job_meta.json for %s: %s", job_dir.name, exc)
        return {}


def _get_async_lock(namespace: str, key: str) -> asyncio.Lock:
    lock_key = (namespace, key)
    with _ASYNC_LOCKS_GUARD:
        lock = _ASYNC_TTS_LOCKS.get(lock_key)
        if lock is None:
            lock = asyncio.Lock()
            _ASYNC_TTS_LOCKS[lock_key] = lock
        return lock


def _legacy_tts_cache_path(job_id: str, scene_id: int) -> Path:
    return _job_dir(job_id) / "tts_cache" / f"scene_{scene_id:04d}.mp3"


def _tts_cache_path(job_id: str, scene_id: int, language: str) -> Path:
    return _job_dir(job_id) / "tts_cache" / f"scene_{scene_id:04d}_{language}.mp3"


def _safe_read_timeline(job_dir: Path) -> dict:
    timeline_path = job_dir / "timeline.json"
    if timeline_path.exists():
        try:
            return json.loads(timeline_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read timeline.json for %s: %s", job_dir.name, exc)
    return {}


def _resolve_job_languages(
    job_dir: Path,
    *,
    meta: dict | None = None,
    timeline: dict | None = None,
) -> tuple[str, str]:
    """
    Resolve the user-facing pipeline language and the ASR-detected language.

    `language` stays stable as the requested/output language used by UI/TTS.
    `detected_language` preserves what Whisper reported. Older jobs without an
    explicit detected-language field fall back to timeline.language.
    """
    meta = meta or {}
    timeline = timeline if timeline is not None else _safe_read_timeline(job_dir)

    requested_language = (
        meta.get("language")
        or meta.get("requested_language")
        or timeline.get("language")
        or meta.get("detected_language")
        or "en"
    )
    detected_language = (
        meta.get("detected_language")
        or timeline.get("detected_language")
        or timeline.get("language")
        or requested_language
    )
    return requested_language, detected_language


def _job_video_stem_candidates(job_id: str) -> list[str]:
    candidates = [job_id]
    parts = job_id.split("_")
    if len(parts) >= 2:
        candidates.append("_".join(parts[:-1]))
    if len(parts) >= 3 and re.fullmatch(r"\d{8}T\d{6}\d{6}Z", parts[-2]):
        candidates.append("_".join(parts[:-2]))
    return [
        candidate
        for i, candidate in enumerate(candidates)
        if candidate and candidate not in candidates[:i]
    ]


def _build_queued_job_meta(
    *,
    job_id: str,
    video: Path,
    language: str,
    enable_visual: bool,
) -> dict:
    created_at = utc_now_iso()
    runtime_snapshot = settings.runtime_snapshot()
    return {
        "job_id": job_id,
        "video_file": video.name,
        "video_path": str(video.resolve()),
        "language": language,
        "requested_language": language,
        "detected_language": None,
        "enable_visual": enable_visual,
        "status": JOB_STATUS_QUEUED,
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "processing_time_sec": None,
        "scenes_count": 0,
        "whisper_model": settings.whisper_model_size,
        "whisper_device": settings.whisper_device,
        "description_mode": settings.description_mode,
        "description_runtime": runtime_snapshot["description"],
        "tts_provider": settings.tts_provider,
        "tts_runtime": runtime_snapshot["tts"],
        "artifacts": {},
        "error_type": None,
        "error_message": None,
    }


def _finalize_successful_job(job_dir: Path, result: dict) -> None:
    # Use the on-disk artifact map as the single source of truth so CLI/API/meta
    # expose the same optional files when they actually exist.
    artifacts = build_job_artifacts(job_dir)
    update_job_meta(
        job_dir,
        status=JOB_STATUS_COMPLETED,
        completed_at=utc_now_iso(),
        processing_time_sec=result.get("processing_time_sec"),
        artifacts=artifacts,
        error_type=None,
        error_message=None,
    )


def _finalize_failed_job(job_dir: Path, exc: Exception, elapsed: float | None) -> None:
    update_job_meta(
        job_dir,
        status=JOB_STATUS_FAILED,
        completed_at=utc_now_iso(),
        processing_time_sec=round(elapsed, 2) if elapsed is not None else None,
        artifacts=build_job_artifacts(job_dir),
        error_type=exc.__class__.__name__,
        error_message=str(exc),
    )


def _run_process_job(
    *,
    job_id: str,
    video_path: str,
    language: str,
    enable_visual: bool,
    output_dir: str,
) -> None:
    job_dir = Path(output_dir)
    started_perf = time.perf_counter()
    update_job_meta(
        job_dir,
        status=JOB_STATUS_PROCESSING,
        started_at=utc_now_iso(),
        error_type=None,
        error_message=None,
    )

    try:
        result = process_video(
            video_path=video_path,
            language=language,
            enable_visual=enable_visual,
            output_dir=output_dir,
            job_id=job_id,
        )
        _finalize_successful_job(job_dir, result)
    except Exception as exc:
        logger.error("Background processing failed for job %s: %s", job_id, exc, exc_info=True)
        _finalize_failed_job(job_dir, exc, time.perf_counter() - started_perf)


def _artifact_missing_exception(job_id: str, artifact_label: str, detail: str) -> HTTPException:
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        return HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    meta = _safe_read_job_meta(job_dir)
    status = infer_job_status(job_dir, meta)
    if status in {JOB_STATUS_QUEUED, JOB_STATUS_PROCESSING}:
        return HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is still {status}; {artifact_label} is not ready yet.",
        )
    if status == JOB_STATUS_FAILED:
        error_message = meta.get("error_message") or "unknown error"
        return HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' failed: {error_message}",
        )
    return HTTPException(status_code=404, detail=detail)


def _mark_scene_tts_cached(scene_index: list[dict], scene_id: int, language: str) -> list[dict]:
    for scene in scene_index:
        if scene.get("scene_id") != scene_id:
            continue
        cached_languages = sorted(set(scene.get("tts_cached_languages", [])) | {language})
        scene["tts_cached_languages"] = cached_languages
        scene["tts_cached"] = True
        break
    return scene_index


# ── Endpoints ────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Return a lightweight health response plus non-secret runtime settings."""
    return {
        "status": "ok",
        "version": API_VERSION,
        "whisper_model": settings.whisper_model_size,
        "device": settings.whisper_device,
        "description_mode": settings.description_mode,
        "tts_provider": settings.tts_provider,
        "runtime": settings.runtime_snapshot(),
        "supported_languages": settings.supported_languages,
    }


@app.post("/process", response_model=ProcessVideoResponse)
async def process_video_endpoint(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """Queue asynchronous preprocessing for a source video.

    The background job performs ASR and optional visual indexing, but it does
    not synthesize TTS. Audio description is still generated lazily through
    ``POST /jobs/{job_id}/describe``.
    """
    return _queue_process_job(
        video=Path(request.video_path),
        language=request.language,
        enable_visual=request.enable_visual,
        background_tasks=background_tasks,
    )


@app.post("/process-upload", response_model=ProcessVideoResponse)
async def process_uploaded_video(
    request: Request,
    background_tasks: BackgroundTasks,
    language: str = "en",
    enable_visual: bool = True,
):
    """Accept a literal uploaded video file and queue the standard preprocessing job."""
    filename = _sanitize_uploaded_filename(request.headers.get("X-Upload-Filename"))
    file_bytes = await request.body()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    upload_dir = settings.input_dir / "_uploads" / create_job_id(Path(filename).stem)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / filename
    target_path.write_bytes(file_bytes)

    return _queue_process_job(
        video=target_path,
        language=language,
        enable_visual=enable_visual,
        background_tasks=background_tasks,
    )


@app.get("/jobs")
async def list_jobs():
    """List persisted jobs together with their current metadata snapshot."""
    output_dir = settings.output_dir
    if not output_dir.exists():
        return {"jobs": []}

    jobs = []
    for job_dir in sorted(output_dir.iterdir()):
        if job_dir.is_dir():
            artifacts = build_job_artifacts(job_dir)
            meta = _safe_read_job_meta(job_dir)
            language, detected_language = _resolve_job_languages(job_dir, meta=meta)
            status = infer_job_status(job_dir, meta)

            jobs.append(
                {
                    "job_id": job_dir.name,
                    "language": language,
                    "requested_language": meta.get("requested_language", language),
                    "detected_language": detected_language,
                    "video_file": meta.get("video_file", ""),
                    "scenes_count": meta.get("scenes_count", 0),
                    "status": status,
                    "processing_time_sec": meta.get("processing_time_sec"),
                    "created_at": meta.get("created_at"),
                    "completed_at": meta.get("completed_at"),
                    "artifacts": artifacts,
                    "error_message": meta.get("error_message"),
                }
            )

    return {"jobs": jobs}


@app.get("/jobs/{job_id}/meta")
async def get_job_meta(job_id: str):
    """Return persisted metadata for a single job."""
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    try:
        meta = read_job_meta(job_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not meta:
        meta = {"job_id": job_id}

    language, detected_language = _resolve_job_languages(job_dir, meta=meta)
    meta["job_id"] = job_id
    meta["language"] = language
    meta.setdefault("requested_language", language)
    meta["detected_language"] = detected_language
    meta.setdefault("status", infer_job_status(job_dir, meta))
    meta.setdefault("artifacts", build_job_artifacts(job_dir))
    return meta


@app.get("/jobs/{job_id}/scenes")
async def get_scenes(job_id: str):
    """Return indexed scene descriptions for a job.

    The UI uses this list to show which scene descriptions are available for
    on-demand audio playback.
    """
    scene_index_path = _job_dir(job_id) / "scene_index.json"

    if not scene_index_path.exists():
        raise _artifact_missing_exception(
            job_id,
            "scene index",
            detail=f"Scene index not found for job '{job_id}'. "
            f"Run video processing with enable_visual=true.",
        )

    try:
        scene_index = load_scene_index(str(scene_index_path))
        return {"job_id": job_id, "scenes": scene_index}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/jobs/{job_id}/describe", response_model=DescribeResponse)
async def describe_scene(job_id: str, request: DescribeRequest):
    """Generate or reuse TTS for the nearest indexed scene.

    Flow:
    1. Find the nearest scene to the requested playback time.
    2. Reuse cached audio when it already exists.
    3. Otherwise synthesize new audio and store it under the job directory.
    """
    if request.language not in settings.supported_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{request.language}' is not supported. "
            f"Available: {settings.supported_languages}",
        )

    scene_index_path = _job_dir(job_id) / "scene_index.json"

    if not scene_index_path.exists():
        raise _artifact_missing_exception(
            job_id,
            "scene index",
            detail=f"Scene index not found for job '{job_id}'.",
        )

    try:
        scene_index = load_scene_index(str(scene_index_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Resolve the nearest described scene for the requested playback time.
    nearest = find_nearest_scene(scene_index, request.time)

    if nearest is None:
        raise HTTPException(
            status_code=404,
            detail=f"No scene found within 30 seconds of time={request.time}",
        )

    scene_id = nearest["scene_id"]
    description = nearest["description"]

    # Keep cache entries scoped by job, scene, and language.
    tts_dir = _job_dir(job_id) / "tts_cache"
    tts_dir.mkdir(parents=True, exist_ok=True)
    tts_path = _tts_cache_path(job_id, scene_id, request.language)
    legacy_tts_path = _legacy_tts_cache_path(job_id, scene_id)
    tts_lock = _get_async_lock("tts-cache", f"{job_id}:{scene_id}:{request.language}")

    async with tts_lock:
        cache_path = tts_path
        if not cache_path.exists() and request.language == "en" and legacy_tts_path.exists():
            cache_path = legacy_tts_path

        if cache_path.exists():
            # Reuse cached audio when available.
            from pipeline.visual.tts import _get_audio_duration

            duration = _get_audio_duration(str(cache_path))
            logger.info("Reused cached TTS for scene %s, language %s", scene_id, request.language)
        else:
            # Generate fresh audio when the cache is empty.
            logger.info(
                "Generating on-demand TTS for scene %s, language %s...",
                scene_id,
                request.language,
            )
            tts_result = await synthesize_speech_async(description, str(tts_path), request.language)
            duration = tts_result["duration_sec"]

        update_json_file(
            scene_index_path,
            lambda current: _mark_scene_tts_cached(current, scene_id, request.language),
            default=[],
        )

    return DescribeResponse(
        scene_id=scene_id,
        time=nearest["time"],
        description=description,
        tts_audio_url=f"/jobs/{job_id}/tts/{scene_id}?language={request.language}",
        tts_duration_sec=duration,
    )


@app.get(
    "/jobs/{job_id}/tts/{scene_id}",
    responses={200: {"content": {"audio/mpeg": {}}}},
    response_class=FileResponse,
)
async def get_tts_audio(job_id: str, scene_id: int, language: str = "en"):
    """Serve a cached TTS audio file for a scene."""
    tts_path = _tts_cache_path(job_id, scene_id, language)
    legacy_tts_path = _legacy_tts_cache_path(job_id, scene_id)
    cache_path = tts_path
    if not cache_path.exists() and language == "en" and legacy_tts_path.exists():
        cache_path = legacy_tts_path

    if not cache_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"TTS for scene {scene_id} has not been generated yet. "
            f"Call POST /jobs/{job_id}/describe first",
        )

    return FileResponse(
        path=str(cache_path),
        media_type="audio/mpeg",
        filename=cache_path.name,
    )


# ── Legacy compatibility endpoint ────────────────────────────────


@app.post("/process_video", response_model=ProcessVideoResponse, deprecated=True)
async def process_video_legacy(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """Deprecated endpoint. Use POST /process instead."""
    return await process_video_endpoint(request, background_tasks)


# ── Artifact delivery endpoints ──────────────────────────────────


@app.get("/jobs/{job_id}/summary")
async def get_summary(job_id: str):
    """Return a cached summary or generate one from scene descriptions.

    The summary is derived from ``scene_index.json`` and cached as
    ``summary.json`` inside the job directory.
    """
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    # Reuse the cached summary when it already exists.
    summary_path = job_dir / "summary.json"
    if summary_path.exists():
        try:
            cached_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not _summary_cache_is_stale(cached_summary):
                return cached_summary
        except Exception as e:
            logger.warning(f"Failed to read summary.json for {job_id}: {e}")

    # Scene descriptions are the input to summary generation.
    scene_index_path = job_dir / "scene_index.json"
    if not scene_index_path.exists():
        raise _artifact_missing_exception(
            job_id,
            "summary",
            detail="Scene index not found. Process the video first.",
        )

    scenes = json.loads(scene_index_path.read_text(encoding="utf-8"))

    # Use persisted job metadata to pick the user-facing language.
    meta = _safe_read_job_meta(job_dir)
    language, _ = _resolve_job_languages(job_dir, meta=meta)
    timeline = _safe_read_timeline(job_dir)
    transcript_segments = [segment.get("text", "") for segment in timeline.get("segments", [])]

    # Run the shared summary module in a worker thread.
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor,
        lambda: generate_summary(
            scenes=scenes,
            job_id=job_id,
            language=language,
            output_path=str(summary_path),
            transcript_segments=transcript_segments,
        ),
    )

    return result


def _summary_cache_is_stale(summary_payload: dict) -> bool:
    """Detect cached summary payloads that should be regenerated."""
    if summary_payload.get("summary_version", 0) < 3:
        return True

    summary_points = summary_payload.get("summary_points") or []
    if not summary_points:
        return True

    placeholder_markers = (
        "summary unavailable",
        "summary generation failed",
        "no gemini api key",
        "external summarization model",
    )

    return all(
        any(marker in str(point).lower() for marker in placeholder_markers)
        for point in summary_points
    )


@app.get(
    "/jobs/{job_id}/video",
    responses={200: {"content": VIDEO_OPENAPI_CONTENT}},
    response_class=FileResponse,
)
async def get_video(job_id: str):
    """Serve the original source video for playback."""
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    # Prefer the recorded absolute source path when it is still valid.
    meta = _safe_read_job_meta(job_dir)

    recorded_path = meta.get("video_path")
    if recorded_path and Path(recorded_path).exists():
        return _video_file_response(Path(recorded_path))

    video_filename = meta.get("video_file")
    if video_filename:
        input_video_path = settings.input_dir / video_filename
        if input_video_path.exists():
            return _video_file_response(input_video_path)

    # Fall back to input_dir using both newer and legacy job-id patterns.
    for video_stem in _job_video_stem_candidates(job_id):
        for ext in (".mp4", ".webm", ".mkv"):
            video_path = settings.input_dir / f"{video_stem}{ext}"
            if video_path.exists():
                return _video_file_response(video_path)

    raise HTTPException(status_code=404, detail=f"Video for job '{job_id}' not found.")


@app.get(
    "/jobs/{job_id}/subtitles",
    responses={200: {"content": {"text/vtt": {}}}},
    response_class=FileResponse,
)
async def get_subtitles(job_id: str):
    """Serve the exported VTT subtitles for a job."""
    vtt_path = _job_dir(job_id) / "subtitles.vtt"
    if not vtt_path.exists():
        raise _artifact_missing_exception(
            job_id,
            "subtitles",
            detail="Subtitles not found.",
        )
    return FileResponse(
        path=str(vtt_path),
        media_type="text/vtt",
        filename="subtitles.vtt",
    )


@app.get("/jobs/{job_id}/words")
async def get_words(job_id: str):
    """Return word-level timings from ``timeline.json``.

    The UI uses this endpoint for karaoke-style highlighting. Words are grouped
    back into display segments before they are returned.
    """
    timeline_path = _job_dir(job_id) / "timeline.json"
    if not timeline_path.exists():
        raise _artifact_missing_exception(
            job_id,
            "timeline",
            detail="Timeline not found.",
        )

    try:
        tl = json.loads(timeline_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    meta = _safe_read_job_meta(_job_dir(job_id))
    language, detected_language = _resolve_job_languages(
        _job_dir(job_id),
        meta=meta,
        timeline=tl,
    )
    words = tl.get("words", [])
    segments = tl.get("segments", [])

    # Re-group words into their display segments with the shared midpoint matcher.
    grouped = group_words_by_segments(words, segments)

    return {
        "job_id": job_id,
        "language": language,
        "detected_language": detected_language,
        "segments": grouped,
        "total_words": len(words),
    }


# ── Web UI endpoints ──────────────────────────────────────────────


@app.get("/favicon.ico")
async def favicon():
    """Return an empty favicon response to avoid browser 404 noise."""
    return Response(content=b"", media_type="image/x-icon")


@app.get("/")
async def serve_ui():
    """Serve the minimal bundled web UI."""
    ui_path = Path(__file__).parent.parent / "static" / "index.html"
    if ui_path.exists():
        return FileResponse(str(ui_path), media_type="text/html")
    return HTMLResponse("<h1>Prototype API</h1><p>UI not found. Visit /docs for API.</p>")
