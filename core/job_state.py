"""Shared helpers for persisted job state and small JSON file updates."""

from __future__ import annotations

import json
import re
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUSES = {
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
}

JOB_META_FILENAME = "job_meta.json"
ARTIFACT_SUFFIXES = {".json", ".vtt", ".mp4", ".webm", ".mkv"}

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}
_NAMED_LOCKS: dict[tuple[str, str], threading.Lock] = {}


def utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp with stable formatting."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def create_job_id(video_stem: str) -> str:
    """Generate a collision-resistant job id while keeping the source stem visible."""
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", video_stem).strip("._-") or "job"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{safe_stem}_{timestamp}_{uuid.uuid4().hex[:8]}"


def job_meta_path(job_dir: Path) -> Path:
    return job_dir / JOB_META_FILENAME


def build_job_artifacts(job_dir: Path) -> dict[str, str]:
    """Return the user-facing artifact map for a job directory."""
    artifacts: dict[str, str] = {}
    if not job_dir.exists():
        return artifacts

    for file_path in sorted(job_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name == JOB_META_FILENAME:
            continue
        if file_path.suffix.lower() in ARTIFACT_SUFFIXES:
            artifacts[file_path.stem] = str(file_path)
    return artifacts


def get_named_lock(namespace: str, key: str) -> threading.Lock:
    """Return a stable lock for shared mutable state."""
    lock_key = (namespace, key)
    with _LOCKS_GUARD:
        lock = _NAMED_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            _NAMED_LOCKS[lock_key] = lock
        return lock


def _get_path_lock(path: Path) -> threading.Lock:
    normalized = str(path.resolve(strict=False))
    with _LOCKS_GUARD:
        lock = _PATH_LOCKS.get(normalized)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[normalized] = lock
        return lock


def _read_json_file_unlocked(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, payload: Any) -> None:
    """Atomically write JSON to disk with a per-path lock."""
    lock = _get_path_lock(path)
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)


def update_json_file(
    path: Path,
    updater: Callable[[Any], Any],
    *,
    default: Any | None = None,
) -> Any:
    """Read-update-write JSON atomically under a per-path lock."""
    lock = _get_path_lock(path)
    with lock:
        current = _read_json_file_unlocked(path, default=default)
        updated = updater(current)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
        temp_path.write_text(
            json.dumps(updated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)
        return updated


def read_job_meta(job_dir: Path) -> dict[str, Any]:
    """Read job metadata or return an empty dict when it is absent."""
    try:
        return _read_json_file_unlocked(job_meta_path(job_dir), default={})
    except json.JSONDecodeError:
        raise


def write_job_meta(job_dir: Path, payload: dict[str, Any]) -> None:
    write_json_file(job_meta_path(job_dir), payload)


def update_job_meta(job_dir: Path, **updates: Any) -> dict[str, Any]:
    """Merge updates into job metadata and persist them atomically."""

    def _merge(current: Any) -> dict[str, Any]:
        meta = dict(current or {})
        meta.update(updates)
        return meta

    return update_json_file(job_meta_path(job_dir), _merge, default={})


def infer_job_status(job_dir: Path, meta: dict[str, Any] | None = None) -> str:
    """Infer a reasonable job status for older outputs without persisted state."""
    meta = meta or {}
    status = meta.get("status")
    if status in JOB_STATUSES:
        return status

    artifacts = build_job_artifacts(job_dir)
    if "timeline" in artifacts or meta.get("processing_time_sec") is not None:
        return JOB_STATUS_COMPLETED
    if meta.get("error_message"):
        return JOB_STATUS_FAILED
    return JOB_STATUS_PROCESSING if job_dir.exists() else JOB_STATUS_FAILED
