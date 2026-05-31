"""
core/database.py — SQLite persistence layer.
Replaces scattered file-based state (job_meta.json, per_video_metrics.csv, run dirs)
with a single structured database.  Writes are always mirrored to JSON/CSV on disk
so that existing scripts and paper tooling keep working without refactors.

Tables: videos, jobs, artifacts, scenes, tts_cache, evaluation_runs, evaluation_metrics.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "prototype.db"

_ENGINE_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    id               TEXT PRIMARY KEY,
    source           TEXT NOT NULL DEFAULT 'corpus',
    filename         TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    language         TEXT,
    duration_bucket  TEXT,
    content_type     TEXT,
    video_duration_sec REAL,
    checksum         TEXT,
    uploaded_at      TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id               TEXT PRIMARY KEY,
    video_id         TEXT NOT NULL REFERENCES videos(id),
    config           TEXT NOT NULL DEFAULT 'B1',
    status           TEXT NOT NULL DEFAULT 'queued',
    processing_time_sec REAL,
    error_message    TEXT,
    error_type       TEXT,
    language         TEXT,
    detected_language TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    completed_at     TEXT,
    git_commit       TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    job_id   TEXT NOT NULL REFERENCES jobs(id),
    type     TEXT NOT NULL,
    file_path TEXT NOT NULL,
    PRIMARY KEY (job_id, type)
);

CREATE TABLE IF NOT EXISTS scenes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id             TEXT NOT NULL REFERENCES jobs(id),
    scene_id           INTEGER NOT NULL,
    time_sec           REAL NOT NULL,
    description        TEXT,
    description_length INTEGER,
    has_screen_text    INTEGER DEFAULT 0,
    content_score      INTEGER DEFAULT 0,
    tts_cached         INTEGER DEFAULT 0,
    UNIQUE(job_id, scene_id)
);

CREATE TABLE IF NOT EXISTS tts_cache (
    scene_id    INTEGER NOT NULL REFERENCES scenes(id),
    language    TEXT NOT NULL,
    audio_path  TEXT,
    duration_sec REAL,
    cached_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (scene_id, language)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name       TEXT NOT NULL UNIQUE,
    config_hash    TEXT,
    total_videos   INTEGER DEFAULT 0,
    completed_videos INTEGER DEFAULT 0,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evaluation_metrics (
    run_id             INTEGER NOT NULL REFERENCES evaluation_runs(id),
    video_id           TEXT NOT NULL,
    language           TEXT,
    duration_bucket    TEXT,
    content_type       TEXT,
    video_duration_sec REAL,
    b0_asr_sec         REAL,
    b0_rtf             REAL,
    b1_total_sec       REAL,
    b1_rtf             REAL,
    asr_confidence     REAL,
    low_conf_ratio     REAL,
    overlap_ratio      REAL,
    scene_count        INTEGER,
    scene_density_per_min REAL,
    tail_uncovered_sec REAL,
    coverage_15s_pct   REAL,
    PRIMARY KEY (run_id, video_id)
);
"""

_MIGRATIONS = [
    "ALTER TABLE evaluation_metrics ADD COLUMN avg_content_score REAL",
    "ALTER TABLE evaluation_metrics ADD COLUMN has_screen_text_pct REAL",
    "ALTER TABLE evaluation_metrics ADD COLUMN avg_description_chars REAL",
    "ALTER TABLE evaluation_metrics ADD COLUMN generic_description_pct REAL",
]


def _init_db() -> None:
    """Ensure the database file and schema exist (idempotent, thread-safe)."""
    db_dir = DB_PATH.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)

    with _ENGINE_LOCK:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.executescript(SCHEMA)
            # Run idempotent migrations (skip if column already exists)
            for migration in _MIGRATIONS:
                try:
                    conn.execute(migration)
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


@contextmanager
def get_db():
    """Yield a sqlite3.Connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Videos helpers
# ---------------------------------------------------------------------------


def ensure_video(video_id: str, *, source: str = "corpus", **fields: Any) -> None:
    """Insert or ignore a video row. Missing optional fields default to empty strings."""
    defaults = {
        "id": video_id,
        "source": source,
        "filename": "",
        "file_path": "",
        "language": "",
        "duration_bucket": "",
        "content_type": "",
        "video_duration_sec": 0.0,
        "checksum": "",
    }
    defaults.update(fields)
    with get_db() as db:
        db.execute(
            """INSERT OR IGNORE INTO videos (id, source, filename, file_path,
               language, duration_bucket, content_type, video_duration_sec, checksum)
               VALUES (:id, :source, :filename, :file_path,
                       :language, :duration_bucket, :content_type, :video_duration_sec, :checksum)""",
            defaults,
        )


# ---------------------------------------------------------------------------
# Job helpers (mirror + supplement file-based job_meta.json)
# ---------------------------------------------------------------------------


def create_job(job_id: str, video_id: str, *, config: str = "B1", language: str = "en") -> None:
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO jobs (id, video_id, config, status, language) VALUES (:id, :vid, :cfg, :st, :lang)",
            {"id": job_id, "vid": video_id, "cfg": config, "st": "queued", "lang": language},
        )


def update_job(job_id: str, **fields: Any) -> None:
    """Update job fields: status, processing_time_sec, error_message, etc."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    with get_db() as db:
        db.execute(f"UPDATE jobs SET {set_clause} WHERE id = :id", {"id": job_id, **fields})


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = :id", {"id": job_id}).fetchone()
        return dict(row) if row else None


