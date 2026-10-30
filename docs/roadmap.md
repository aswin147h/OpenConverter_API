# Roadmap

This file tracks implementation status against the current verified codebase.
Complete phases are based on passing tests and runnable Docker/frontend/API surfaces.

## Verified status
- [x] **Phase 0** — Scope, limits, format matrix and project structure
- [x] **Phase 1** — Local OCR for images and PDFs, including searchable PDF output
- [x] **Phase 2** — LibreOffice office-to-PDF, DOCX/XLSX text extraction and CSV export
- [x] **Phase 3** — FastAPI job API
- [x] **Phase 4** — React drag-and-drop UI with job progress and download states
- [ ] **Phase 5** — Docker queue/hardening, rate limits, malware scanning and launch
- [ ] **Phase 6** — Private beta, usage metrics and iteration

## Phase 0 — Scope and UX (1–2 days)
- Choose a name and minimal visual identity.
- Decide file size/page limits.
- Publish a tested format matrix.
- Sketch upload, options, processing, success and error states.

## Phase 1 — Local OCR engine (3–5 days)
- Set up Python environment and install Tesseract + language data.
- Implement image -> TXT.
- Implement scanned PDF -> searchable PDF and TXT.
- Add page-by-page processing, timeout and clear errors.
- Test clean, blurry, rotated, multi-page and Tamil/English samples.

## Phase 2 — Conversion adapters (3–7 days)
- Add DOCX/XLSX/PPTX -> PDF using LibreOffice.
- Add text PDF -> TXT and DOCX best-effort.
- Add CSV/XLSX extraction routes.
- Create automated tests for every supported source/target pair.

## Phase 3 — API (4–7 days)
- Build FastAPI upload/capabilities/status/download endpoints.

## Phase 4 — Frontend (3–5 days)
- Build React drag-and-drop UI and progress polling.
- Add preview, OCR language selection and clear warnings.
- Add unit and end-to-end tests.

## Phase 5 — Public MVP hardening (3–7 days)
- Dockerize API and worker.
- Add job queue for long jobs.
- Add rate limits, secure temporary storage, automatic cleanup and logging.
- Run malformed-file and load tests.
- Add privacy policy, limits and error reporting.

## Phase 6 — Launch and iterate
- Deploy a private beta first.
- Track conversion success, median processing time, timeout rate and cost per job.
- Add formats based on real demand.
- Add accounts only if they are needed; anonymous conversion reduces initial complexity.

Time estimate: roughly 2–4 weeks for a focused solo MVP, depending on experience, testing depth and hosting setup. This is an estimate, not a guarantee.
