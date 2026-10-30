from io import BytesIO

import fitz
from PIL import Image
import zipfile
from .. import config

from ..errors import ConversionError


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "tif", "tiff"}


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_upload(filename: str, content: bytes, max_bytes: int, max_pages: int):
    if len(content) > max_bytes:
        raise ConversionError("upload_too_large", "The upload exceeds the configured size limit.")

    extension = _extension(filename)
    if extension == "pdf":
        try:
            if not content.startswith(b"%PDF-"):
                raise ConversionError("invalid_pdf", "The uploaded PDF could not be read.")
            with fitz.open("pdf", content) as doc:
                if doc.needs_pass:
                    raise ConversionError("encrypted_pdf", "Password-protected PDFs are not supported.")
                if doc.page_count == 0:
                    raise ConversionError("invalid_pdf", "The uploaded PDF is empty or invalid.")
                if doc.page_count > max_pages:
                    raise ConversionError("too_many_pages", "The uploaded PDF exceeds the page limit.")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("invalid_pdf", "The uploaded PDF could not be read.") from exc
        return "pdf"

    if extension in IMAGE_EXTENSIONS:
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                if width * height > config.MAX_IMAGE_PIXELS:
                    raise ConversionError("image_too_large", "The image exceeds the configured pixel limit.")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("invalid_image", "The uploaded image could not be read.") from exc
        return "image"

    if extension == "docx":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                if "word/document.xml" not in names:
                    raise ConversionError("invalid_docx", "The uploaded Word document could not be read.")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("invalid_docx", "The uploaded Word document could not be read.") from exc
        return "docx"

    if extension == "xlsx":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                    raise ConversionError("invalid_xlsx", "The uploaded Excel workbook could not be read.")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("invalid_xlsx", "The uploaded Excel workbook could not be read.") from exc
        return "xlsx"

    if extension == "pptx":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
                    raise ConversionError("invalid_pptx", "The uploaded PowerPoint file could not be read.")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("invalid_pptx", "The uploaded PowerPoint file could not be read.") from exc
        return "pptx"

    raise ConversionError("unsupported_file_type", "The uploaded file type is not supported.")