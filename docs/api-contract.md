# API contract (proposed)

## POST /api/v1/jobs
Content type: multipart/form-data
Fields:
- `file`: uploaded file
- `target_format`: e.g. `pdf`, `docx`, `xlsx`, `txt`, `csv`
- `ocr_enabled`: boolean
- `ocr_language`: language code such as `eng` (must be installed and allowlisted)

Response: `202 Accepted`
```json
{
  "job_id": "random-unguessable-id",
  "status": "queued",
  "status_url": "/api/v1/jobs/random-unguessable-id"
}
```

## GET /api/v1/jobs/{job_id}
Example response:
```json
{
  "job_id": "random-unguessable-id",
  "status": "processing",
  "progress": 45,
  "message": "OCR processing page 4 of 9",
  "output_format": "pdf",
  "error_code": null
}
```
Statuses: `queued`, `processing`, `completed`, `failed`, `expired`, `cancelled`.

## GET /api/v1/jobs/{job_id}/download
Returns the output as a file attachment only if the job belongs to the requester or a valid unguessable capability token is supplied. In production, prefer a short-lived signed URL for private object storage.

## GET /api/v1/capabilities
Returns supported input types, valid target formats per input type, OCR languages, maximum file size and page count.

## Error conventions
- 400: malformed request
- 413: upload exceeds limit
- 415: unsupported or mismatched file type
- 422: unsupported conversion pair or invalid options
- 429: rate/quota limit reached
- 500: generic failure; do not expose stack traces or server paths

Do not return raw filesystem paths, internal exception messages, or secrets.
