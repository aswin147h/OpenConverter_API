"""PDF inspection, native text extraction, rendering and OCR pipelines."""
from typing import Callable, Optional

import fitz  # PyMuPDF
from PIL import Image

from .. import config
from ..errors import ConversionError
from . import ocr

Progress = Optional[Callable[[int, int], None]]  # (current_page, total_pages)
MIN_NATIVE_CHARS_PER_PAGE = 20


def open_pdf(path: str) -> fitz.Document:
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise ConversionError("invalid_pdf", "PDF could not be read.") from exc
    if doc.needs_pass:
        doc.close()
        raise ConversionError("encrypted_pdf", "Password-protected PDFs are not supported.")
    if doc.page_count > config.MAX_PAGES:
        doc.close()
        raise ConversionError("too_many_pages", "PDF exceeds the page limit.")
    return doc


def has_native_text(doc: fitz.Document) -> bool:
    """True if most pages carry real extractable text."""
    if doc.page_count == 0:
        return False
    good = sum(1 for p in doc if len(p.get_text().strip()) >= MIN_NATIVE_CHARS_PER_PAGE)
    return good / doc.page_count >= 0.5


def extract_native_text(doc: fitz.Document) -> str:
    return "\n\n".join(p.get_text() for p in doc)


def render_page(page: fitz.Page) -> Image.Image:
    pix = page.get_pixmap(dpi=config.RENDER_DPI)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def pdf_to_text(path: str, lang: str = "eng", force_ocr: bool = False, progress: Progress = None) -> str:
    doc = open_pdf(path)
    try:
        if not force_ocr and has_native_text(doc):
            return extract_native_text(doc)
        texts = []
        for i, page in enumerate(doc, start=1):
            texts.append(ocr.image_to_text(render_page(page), lang))
            if progress:
                progress(i, doc.page_count)
        return "\n\n".join(texts)
    finally:
        doc.close()


def pdf_to_searchable_pdf(path: str, out_path: str, lang: str = "eng", progress: Progress = None) -> None:
    doc = open_pdf(path)
    out = fitz.open()
    try:
        for i, page in enumerate(doc, start=1):
            pdf_bytes = ocr.image_to_pdf_bytes(render_page(page), lang)
            with fitz.open("pdf", pdf_bytes) as single:
                out.insert_pdf(single)
            if progress:
                progress(i, doc.page_count)
        out.save(out_path)
    finally:
        out.close()
        doc.close()
