import fitz
import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.errors import ConversionError
from app.services import capabilities, conversion, ocr, pdf


def test_image_to_txt(image_path, tmp_path):
    out = tmp_path / "o.txt"
    conversion.image_to_txt(image_path, str(out))
    assert "OpenConvert" in out.read_text()


def test_image_to_searchable_pdf(image_path, tmp_path):
    out = tmp_path / "o.pdf"
    conversion.image_to_searchable_pdf(image_path, str(out))
    with fitz.open(out) as d:
        assert "OpenConvert" in d[0].get_text()


def test_text_pdf_uses_native_extraction(text_pdf):
    doc = pdf.open_pdf(text_pdf)
    assert pdf.has_native_text(doc)
    doc.close()
    assert "Native text layer" in pdf.pdf_to_text(text_pdf)


def test_scanned_pdf_detected_and_ocrd(scanned_pdf):
    doc = pdf.open_pdf(scanned_pdf)
    assert not pdf.has_native_text(doc)
    doc.close()
    calls = []
    text = pdf.pdf_to_text(scanned_pdf, progress=lambda c, t: calls.append((c, t)))
    assert text.count("OpenConvert") == 2
    assert calls == [(1, 2), (2, 2)]


def test_scanned_pdf_to_searchable_pdf(scanned_pdf, tmp_path):
    out = tmp_path / "s.pdf"
    conversion.pdf_to_searchable_pdf(scanned_pdf, str(out))
    with fitz.open(out) as d:
        assert d.page_count == 2
        assert all("OpenConvert" in p.get_text() for p in d)


def test_invalid_language_rejected(image_path):
    with pytest.raises(ConversionError) as e:
        ocr.image_to_text(ocr.open_image(image_path), "xx; rm -rf /")
    assert e.value.code == "invalid_language"


def test_corrupt_pdf(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"not a pdf")
    with pytest.raises(ConversionError) as e:
        pdf.open_pdf(str(p))
    assert e.value.code == "invalid_pdf"


def test_capabilities_matrix():
    assert capabilities.outputs_for("image") == ["pdf", "txt"]
    assert capabilities.outputs_for("pdf") == ["docx", "pdf", "txt"]
    assert capabilities.outputs_for("docx") == ["pdf", "txt"]
    assert capabilities.outputs_for("xlsx") == ["csv", "pdf"]
    assert capabilities.outputs_for("pptx") == ["pdf"]
    assert capabilities.get_adapter("image", "docx") is None


def test_docx_to_txt(docx_path, tmp_path):
    out = tmp_path / "sample.txt"
    conversion.docx_to_txt(docx_path, str(out))
    text = out.read_text(encoding="utf-8")
    assert "OpenConvert Word document" in text
    assert "Name\tValue" in text


def test_xlsx_to_csv(xlsx_path, tmp_path):
    out = tmp_path / "sample.csv"
    conversion.xlsx_to_csv(xlsx_path, str(out))
    text = out.read_text(encoding="utf-8")
    assert "Worksheet: Results" in text
    assert "OpenConvert,123" in text


def test_pdf_to_docx(text_pdf, tmp_path):
    out = tmp_path / "sample.docx"
    conversion.pdf_to_docx(text_pdf, str(out))
    from docx import Document

    document = Document(str(out))
    assert "Native text layer document for OpenConvert testing." in "\n".join(
        paragraph.text for paragraph in document.paragraphs
    )


def test_office_to_pdf_mocked(tmp_path):
    src = tmp_path / "sample.docx"
    src.write_bytes(b"fake-office-source")
    dst = tmp_path / "sample.pdf"

    def fake_run(command, **kwargs):
        outdir = Path(command[command.index("--outdir") + 1])
        (outdir / "sample.pdf").write_bytes(b"%PDF-1.4")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch.object(conversion, "_libreoffice_executable", return_value="/usr/bin/soffice"), patch.object(
        conversion.subprocess, "run", side_effect=fake_run
    ):
        conversion.docx_to_pdf(str(src), str(dst))

    assert dst.read_bytes().startswith(b"%PDF")
