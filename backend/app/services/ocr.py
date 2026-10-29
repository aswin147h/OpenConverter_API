"""Tesseract adapter (arguments passed as arrays by pytesseract; timeout enforced)."""
import os
import shutil

from PIL import Image
import pytesseract

from .. import config
from ..errors import ConversionError

Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS


def _configure_tesseract() -> None:
    candidates = [
        config.TESSERACT_CMD,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


_configure_tesseract()


def check_language(lang: str) -> str:
    parts = lang.split("+")
    if not parts or any(p not in config.ALLOWED_OCR_LANGUAGES for p in parts):
        raise ConversionError("invalid_language", "OCR language is not supported.")
    return lang


def image_to_text(image: Image.Image, lang: str = "eng") -> str:
    lang = check_language(lang)
    try:
        return pytesseract.image_to_string(image, lang=lang, timeout=config.OCR_TIMEOUT_SECONDS)
    except RuntimeError as exc:  # pytesseract raises RuntimeError on timeout
        raise ConversionError("ocr_timeout", "OCR timed out.") from exc


def image_to_pdf_bytes(image: Image.Image, lang: str = "eng") -> bytes:
    """Single-page PDF: original image plus invisible OCR text layer."""
    lang = check_language(lang)
    try:
        return pytesseract.image_to_pdf_or_hocr(
            image, lang=lang, extension="pdf", timeout=config.OCR_TIMEOUT_SECONDS
        )
    except RuntimeError as exc:
        raise ConversionError("ocr_timeout", "OCR timed out.") from exc


def open_image(path: str) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
        return img.convert("RGB")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ConversionError("invalid_image", "Image could not be read.") from exc
