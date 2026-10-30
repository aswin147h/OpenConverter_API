import time
import zipfile

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_and_capabilities():
    assert client.get("/").json()["status"] == "ok"
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert "image" in body["supported_input_types"]
    assert "pdf" in body["supported_input_types"]
    assert "docx" in body["supported_input_types"]
    assert "xlsx" in body["supported_input_types"]
    assert "pptx" in body["supported_input_types"]
    assert body["limits"]["max_upload_bytes"] > 0


def test_job_history_endpoint():
    response = client.get("/api/v1/jobs?limit=20")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_status_and_download_image_job(image_path):
    with open(image_path, "rb") as upload:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("scan.png", upload, "image/png")},
            data={"target_format": "txt", "ocr_enabled": "true", "ocr_language": "eng"},
        )

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(100):
        status = client.get(f"/api/v1/jobs/{job_id}")
        assert status.status_code == 200
        if status.json()["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    assert status.json()["status"] == "completed"

    download = client.get(f"/api/v1/jobs/{job_id}/download")
    assert download.status_code == 200
    assert b"OpenConvert" in download.content


def test_invalid_conversion_pair(image_path):
    with open(image_path, "rb") as upload:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("scan.png", upload, "image/png")},
            data={"target_format": "csv"},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_conversion"


def test_create_docx_and_xlsx_jobs(docx_path, xlsx_path):
    for path, target_format in ((docx_path, "txt"), (xlsx_path, "csv")):
        filename = f"sample{'.docx' if target_format == 'txt' else '.xlsx'}"
        with open(path, "rb") as upload:
            response = client.post(
                "/api/v1/jobs",
                files={"file": (filename, upload, "application/octet-stream")},
                data={"target_format": target_format, "ocr_enabled": "false", "ocr_language": "eng"},
            )
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        for _ in range(100):
            status = client.get(f"/api/v1/jobs/{job_id}")
            if status.json()["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)
        assert status.json()["status"] == "completed"


def test_cancel_job(image_path):
    with open(image_path, "rb") as upload:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("scan.png", upload, "image/png")},
            data={"target_format": "txt"},
        )
    job_id = response.json()["job_id"]
    cancelled = client.delete(f"/api/v1/jobs/{job_id}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
