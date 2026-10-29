from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse

from ... import config
from ...errors import ConversionError
from ...security import validate_upload
from ...services import capabilities, pdf
from ...storage import jobs, new_job_directory


router = APIRouter(prefix="/api/v1", tags=["jobs"])


def _error(status_code: int, code: str, message: str):
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


def _progress(job_id: str):
    def update(current: int, total: int):
        percent = round((current / total) * 100) if total else 0
        jobs.update(job_id, progress=percent, message=f"OCR processing page {current} of {total}")
    return update


def _process_job(job_id: str, input_path: str, output_path: str, target: str,
                 kind: str, lang: str, force_ocr: bool):
    current = jobs.get(job_id)
    if current and current.status == "cancelled":
        return
    jobs.update(job_id, status="processing", progress=0, message="Processing document")
    try:
        adapter = capabilities.get_adapter(kind, target)
        if adapter is None:
            raise ConversionError("unsupported_conversion", "The conversion pair is not supported.")

        if kind == "pdf":
            if target == "txt":
                text = pdf.pdf_to_text(
                    input_path, lang=lang, force_ocr=force_ocr, progress=_progress(job_id)
                )
                with open(output_path, "w", encoding="utf-8") as output:
                    output.write(text)
                jobs.update(job_id, progress=100)
            else:
                pdf.pdf_to_searchable_pdf(
                    input_path, output_path, lang=lang, progress=_progress(job_id)
                )
        else:
            adapter(input_path, output_path, lang=lang, progress=_progress(job_id))
        jobs.update(job_id, status="completed", progress=100, message="Conversion complete")
    except ConversionError as exc:
        jobs.update(job_id, status="failed", progress=0, error_code=exc.code,
                    message="Conversion failed")
    except Exception:
        jobs.update(job_id, status="failed", progress=0, error_code="processing_failed",
                    message="Conversion failed")


@router.get("/capabilities")
def get_capabilities():
    return {
        "supported_inputs": {
            "image": ["jpg", "jpeg", "png", "tif", "tiff"],
            "pdf": ["pdf"],
        },
        "valid_outputs": {
            "image": capabilities.outputs_for("image"),
            "pdf": capabilities.outputs_for("pdf"),
        },
        "ocr_languages": sorted(config.ALLOWED_OCR_LANGUAGES),
        "max_upload_bytes": config.MAX_UPLOAD_BYTES,
        "max_pdf_pages": config.MAX_PAGES,
    }


@router.post("/jobs", status_code=202)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    ocr_enabled: bool = Form(False),
    ocr_language: str = Form("eng"),
):
    filename = file.filename or "upload"
    try:
        if ocr_language not in config.ALLOWED_OCR_LANGUAGES:
            raise ConversionError("invalid_language", "OCR language is not supported.")
        content = await file.read(config.MAX_UPLOAD_BYTES + 1)
        kind = validate_upload(
            filename, content, config.MAX_UPLOAD_BYTES, config.MAX_PAGES
        )
        target = target_format.lower().lstrip(".")
        if target not in capabilities.outputs_for(kind):
            raise ConversionError(
                "unsupported_conversion",
                f"Unsupported conversion pair. Supported outputs: {capabilities.outputs_for(kind)}",
            )

        job = jobs.create(target, filename)
        directory = new_job_directory(job.job_id)
        extension = filename.rsplit(".", 1)[-1].lower()
        input_path = str(directory / f"input.{extension}")
        output_path = str(directory / f"output.{target}")
        with open(input_path, "wb") as destination:
            destination.write(content)
        jobs.update(job.job_id, input_path=input_path, output_path=output_path)
        background_tasks.add_task(
            _process_job, job.job_id, input_path, output_path,
            target, kind, ocr_language, ocr_enabled,
        )
        return {
            "job_id": job.job_id,
            "status": "queued",
            "status_url": f"/api/v1/jobs/{job.job_id}",
        }
    except ConversionError as exc:
        status = 422
        if exc.code in {"upload_too_large"}:
            status = 413
        elif exc.code in {"invalid_image", "invalid_pdf", "encrypted_pdf", "unsupported_file_type"}:
            status = 415 if exc.code != "encrypted_pdf" else 422
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "output_format": job.output_format,
        "error_code": job.error_code,
    }


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})
    if job.status != "completed":
        raise HTTPException(status_code=409, detail={"code": "job_not_ready", "message": "Job is not completed."})
    if not job.output_path or not Path(job.output_path).is_file():
        raise HTTPException(status_code=410, detail={"code": "output_expired", "message": "The output is no longer available."})

    stem = job.source_name.rsplit(".", 1)[0] if "." in job.source_name else job.source_name
    filename = f"{stem}.{job.output_format}"
    media_type = "application/pdf" if job.output_format == "pdf" else "text/plain"
    return FileResponse(job.output_path, filename=filename, media_type=media_type)


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    if not jobs.cancel(job_id):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job not found."})
        raise HTTPException(status_code=409, detail={"code": "job_not_cancellable", "message": "Job cannot be cancelled."})
    return {"job_id": job_id, "status": "cancelled"}