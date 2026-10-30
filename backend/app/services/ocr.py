"""Tesseract adapter (arguments passed as arrays by pytesseract; timeout enforced)."""
import os
import shutil

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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


def _prepare_image(image: Image.Image) -> Image.Image:
    """Normalize low-quality scans before Tesseract without changing the original output image."""
    prepared = ImageOps.exif_transpose(image).convert("RGB")
    prepared = ImageOps.grayscale(prepared)
    prepared = ImageOps.autocontrast(prepared, cutoff=1)
    prepared = ImageEnhance.Contrast(prepared).enhance(1.25)

    width, height = prepared.size
    longest = max(width, height)
    if longest and longest < 1800:
        scale = min(3.0, 1800 / longest)
        prepared = prepared.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.LANCZOS,
        )

    return prepared.filter(ImageFilter.MedianFilter(size=3))


def _ocr_text(image: Image.Image, lang: str, psm: int = 3) -> str:
    config_text = f"--psm {psm} --oem 1 preserve_interword_spaces=1"
    return pytesseract.image_to_string(
        image,
        lang=lang,
        config=config_text,
        timeout=config.OCR_TIMEOUT_SECONDS,
    )


def image_to_text(image: Image.Image, lang: str = "eng") -> str:
    lang = check_language(lang)
    try:
        prepared = _prepare_image(image)
        text = _ocr_text(prepared, lang).strip()
        if len(text) < 20:
            fallback = _ocr_text(prepared, lang, psm=6).replace("\n\n", "\n")
            if len(fallback) > len(text):
                text = fallback
        return "\n".join(line.rstrip() for line in text.splitlines()).strip()
    except RuntimeError as exc:  # pytesseract raises RuntimeError on timeout
        raise ConversionError("ocr_timeout", "OCR timed out.") from exc


def image_to_pdf_bytes(image: Image.Image, lang: str = "eng") -> bytes:
    """Single-page PDF: original image plus invisible OCR text layer."""
    lang = check_language(lang)
    try:
        prepared = _prepare_image(image)
        return pytesseract.image_to_pdf_or_hocr(
            prepared,
            lang=lang,
            extension="pdf",
            config="--psm 3 --oem 1",
            timeout=config.OCR_TIMEOUT_SECONDS,
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
