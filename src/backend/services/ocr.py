"""Document text extraction service.

Extracts text from selectable PDFs via pypdf, falling back to OCR
(PaddleOCR if available) for scanned documents and images.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Check optional PaddleOCR
try:
    from paddleocr import PaddleOCR  # type: ignore

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False


def clean_extracted_text(text: str) -> str:
    """Normalize extracted text by collapsing multiple blank lines and spaces."""
    if not text:
        return ""
    # Strip null bytes and non-printable control chars (except newline and tab)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Replace carriage returns
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Clean whitespace line by line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.split("\n")]
    result = "\n".join(lines)
    # Collapse 3+ newlines to 2
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_pdf_selectable_text(path: Path) -> str:
    """Extract embedded selectable text from a PDF file using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages_text: list[str] = []
    for index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages_text.append(f"--- Page {index + 1} ---\n{page_text}")
    return "\n\n".join(pages_text)


def extract_image_ocr(path: Path) -> str:
    """Extract text from an image or scanned document using PaddleOCR if installed."""
    if not _PADDLE_AVAILABLE:
        logger.warning("PaddleOCR not installed; cannot OCR image or scanned document.")
        return ""

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en")
        results = ocr.ocr(str(path), cls=True)
        lines: list[str] = []
        if results and results[0]:
            for line in results[0]:
                if line and len(line) >= 2 and line[1]:
                    text, _confidence = line[1]
                    if text:
                        lines.append(str(text))
        return "\n".join(lines)
    except Exception as exc:
        logger.error("PaddleOCR execution failed: %s", exc)
        return ""


def extract_text_from_file(file_path: Path | str, file_type: str) -> tuple[str, str]:
    """Extract text from document.

    Returns:
        tuple[str, str]: (extracted_text, extraction_method)
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found: {path}")

    norm_type = file_type.lower().lstrip(".")

    if norm_type == "pdf":
        try:
            pdf_text = extract_pdf_selectable_text(path)
            cleaned = clean_extracted_text(pdf_text)
            # If significant selectable text was extracted, return it
            if len(cleaned.strip()) >= 30:
                return cleaned, "pdf_text"
        except Exception as exc:
            logger.warning("pypdf extraction failed on %s: %s", path.name, exc)

        # Scanned PDF fallback
        ocr_text = extract_image_ocr(path)
        cleaned_ocr = clean_extracted_text(ocr_text)
        if cleaned_ocr:
            return cleaned_ocr, "paddleocr"
        return clean_extracted_text(pdf_text if "pdf_text" in locals() else ""), "pdf_text_partial"

    if norm_type in {"png", "jpg", "jpeg"}:
        ocr_text = extract_image_ocr(path)
        cleaned_ocr = clean_extracted_text(ocr_text)
        method = "paddleocr" if cleaned_ocr else "ocr_unavailable"
        return cleaned_ocr, method

    return "", "unsupported_type"
