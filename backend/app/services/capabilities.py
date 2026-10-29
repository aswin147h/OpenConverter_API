"""Explicit supported conversion matrix. Only routes with automated tests belong here."""
from . import conversion

# (input_kind, output_format) -> adapter
ROUTES = {
    ("image", "txt"): conversion.image_to_txt,
    ("image", "pdf"): conversion.image_to_searchable_pdf,
    ("pdf", "txt"): conversion.pdf_to_txt,
    ("pdf", "pdf"): conversion.pdf_to_searchable_pdf,
    ("pdf", "docx"): conversion.pdf_to_docx,
    ("docx", "txt"): conversion.docx_to_txt,
    ("docx", "pdf"): conversion.docx_to_pdf,
    ("xlsx", "csv"): conversion.xlsx_to_csv,
    ("xlsx", "pdf"): conversion.xlsx_to_pdf,
    ("pptx", "pdf"): conversion.pptx_to_pdf,
}

IMAGE_EXTS = {"jpg", "jpeg", "png", "tif", "tiff"}


def kind_for_extension(ext: str):
    ext = ext.lower().lstrip(".")
    if ext in IMAGE_EXTS:
        return "image"
    if ext == "pdf":
        return "pdf"
    if ext == "docx":
        return "docx"
    if ext == "xlsx":
        return "xlsx"
    if ext == "pptx":
        return "pptx"
    return None


def outputs_for(kind: str):
    return sorted({out for (k, out) in ROUTES if k == kind})


def get_adapter(kind: str, target: str):
    return ROUTES.get((kind, target))
