"""Environment-driven settings and processing limits."""
import os

MAX_UPLOAD_BYTES = int(os.getenv("OC_MAX_UPLOAD_BYTES", 20 * 1024 * 1024))
MAX_PAGES = int(os.getenv("OC_MAX_PAGES", 30))
MAX_IMAGE_PIXELS = int(os.getenv("OC_MAX_IMAGE_PIXELS", 60_000_000))
OCR_TIMEOUT_SECONDS = int(os.getenv("OC_OCR_TIMEOUT", 60))  # per page
RENDER_DPI = int(os.getenv("OC_RENDER_DPI", 200))
RETENTION_SECONDS = int(os.getenv("OC_RETENTION_SECONDS", 3600))
ALLOWED_OCR_LANGUAGES = frozenset(
    x for x in os.getenv("OC_OCR_LANGS", "eng").split(",") if x
)
TESSERACT_CMD = os.getenv("OC_TESSERACT_CMD")
DATA_DIR = os.getenv("OC_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
