"""Text extraction: PDF text layer first (PyMuPDF), Tesseract OCR fallback for scans/images.

Most university question papers are digital PDFs with an embedded text layer, so OCR is
the exception path, not the default (Implmentation-01.md §4 Step 1).
"""

from pathlib import Path

import fitz  # PyMuPDF

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

# Below this many characters per page on average, assume the PDF is a scan without
# a usable text layer and fall back to OCR.
MIN_CHARS_PER_PAGE = 50

# Render scale for OCR rasterization; 300 dpi equivalent (72 * ~4.17)
OCR_ZOOM = 300 / 72


class ExtractionError(Exception):
    pass


def _ocr_image_bytes(png_bytes: bytes) -> str:
    try:
        import io

        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ExtractionError(
            "This file needs OCR but pytesseract/Pillow are not installed."
        ) from exc

    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(png_bytes)))
    except pytesseract.TesseractNotFoundError as exc:
        raise ExtractionError(
            "This file needs OCR but the Tesseract binary was not found. "
            "Install it from https://github.com/UB-Mannheim/tesseract/wiki and ensure it is on PATH."
        ) from exc


def _ocr_pdf(doc: fitz.Document) -> str:
    pages = []
    matrix = fitz.Matrix(OCR_ZOOM, OCR_ZOOM)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        pages.append(_ocr_image_bytes(pix.tobytes("png")))
    return "\n".join(pages)


def extract_text(file_path: str | Path) -> str:
    """Return the full text of a PDF or image file. Raises ExtractionError if nothing
    usable can be extracted."""
    path = Path(file_path)

    if path.suffix.lower() in IMAGE_EXTENSIONS:
        text = _ocr_image_bytes(path.read_bytes())
    elif path.suffix.lower() == ".pdf":
        with fitz.open(path) as doc:
            if doc.page_count == 0:
                raise ExtractionError("PDF has no pages.")
            text = "\n".join(page.get_text() for page in doc)
            if len(text.strip()) < MIN_CHARS_PER_PAGE * doc.page_count:
                # No usable text layer -> scanned PDF -> OCR each page
                text = _ocr_pdf(doc)
    else:
        raise ExtractionError(f"Unsupported file type: {path.suffix}. Upload a PDF or image.")

    if not text.strip():
        raise ExtractionError("No text could be extracted from the file.")
    return text