def list_jobs(video_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    clauses = []
    params: dict[str, Any] = {}
    if video_id:
        clauses.append("video_id = :vid")
        params["vid"] = video_id
    if status:
        clauses.append("status = :st")
        params["st"] = status
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM jobs {where} ORDER BY created_at DESC", params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


def upsert_artifact(job_id: str, artifact_type: str, file_path: str) -> None:
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO artifacts (job_id, type, file_path) VALUES (:jid, :typ, :fp)",
            {"jid": job_id, "typ": artifact_type, "fp": file_path},
        )


def get_artifacts(job_id: str) -> dict[str, str]:
    with get_db() as db:
        rows = db.execute(
            "SELECT type, file_path FROM artifacts WHERE job_id = :jid", {"jid": job_id}
        ).fetchall()
        return {r["type"]: r["file_path"] for r in rows}


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def upsert_scene(
    job_id: str,
    scene_id: int,
    *,
    time_sec: float,
    description: str,
    description_length: int | None = None,
    has_screen_text: int = 0,
    content_score: int = 0,
    tts_cached: int = 0,
) -> int:
    dlen = description_length or len(description)
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO scenes
               (job_id, scene_id, time_sec, description, description_length,
                has_screen_text, content_score, tts_cached)
               VALUES (:jid, :sid, :ts, :desc, :dlen, :hst, :cs, :tts)""",
            {
                "jid": job_id,
                "sid": scene_id,
                "ts": time_sec,
                "desc": description,
                "dlen": dlen,
                "hst": has_screen_text,
                "cs": content_score,
                "tts": tts_cached,
            },
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_scenes(job_id: str) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM scenes WHERE job_id = :jid ORDER BY scene_id", {"jid": job_id}
        ).fetchall()
        return [dict(r) for r in rows]


def get_scene(job_id: str, scene_id: int) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM scenes WHERE job_id = :jid AND scene_id = :sid",
            {"jid": job_id, "sid": scene_id},
        ).fetchone()
        return dict(row) if row else None


def get_nearest_scene(job_id: str, time_sec: float, tolerance: float = 30.0) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM scenes WHERE job_id = :jid
               AND ABS(time_sec - :ts) <= :tol
               ORDER BY ABS(time_sec - :ts) LIMIT 1""",
            {"jid": job_id, "ts": time_sec, "tol": tolerance},
        ).fetchone()
        return dict(row) if row else None


def mark_scene_tts(scene_db_id: int, language: str, audio_path: str, duration_sec: float) -> None:
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO tts_cache (scene_id, language, audio_path, duration_sec) VALUES (:sid, :lang, :ap, :dur)",
            {"sid": scene_db_id, "lang": language, "ap": audio_path, "dur": duration_sec},
        )
        db.execute("UPDATE scenes SET tts_cached = 1 WHERE id = :sid", {"sid": scene_db_id})


def get_tts_cache(scene_db_id: int, language: str) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM tts_cache WHERE scene_id = :sid AND language = :lang",
            {"sid": scene_db_id, "lang": language},
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------


def create_evaluation_run(run_name: str, total_videos: int = 0) -> int:
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO evaluation_runs (run_name, total_videos) VALUES (:rn, :tv)",
            {"rn": run_name, "tv": total_videos},
        )
        row = db.execute("SELECT id FROM evaluation_runs WHERE run_name = :rn", {"rn": run_name}).fetchone()
        return row["id"]  # type: ignore[index]


def upsert_evaluation_metric(run_id: int, video_id: str, **fields: Any) -> None:
    columns = ", ".join(fields.keys())
    placeholders = ", ".join(f":{k}" for k in fields)
    updates = ", ".join(f"{k} = excluded.{k}" for k in fields)
    with get_db() as db:
        db.execute(
            f"INSERT INTO evaluation_metrics (run_id, video_id, {columns}) "
            f"VALUES (:run_id, :video_id, {placeholders}) "
            f"ON CONFLICT(run_id, video_id) DO UPDATE SET {updates}",
            {"run_id": run_id, "video_id": video_id, **fields},
        )


def get_evaluation_metrics(run_id: int) -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM evaluation_metrics WHERE run_id = :rid ORDER BY video_id",
            {"rid": run_id},
        ).fetchall()
        return [dict(r) for r in rows]


def list_evaluation_runs() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM evaluation_runs ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# Boot schema on first import
_init_db()
