import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont


def _text_image(text="Hello OpenConvert 12345", size=(900, 200)):
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((30, 60), text, fill="black", font=font)
    return img


@pytest.fixture
def image_path(tmp_path):
    p = tmp_path / "scan.png"
    _text_image().save(p)
    return str(p)


@pytest.fixture
def text_pdf(tmp_path):
    p = tmp_path / "text.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Native text layer document for OpenConvert testing.", fontsize=14)
    doc.save(p)
    return str(p)


@pytest.fixture
def scanned_pdf(tmp_path, image_path):
    p = tmp_path / "scanned.pdf"
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=612, height=200)
        page.insert_image(page.rect, filename=image_path)
    doc.save(p)
    return str(p)
