import sqlite3
import threading
import time
import shutil
from pathlib import Path
from typing import Any

from app import config

_lock = threading.RLock()


def _database_path() -> Path:
    return Path(config.DATA_DIR) / "jobs.sqlite3"


def initialize() -> None:
    database = _database_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source_name TEXT NOT NULL,
                target_format TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                input_path TEXT,
                output_path TEXT,
                error_code TEXT,
                error_message TEXT
            )
            """
        )


def create(job_id: str, source_name: str, target_format: str, created_at: str,
           input_path: str, output_path: str) -> None:
    initialize()
    with _lock, sqlite3.connect(_database_path()) as connection:
        connection.execute(
            "INSERT INTO jobs(job_id,status,source_name,target_format,message,created_at,input_path,output_path) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (job_id, "queued", source_name, target_format, "Waiting to be processed", created_at, input_path, output_path),
        )


def update(job_id: str, **changes: Any) -> None:
    allowed = {
        "status": "status", "progress": "progress", "message": "message",
        "error_code": "error_code", "error_message": "error_message",
        "input_path": "input_path", "output_path": "output_path",
    }
    columns = [(allowed[key], value) for key, value in changes.items() if key in allowed]
    if not columns:
        return
    initialize()
    assignments = ", ".join(f"{column} = ?" for column, _ in columns)
    values = [value for _, value in columns] + [job_id]
    with _lock, sqlite3.connect(_database_path()) as connection:
        connection.execute(f"UPDATE jobs SET {assignments} WHERE job_id = ?", values)


def get(job_id: str):
    initialize()
    with _lock, sqlite3.connect(_database_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_recent(limit: int = 20):
    initialize()
    with _lock, sqlite3.connect(_database_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def cleanup(retention_seconds: int) -> int:
    initialize()
    cutoff = time.time() - retention_seconds
    root = Path(config.DATA_DIR) / "jobs"
    removed = 0
    if root.exists():
        for directory in root.iterdir():
            if directory.is_dir() and directory.stat().st_mtime < cutoff:
                shutil.rmtree(directory, ignore_errors=True)
                removed += 1
    with _lock, sqlite3.connect(_database_path()) as connection:
        connection.execute(
            "UPDATE jobs SET status = 'expired' WHERE status IN ('completed','failed','cancelled') "
            "AND created_at < datetime('now', '-' || ? || ' seconds')",
            (retention_seconds,),
        )
    return removed
