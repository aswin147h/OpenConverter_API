"""Route adapters. Each takes (src, dst, lang, progress) and writes dst."""
from . import ocr, pdf


def image_to_txt(src, dst, lang="eng", progress=None):
    text = ocr.image_to_text(ocr.open_image(src), lang)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    if progress:
        progress(1, 1)


def image_to_searchable_pdf(src, dst, lang="eng", progress=None):
    data = ocr.image_to_pdf_bytes(ocr.open_image(src), lang)
    with open(dst, "wb") as f:
        f.write(data)
    if progress:
        progress(1, 1)


def pdf_to_txt(src, dst, lang="eng", progress=None):
    text = pdf.pdf_to_text(src, lang, progress=progress)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)


def pdf_to_searchable_pdf(src, dst, lang="eng", progress=None):
    pdf.pdf_to_searchable_pdf(src, dst, lang, progress=progress)
