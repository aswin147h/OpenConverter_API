# Supported formats: MVP policy

Avoid the claim "any file to any file." Publish a tested capability matrix and only expose combinations that have automated tests.

| Input | Output | OCR? | Notes |
|---|---|---|---|
| JPG / PNG / TIFF | TXT | Yes | Printed text; accuracy depends on image quality |
| JPG / PNG / TIFF | Searchable PDF | Yes | Image remains visible; OCR text layer is added |
| Scanned PDF | Searchable PDF | Yes | Render pages, OCR, create searchable output |
| Scanned PDF | TXT | Yes | Text only; layout may be lost |
| Text PDF | TXT | Usually no | Native text extraction first |
| DOCX | PDF | No | LibreOffice conversion |
| XLSX | PDF | No | Spreadsheet print layout may differ |
| PPTX | PDF | No | Slide layout conversion |
| DOCX | TXT | No | Text extraction |
| XLSX | CSV | No | One worksheet per CSV export; define worksheet selection |
| PDF | DOCX | Sometimes | Best-effort; complex layout may change |

## Add later
- OCR language selector (English first; Tamil/Hindi after installing and testing trained data)
- ODT/ODS/ODP, RTF, HTML, CSV
- Batch jobs and ZIP download
- OCR confidence indicators and page-level preview

## Unsupported by default
Executables, archives with unknown contents, password-protected documents without a password workflow, corrupted files, macro execution, and formats with no safe conversion adapter.
