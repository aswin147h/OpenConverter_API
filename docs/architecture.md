# Architecture

## High-level request flow
1. React frontend uploads a file and selected conversion options.
2. FastAPI validates size, extension, detected file type, and supported conversion pair.
3. API creates a random job ID and stores the input in a private temporary directory or private object storage.
4. API enqueues a job; a worker processes the file in an isolated working directory.
5. Worker performs text extraction and/or OCR, then calls the appropriate conversion adapter.
6. Worker writes output and updates job status.
7. Frontend polls job status and requests a short-lived download URL.
8. Cleanup removes input/output artifacts after the configured retention period.

## Components
- Frontend: upload/drop zone, format selectors, OCR language, progress state, error messages, download button.
- API: upload endpoint, conversion capability registry, job status, download authorization.
- Conversion registry: explicit map of supported source/target pairs to adapters.
- OCR adapter: Tesseract invocation with configured language packs and timeout.
- PDF adapter: PyMuPDF for text extraction/rendering and PDF inspection.
- Office adapter: LibreOffice headless in a restricted worker container.
- Queue: Redis + Celery once jobs may be long-running or concurrent.
- Metadata database: PostgreSQL in a production deployment; SQLite is acceptable for a local prototype.
- Storage: local temporary directories for development; private object storage for production.
- Observability: structured logs, job duration, failure codes, queue depth, resource metrics.

## Processing strategy
- Text-based PDF: attempt native text extraction first.
- Scanned PDF: render pages to images, OCR each page, optionally create searchable PDF.
- Image: OCR directly after orientation/contrast preprocessing when useful.
- DOCX/XLSX/PPTX: use native parsers or LibreOffice conversion for supported routes.
- PDF tables -> XLSX: a specialized extraction route; warn users that table structure may need correction.
- Unsupported pair: return a clear 422 response listing supported output formats.

## API design
Use asynchronous job semantics for long tasks:
- POST /api/v1/jobs -> 202 Accepted with job_id
- GET /api/v1/jobs/{job_id} -> status and progress
- GET /api/v1/jobs/{job_id}/download -> authorized download response or short-lived URL
- GET /api/v1/capabilities -> supported extensions, output formats, OCR languages, limits
- DELETE /api/v1/jobs/{job_id} -> cancel if possible and schedule cleanup

## Deployment profiles
### Local prototype
Run frontend and API locally; install Tesseract and LibreOffice on the host. Use local temporary storage and SQLite. No public uploads.

### MVP online
Frontend static hosting; API and OCR worker in Docker on a host that supports system packages and persistent/temporary storage; Redis queue; managed PostgreSQL only if job history/account features are required. Keep files private and short-lived.

### Scale-up
Separate API and worker deployments, Redis/Celery, private object storage, PostgreSQL, reverse proxy, monitoring, quotas and autoscaling. OCR workers need CPU and memory limits.
