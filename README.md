# OpenConvert — OCR Document Converter

A Python-first free-to-use OCR document conversion web app.

## MVP goal
Users upload supported documents, choose an output format, optionally enable OCR, see processing status, and download the result.

## Stack
- Frontend: React + TypeScript (Vite) — Phase 4
- API: FastAPI + Uvicorn — Phase 3
- OCR: Tesseract + pytesseract
- PDF: PyMuPDF
- Office conversions: LibreOffice headless — Phase 2
- Later: Redis + Celery, PostgreSQL, Docker Compose

## Scope note
Only explicit, tested conversion routes are exposed (see `docs/supported-formats.md`). OCR does not perfectly reconstruct layout, tables or handwriting.

## Quick start (backend)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
python -m app.cli scan.png out.txt --lang eng
python -m app.cli scan.pdf out.pdf
```

## Layout
- `backend/app/` — services (ocr, pdf, conversion, capabilities), config, CLI
- `backend/tests/` — unit and regression tests
- `frontend/` — React app (not started)
- `docs/` — architecture, API contract, format matrix, security checklist, roadmap
