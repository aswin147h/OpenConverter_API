import shutil
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from .. import config


@dataclass
class Job:
    job_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Waiting to be processed"
    output_format: Optional[str] = None
    error_code: Optional[str] = None
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    source_name: str = ""


class JobStore:
    def __init__(self):
        self._lock = threading.RLock()
        self.jobs: Dict[str, Job] = {}

    def create(self, output_format: str, source_name: str) -> Job:
        with self._lock:
            job = Job(
                job_id=uuid.uuid4().hex,
                output_format=output_format,
                source_name=source_name,
            )
            self.jobs[job.job_id] = job
            return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self.jobs.get(job_id)

    def update(self, job_id: str, **changes) -> Optional[Job]:
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                for key, value in changes.items():
                    setattr(job, key, value)
            return job

    def remove(self, job_id: str) -> bool:
        with self._lock:
            job = self.jobs.pop(job_id, None)
        if not job:
            return False
        for path in (job.input_path, job.output_path):
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
        return True

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status in {"completed", "failed", "cancelled"}:
                return False
            job.status = "cancelled"
            job.message = "Job cancelled"
        for path in (job.input_path, job.output_path):
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
        return True


jobs = JobStore()


def new_job_directory(job_id: str) -> Path:
    directory = Path(config.DATA_DIR) / "jobs" / job_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cleanup_expired_jobs() -> None:
    import time

    cutoff = time.time() - config.RETENTION_SECONDS
    root = Path(config.DATA_DIR) / "jobs"
    if not root.exists():
        return
    for job in list(jobs.jobs.values()):
        if job.status in {"completed", "failed", "cancelled", "expired"}:
            for path in (job.input_path, job.output_path):
                if path and Path(path).exists() and Path(path).stat().st_mtime < cutoff:
                    try:
                        Path(path).unlink()
                    except OSError:
                        pass
    for directory in root.iterdir():
        if directory.is_dir() and directory.stat().st_mtime < cutoff:
            shutil.rmtree(directory, ignore_errors=True)