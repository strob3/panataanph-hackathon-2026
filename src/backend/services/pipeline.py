"""Document processing pipeline coordinator.

Orchestrates:
1. File lookup
2. Text extraction via pypdf / OCR
3. Structured field extraction via local Ollama
4. Database record creation (ExtractionResult)
5. Document status updates
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend import crud
from backend.models import Document, ExtractionResult
from backend.services import llm, ocr

logger = logging.getLogger(__name__)


async def extract_documents(document_ids: list[int], bind: Engine | Connection) -> None:
    """Process committed uploads with a separate session after the response."""
    with Session(bind) as db:
        for document_id in document_ids:
            try:
                await run_document_extraction(db, document_id)
            except Exception:
                db.rollback()
                crud.update_document_status(db, document_id, "failed")
                logger.exception("Background extraction failed for document %s", document_id)


async def run_document_extraction(
    db: Session,
    document_id: int,
    *,
    allow_offline_fallback: bool = True,
) -> ExtractionResult:
    """Execute the extraction pipeline for a single document.

    Updates document.processing_status and saves ExtractionResult.
    """
    document: Document | None = crud.get_document_by_id(db, document_id)
    if document is None:
        raise ValueError(f"Document with ID {document_id} not found")

    file_path = Path(document.storage_path)
    if not file_path.exists():
        crud.update_document_status(db, document_id, "failed")
        raise FileNotFoundError(f"Document file does not exist on disk: {file_path}")

    # Step 1: Mark processing
    crud.update_document_status(db, document_id, "processing")

    raw_text = ""
    text_error: str | None = None
    # Step 2: Extract raw text without blocking HTTP requests.
    try:
        raw_text, extraction_method = await run_in_threadpool(ocr.extract_text_from_file, file_path, document.file_type)
        if not raw_text.strip():
            raise ocr.TextExtractionError("No readable text found. Upload a clearer document.")
    except ocr.TextExtractionError as exc:
        text_error = str(exc)
        extraction_method = "failed"
    except Exception as exc:
        logger.error("Text extraction failed for document %s: %s", document_id, exc)
        crud.update_document_status(db, document_id, "failed")
        raise

    # Step 3: Run Ollama LLM extraction
    raw_llm_json: str | None = None
    confidence_notes: str | None = f"Extracted via {extraction_method}"
    extracted_fields = llm.sanitize_extracted_data({})

    try:
        if text_error:
            confidence_notes = f"Text extraction failed: {text_error}"
        else:
            extracted_fields, raw_llm_json = await llm.call_ollama_extraction(raw_text)
    except (llm.OllamaUnavailableError, llm.OllamaServiceError) as exc:
        logger.warning("Ollama extraction unavailable for doc %s: %s", document_id, exc)
        if not allow_offline_fallback:
            crud.update_document_status(db, document_id, "failed")
            raise
        confidence_notes = f"LLM offline ({exc}); saved raw text only"
        extracted_fields = llm.sanitize_extracted_data({"missing_fields": llm.EXTRACTION_FIELDS})

    # Step 4: Persist ExtractionResult
    existing_result = crud.get_extraction_by_document(db, document_id)
    missing_fields_json = json.dumps(extracted_fields.missing_fields)

    extraction_dict = {
        "document_type": extracted_fields.document_type,
        "issuing_authority": extracted_fields.issuing_authority,
        "permit_number": extracted_fields.permit_number,
        "organization_name": extracted_fields.organization_name,
        "purpose": extracted_fields.purpose,
        "issue_date": extracted_fields.issue_date,
        "expiration_date": extracted_fields.expiration_date,
        "beneficiaries": extracted_fields.beneficiaries,
        "missing_fields": missing_fields_json,
        "raw_ocr_text": raw_text or None,
        "raw_llm_response": raw_llm_json,
        "confidence_notes": confidence_notes,
    }

    if existing_result is not None:
        result = crud.update_extraction_result(db, existing_result.id, **extraction_dict)
    else:
        result = crud.create_extraction_result(db, document_id=document_id, **extraction_dict)

    # Step 5: Mark document completed
    crud.update_document_status(db, document_id, "failed" if text_error else "completed")
    return result
