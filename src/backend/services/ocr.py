"""Document text extraction service.

Extracts text from selectable PDFs via pypdf, falling back to OCR
(PaddleOCR if available) for scanned documents and images.
"""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

_OCR_LOCK = Lock()


class TextExtractionError(RuntimeError):
    """OCR cannot run or the document contains no readable text."""


@lru_cache(maxsize=1)
def get_ocr() -> PaddleOCR:
    """Load local CPU models once; downloads occur only during initial setup."""
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise TextExtractionError(
            "OCR dependencies missing. Install src/backend/requirements-ocr.txt and restart the backend."
        ) from exc
    # MKL-DNN fails on these OCR models with the Windows CPU runtime.
    return PaddleOCR(
        lang="en", device="cpu", ocr_version="PP-OCRv5", enable_mkldnn=False,
        use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False,
    )


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
    """Extract all image/PDF pages using PaddleOCR 3.x locally."""
    try:
        with _OCR_LOCK:
            results = get_ocr().predict(str(path))
            lines = [text for page in results for text in page["rec_texts"] if text]
        return "\n".join(lines)
    except TextExtractionError:
        raise
    except Exception as exc:
        logger.error("PaddleOCR execution failed: %s", exc)
        raise TextExtractionError(f"Local OCR failed: {exc}") from exc


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
            if cleaned:
                return cleaned, "pdf_text"
        except Exception as exc:
            logger.warning("pypdf extraction failed on %s: %s", path.name, exc)
            raise TextExtractionError("PDF could not be read. Upload a valid, unencrypted PDF.") from exc

        # Scanned PDF fallback
        ocr_text = extract_image_ocr(path)
        cleaned_ocr = clean_extracted_text(ocr_text)
        if cleaned_ocr:
            return cleaned_ocr, "paddleocr"
        raise TextExtractionError("No readable text found in this PDF. Upload a clearer document.")

    if norm_type in {"png", "jpg", "jpeg"}:
        ocr_text = extract_image_ocr(path)
        cleaned_ocr = clean_extracted_text(ocr_text)
        if not cleaned_ocr:
            raise TextExtractionError("No readable text found in this image. Upload a clearer document.")
        return cleaned_ocr, "paddleocr"

    return "", "unsupported_type"
