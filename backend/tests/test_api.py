from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_and_capabilities():
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["valid_outputs"]["image"] == ["pdf", "txt"]
    assert body["valid_outputs"]["pdf"] == ["pdf", "txt"]
    assert body["max_upload_bytes"] > 0


def test_create_status_and_download_image_job(image_path):
    with open(image_path, "rb") as upload:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("scan.png", upload, "image/png")},
            data={"target_format": "txt", "ocr_enabled": "true", "ocr_language": "eng"},
        )

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/v1/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["progress"] == 100

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
