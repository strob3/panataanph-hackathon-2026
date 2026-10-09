"""HTTP integration for the directory and private organizer submissions."""

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend import crud
from backend.database import get_db, init_db
from backend.models import Campaign, Document, ExtractionResult
from backend.schemas import (
    CampaignCreate,
    CampaignListPaginated,
    DocumentWithExtraction,
    ExtractionResultFull,
    ExtractionResultResponse,
    PublicCampaign,
    SubmissionResponse,
)
from backend.services.pipeline import run_document_extraction

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENTS = 4
STORAGE_ROOT = Path(os.getenv(
    "PANATAANPH_STORAGE_PATH", str(Path(__file__).resolve().parents[2] / "storage")
))
FILE_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-", "pdf"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n", "png"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff", "jpg"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff", "jpg"),
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="PanataanPH API", lifespan=lifespan)
Database = Annotated[Session, Depends(get_db)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/campaigns", response_model=CampaignListPaginated)
def campaigns(
    db: Database,
    search: str | None = None,
    location: str | None = None,
    cause: str | None = None,
    urgency: str | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    filters = dict(status="verified", search=search, location=location, cause=cause, urgency=urgency)
    return {
        "items": crud.list_campaigns(db, **filters, skip=skip, limit=limit),
        "total": crud.count_campaigns(db, **filters),
        "skip": skip,
        "limit": limit,
    }


@app.get("/api/campaigns/{public_id}", response_model=PublicCampaign)
def campaign(public_id: str, db: Database) -> Campaign:
    result = crud.get_campaign_by_public_id(db, public_id)
    if result is None or result.status != "verified":
        raise HTTPException(404, "Campaign not found")
    return result


@app.post("/api/submissions", response_model=SubmissionResponse, status_code=201)
async def submit_campaign(
    db: Database,
    campaign: Annotated[str, Form()],
    documents: Annotated[list[UploadFile], File()],
) -> SubmissionResponse:
    """Save a pending submission and its files as one transaction.

    Files stay in private storage. Extraction/scoring and admin approval are
    separate workflows; this endpoint never infers evidence or approves a drive.
    """
    saved: list[Path] = []
    try:
        try:
            data = CampaignCreate.model_validate_json(campaign)
        except ValidationError as error:
            raise HTTPException(422, error.errors(include_input=False, include_context=False)) from error
        if not 1 <= len(documents) <= MAX_DOCUMENTS:
            raise HTTPException(422, "Provide between 1 and 4 supporting documents")

        metadata: list[tuple[Path, str, str, int]] = []
        for upload in documents:
            filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
            filename = re.sub(r"[^\w. -]", "_", filename)[:255]
            extension = Path(filename).suffix.lower()
            file_type = FILE_TYPES.get(extension)
            if file_type is None or upload.content_type != file_type[0]:
                raise HTTPException(415, "Only PDF, JPG, and PNG documents are supported")
            contents = await upload.read(MAX_FILE_BYTES + 1)
            if len(contents) > MAX_FILE_BYTES:
                raise HTTPException(413, "Each document must be at most 10 MB")
            if not contents.startswith(file_type[1]):
                raise HTTPException(415, "Document contents do not match the declared file type")
            STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
            path = STORAGE_ROOT / f"{uuid4().hex}{extension}"
            saved.append(path)
            with path.open("xb") as destination:
                destination.write(contents)
            metadata.append((path, filename, file_type[2], len(contents)))

        result = crud.create_campaign(db, commit=False, **data.model_dump())
        for path, filename, file_type_name, size in metadata:
            crud.create_document(
                db, result.id, str(path), filename, file_type_name, size, commit=False
            )
        response = SubmissionResponse(public_id=result.public_id, documents_received=len(metadata))
        db.commit()
        return response
    except Exception:
        db.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in documents:
            await upload.close()


@app.get("/api/documents/{document_id}", response_model=DocumentWithExtraction)
def get_document(document_id: int, db: Database) -> Document:
    doc = crud.get_document_by_id(db, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.post("/api/documents/{document_id}/extract", response_model=ExtractionResultResponse)
async def extract_document(document_id: int, db: Database) -> ExtractionResult:
    doc = crud.get_document_by_id(db, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    try:
        result = await run_document_extraction(db, document_id)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}") from exc


@app.get("/api/documents/{document_id}/extraction", response_model=ExtractionResultFull)
def get_document_extraction(document_id: int, db: Database) -> ExtractionResult:
    doc = crud.get_document_by_id(db, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    result = crud.get_extraction_by_document(db, document_id)
    if result is None:
        raise HTTPException(404, "Extraction result not found for this document")
    return result
