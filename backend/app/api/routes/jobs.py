import os
import threading
import uuid
import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import config
from app.errors import ConversionError
from app.security import validate_upload
from app.services import capabilities
from app.storage.job_store import create as store_create_job
from app.storage.job_store import get as store_get_job
from app.storage.job_store import update as store_update_job

router = APIRouter(prefix="/api/v1", tags=["jobs"])

JOB_STORE: dict[str, dict[str, Any]] = {}


def _ensure_storage() -> Path:
    root = Path(config.DATA_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_path(job_id: str) -> Path:
    return _ensure_storage() / job_id


def _file_kind(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return capabilities.kind_for_extension(ext)


def _run_conversion(job_id: str, src_path: str, dst_path: str, target_format: str, lang: str) -> None:
    job = JOB_STORE[job_id]
    if job["status"] == "cancelled":
            return
    job["status"] = "processing"
    job["progress"] = 0
    job["message"] = "Processing document"
    store_update_job(job_id, status="processing", progress=0, message="Processing document")

    kind = _file_kind(job["source_name"])
    adapter = capabilities.get_adapter(kind, target_format) if kind else None
    if adapter is None:
        raise ConversionError("unsupported_conversion", "Unsupported conversion pair.")

    try:
        def progress(current: int, total: int) -> None:
            if job["status"] == "cancelled":
                return
            job["progress"] = round(current / total * 100) if total else 100
            job["message"] = f"OCR processing page {current} of {total}"
            store_update_job(
                job_id,
                progress=job["progress"],
                message=job["message"],
            )

        adapter(src_path, dst_path, lang=lang, progress=progress)
    except ConversionError as exc:
        if job["status"] == "cancelled":
            return
        job["status"] = "failed"
        job["error"] = {"code": exc.code, "message": exc.message}
        store_update_job(job_id, status="failed", error_code=exc.code, error_message=exc.message)
        return
    except Exception:  # pragma: no cover - defensive guard for runtime failures
        if job["status"] == "cancelled":
            return
        job["status"] = "failed"
        job["error"] = {"code": "internal_error", "message": "Conversion failed unexpectedly."}
        store_update_job(job_id, status="failed", error_code="internal_error", error_message="Conversion failed unexpectedly.")
        return

    if job["status"] == "cancelled":
        return
    job["status"] = "completed"
    job["progress"] = 100
    job["message"] = "Conversion complete"
    job["output_format"] = target_format
    job["download_filename"] = f"converted.{target_format}"
    job["output_path"] = dst_path
    store_update_job(job_id, status="completed", progress=100, message="Conversion complete", output_path=dst_path)


@router.post("/jobs", status_code=202)
def create_job(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    ocr_enabled: bool = Form(False),
    ocr_language: str = Form("eng"),
):
    target_format = target_format.lower().strip(".")
    if not target_format:
        raise HTTPException(status_code=422, detail={"code": "invalid_target_format", "message": "target_format is required"})

    if ocr_language not in config.ALLOWED_OCR_LANGUAGES:
        raise HTTPException(status_code=422, detail={"code": "invalid_language", "message": "OCR language is not supported."})

    source_kind = _file_kind(file.filename or "")
    if source_kind is None:
        raise HTTPException(status_code=415, detail={"code": "unsupported_input_type", "message": "Unsupported input file type."})

    if capabilities.get_adapter(source_kind, target_format) is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_conversion",
                "message": f"Unsupported conversion: {source_kind} -> {target_format}",
            },
        )

    job_id = str(uuid.uuid4())
    job_dir = _job_path(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    input_path = job_dir / "input"
    output_path = job_dir / "output"

    if file.filename:
        suffix = Path(file.filename).suffix.lower()
        input_path = job_dir / f"input{suffix}"

    # Save the uploaded content to the job directory.
    file_bytes = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail={"code": "empty_file", "message": "Uploaded file is empty."})
    if len(file_bytes) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={"code": "upload_too_large", "message": "Upload exceeds the configured size limit."})

    try:
        detected_kind = validate_upload(
            file.filename or "",
            file_bytes,
            config.MAX_UPLOAD_BYTES,
            config.MAX_PAGES,
        )
    except ConversionError as exc:
        status_code = 422 if exc.code == "encrypted_pdf" else 415
        raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})

    if detected_kind != source_kind:
        raise HTTPException(status_code=415, detail={"code": "unsupported_file_type", "message": "The file content does not match its extension."})

    input_path.write_bytes(file_bytes)
    output_path = job_dir / f"converted.{target_format}"

    job = {
        "job_id": job_id,
        "status": "queued",
        "source_name": file.filename or "upload",
        "target_format": target_format,
        "output_format": target_format,
        "progress": 0,
        "message": "Waiting to be processed",
        "ocr_enabled": ocr_enabled,
        "ocr_language": ocr_language,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "input_path": str(input_path),
        "output_path": str(output_path),
    }
    JOB_STORE[job_id] = job
    store_create_job(
        job_id,
        file.filename or "upload",
        target_format,
        job["created_at"],
        str(input_path),
        str(output_path),
    )

    thread = threading.Thread(
        target=_run_conversion,
        args=(job_id, str(input_path), str(output_path), target_format, ocr_language),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOB_STORE.get(job_id)
    if job is None:
        stored = store_get_job(job_id)
        if stored:
            job = {
                "job_id": job_id,
                "status": stored["status"],
                "progress": stored["progress"],
                "message": stored["message"],
                "target_format": stored["target_format"],
                "output_format": stored["target_format"],
                "ocr_enabled": False,
                "ocr_language": "eng",
                "error": None,
                "input_path": stored["input_path"],
                "output_path": stored["output_path"],
            }
            if stored["error_code"]:
                job["error"] = {"code": stored["error_code"], "message": stored["error_message"]}
            JOB_STORE[job_id] = job
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
        "target_format": job.get("target_format"),
        "output_format": job.get("output_format", job.get("target_format")),
        "ocr_enabled": job.get("ocr_enabled", False),
        "ocr_language": job.get("ocr_language", "eng"),
        "error": job.get("error"),
        "error_code": job.get("error", {}).get("code"),
        "download_url": f"/api/v1/jobs/{job_id}/download" if job["status"] == "completed" else None,
    }


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    job = JOB_STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail={"code": "job_not_ready", "message": "Job is not ready for download."})

    output_file = Path(job["output_path"])
    if not output_file.exists():
        raise HTTPException(status_code=404, detail={"code": "output_missing", "message": "Output file is missing."})

    return FileResponse(
        path=str(output_file),
        filename=job.get("download_filename", output_file.name),
        media_type="application/octet-stream",
    )


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    job = JOB_STORE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})

    job["status"] = "cancelled"
    store_update_job(job_id, status="cancelled", progress=job.get("progress", 0), message="Job cancelled")
    for path in [job.get("input_path"), job.get("output_path")]:
        if path:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    return {"job_id": job_id, "status": "cancelled"}


@router.get("/capabilities")
def capabilities_endpoint():
    supported = [
        {"input": kind, "output": target, "ocr": kind in {"image", "pdf"}}
        for kind in sorted({source for source, _ in capabilities.ROUTES})
        for target in capabilities.outputs_for(kind)
    ]
    return {
        "supported_conversions": supported,
        "supported_input_types": sorted({source for source, _ in capabilities.ROUTES}),
        "ocr_languages": sorted(config.ALLOWED_OCR_LANGUAGES),
        "limits": {
            "max_upload_bytes": config.MAX_UPLOAD_BYTES,
            "max_pages": config.MAX_PAGES,
            "max_image_pixels": config.MAX_IMAGE_PIXELS,
            "ocr_timeout_seconds": config.OCR_TIMEOUT_SECONDS,
            "retention_seconds": config.RETENTION_SECONDS,
        },
    }
