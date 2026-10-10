"""HTTP integration for the directory and private organizer submissions."""

import os
import re
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, AsyncIterator, Literal
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import crud
from backend.auth import ALLOWED_ORIGINS, CurrentUser, AdminUser, cleanup_expired_sessions, router as auth_router
from backend.admin import router as admin_router
from backend.database import SessionLocal, get_db, init_db
from backend.security import require_rate_limit, submit_limiter
from backend.models import (
    Campaign,
    Document,
    DonationQRCode,
    ExtractionResult,
    FundUpdate,
)

from backend.schemas import (
    CampaignCreate,
    CampaignListPaginated,
    CampaignResponse,
    DocumentWithExtraction,
    ExtractionResultFull,
    ExtractionResultResponse,
    PublicCampaign,
    PublicFinding,
    PublicFundEntry,
    ReportCreate,
    SubmissionResponse,
)

from backend.services.scoring import MIN_VERIFICATION_SCORE
from backend.services.pipeline import extract_documents, run_document_extraction

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
    with SessionLocal() as session:
        cleanup_expired_sessions(session)
    yield


app = FastAPI(title="PanataanPH API", lifespan=lifespan)
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(auth_router)
app.include_router(admin_router)
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
    filters = dict(public_only=True, search=search, location=location, cause=cause, urgency=urgency)
    return {
        "items": crud.list_campaigns(db, **filters, skip=skip, limit=limit),
        "total": crud.count_campaigns(db, **filters),
        "skip": skip,
        "limit": limit,
    }


@app.get("/api/campaigns/{public_id}", response_model=PublicCampaign)
def campaign(public_id: str, db: Database) -> dict:
    result = published_campaign(public_id, db)
    public = CampaignResponse.model_validate(result).model_dump()
    public["findings"] = [PublicFinding.model_validate(finding) for finding in result.findings]
    public["minimum_score"] = MIN_VERIFICATION_SCORE
    latest_review = max(result.reviews, key=lambda review: review.id, default=None)
    public["threshold_overridden"] = bool(
        result.verification_score is not None and result.verification_score < MIN_VERIFICATION_SCORE
        and latest_review and latest_review.threshold_override and latest_review.warnings_resolved
        and latest_review.override_reason and latest_review.decision == "verified" and latest_review.new_status == "verified"
    )
    public["qr_codes"] = [
        {"public_id": qr.public_id, "label": qr.label,
         "image_url": f"/api/campaigns/{public_id}/qr/{qr.public_id}"}
        for qr in result.qr_codes
    ]
    entries = [PublicFundEntry.model_validate(entry) for entry in result.fund_updates if entry.status == "approved"]
    received = sum(entry.amount_centavos for entry in entries if entry.kind == "received")
    spent = sum(entry.amount_centavos for entry in entries if entry.kind == "spent")
    public["transparency"] = {
        "received_centavos": received, "spent_centavos": spent,
        "balance_centavos": received - spent,
        "entries": sorted(entries, key=lambda entry: (entry.occurred_on, entry.public_id), reverse=True),
    }
    return public


def published_campaign(public_id: str, db: Session) -> Campaign:
    result = db.scalar(select(Campaign).where(Campaign.public_id == public_id, crud.public_campaign_filter()))
    if result is None:
        raise HTTPException(404, "Campaign not found")
    return result


@app.post(
    "/api/campaigns/{public_id}/report",
    status_code=201,
    dependencies=[Depends(require_rate_limit(submit_limiter, "report"))],
)
def report_campaign(public_id: str, data: ReportCreate, db: Database) -> dict:
    target = crud.get_campaign_by_public_id(db, public_id)
    if target is None:
        raise HTTPException(404, "Campaign not found")
    report = crud.create_report(
        db,
        campaign_id=target.id,
        reason=data.reason,
        reporter_name=data.reporter_name,
        reporter_email=data.reporter_email,
    )
    return {"status": "submitted", "report_id": report.id}



def private_file(path: str, file_type: str) -> FileResponse:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(STORAGE_ROOT.resolve()) or not resolved.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(resolved, media_type={"png": "image/png", "jpg": "image/jpeg", "pdf": "application/pdf"}[file_type],
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/campaigns/{public_id}/qr/{qr_id}")
def donation_qr(public_id: str, qr_id: str, db: Database) -> FileResponse:
    owner_campaign = published_campaign(public_id, db)
    qr = db.scalar(select(DonationQRCode).where(DonationQRCode.public_id == qr_id, DonationQRCode.campaign_id == owner_campaign.id))
    if qr is None:
        raise HTTPException(404, "Donation QR not found")
    return private_file(qr.storage_path, qr.file_type)


@app.get("/api/admin/qr/{qr_id}")
def review_qr(qr_id: str, db: Database, admin: AdminUser) -> FileResponse:
    qr = db.scalar(select(DonationQRCode).where(DonationQRCode.public_id == qr_id))
    if qr is None:
        raise HTTPException(404, "Donation QR not found")
    return private_file(qr.storage_path, qr.file_type)


async def save_upload(upload: UploadFile, saved: list[Path], *, image_only: bool = False) -> tuple[Path, str, str, int]:
    filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    filename = re.sub(r"[^\w. -]", "_", filename)[:255]
    extension = Path(filename).suffix.lower()
    file_type = FILE_TYPES.get(extension)
    if file_type is None or upload.content_type != file_type[0] or (image_only and file_type[2] == "pdf"):
        raise HTTPException(415, "Donation QR must be JPG/PNG; supporting documents must be PDF, JPG, or PNG")
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
    return path, filename, file_type[2], len(contents)


@app.post(
    "/api/submissions",
    response_model=SubmissionResponse,
    status_code=201,
    dependencies=[Depends(require_rate_limit(submit_limiter, "submissions"))],
)
async def submit_campaign(
    db: Database,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    campaign: Annotated[str, Form()],
    documents: Annotated[list[UploadFile], File()],
    donation_qr: Annotated[UploadFile | None, File()] = None,
    qr_label: Annotated[str, Form(max_length=100)] = "",
) -> SubmissionResponse:
    """Save a pending submission and its files as one transaction.

    Files stay in private storage. Local extraction runs after saving;
    scoring and campaign approval require human review.
    """
    if user.role in {"admin", "lgu"}:
        raise HTTPException(403, "Reviewer accounts cannot submit fundraising campaigns")
    saved: list[Path] = []
    try:
        try:
            data = CampaignCreate.model_validate_json(campaign)
        except ValidationError as error:
            raise HTTPException(422, error.errors(include_input=False, include_context=False)) from error
        if not 1 <= len(documents) <= MAX_DOCUMENTS:
            raise HTTPException(422, "Provide between 1 and 4 supporting documents")
        if donation_qr and not qr_label.strip():
            raise HTTPException(422, "Name the donation method for this QR image")

        metadata: list[tuple[Path, str, str, int]] = []
        for upload in documents:
            metadata.append(await save_upload(upload, saved))
        qr_metadata = await save_upload(donation_qr, saved, image_only=True) if donation_qr else None

        result = crud.create_campaign(db, commit=False, owner_id=user.id, **data.model_dump())
        document_ids: list[int] = []
        for path, filename, file_type_name, size in metadata:
            document = crud.create_document(
                db, result.id, str(path), filename, file_type_name, size, commit=False
            )
            document_ids.append(document.id)
        if qr_metadata:
            db.add(DonationQRCode(public_id=str(uuid4()), campaign_id=result.id, label=qr_label.strip(),
                                  storage_path=str(qr_metadata[0]), file_type=qr_metadata[2]))
        response = SubmissionResponse(public_id=result.public_id, documents_received=len(metadata))
        db.commit()
        background_tasks.add_task(extract_documents, document_ids, db.get_bind())
        return response
    except Exception:
        db.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in documents:
            await upload.close()
        if donation_qr:
            await donation_qr.close()


@app.get("/api/my/campaigns", response_model=list[CampaignResponse])
def my_campaigns(db: Database, user: CurrentUser) -> list[dict]:
    owned = db.scalars(select(Campaign).where(Campaign.owner_id == user.id).order_by(Campaign.created_at.desc())).all()
    responses = []
    for item in owned:
        response = CampaignResponse.model_validate(item).model_dump()
        feedback = max((review for review in item.reviews if review.decision != "information_submitted"),
                       key=lambda review: review.id, default=None)
        if feedback:
            response["admin_notes"] = feedback.reason
        responses.append(response)
    return responses


class EvidenceResponse(BaseModel):
    public_id: str
    status: Literal["under_review"]
    documents_received: int


@app.post("/api/my/campaigns/{public_id}/documents", response_model=EvidenceResponse, status_code=201)
async def provide_evidence(public_id: str, db: Database, user: CurrentUser,
                           background_tasks: BackgroundTasks,
                           documents: Annotated[list[UploadFile], File()]) -> EvidenceResponse:
    saved: list[Path] = []
    try:
        result = owned_campaign(public_id, db, user.id)
        if result.status != "needs_information":
            raise HTTPException(409, "Additional evidence is accepted when requested by a reviewer")
        if not 1 <= len(documents) <= MAX_DOCUMENTS:
            raise HTTPException(422, "Provide between 1 and 4 supporting documents")
        document_ids: list[int] = []
        for upload in documents:
            path, filename, file_type, size = await save_upload(upload, saved)
            document = crud.create_document(db, result.id, str(path), filename, file_type, size, commit=False)
            document_ids.append(document.id)
        result.verification_score = None
        result.score_breakdown = None
        result.findings.clear()
        crud.create_review(db, result.id, f"organizer:{user.id}", "information_submitted",
                           "Organizer provided additional evidence for review", "needs_information", "under_review")
        background_tasks.add_task(extract_documents, document_ids, db.get_bind())
        return EvidenceResponse(public_id=result.public_id, status="under_review", documents_received=len(documents))
    except Exception:
        db.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    finally:
        for upload in documents:
            await upload.close()


def owned_campaign(public_id: str, db: Session, user_id: int) -> Campaign:
    result = db.scalar(select(Campaign).where(Campaign.public_id == public_id, Campaign.owner_id == user_id))
    if result is None:
        raise HTTPException(404, "Campaign not found")
    return result


class FundUpdateCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    kind: Literal["received", "spent"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    description: str = Field(min_length=1, max_length=1000)
    occurred_on: date

    @field_validator("occurred_on")
    @classmethod
    def no_future_dates(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Fund reports cannot be dated in the future")
        return value


class FundUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: str
    kind: Literal["received", "spent"]
    amount_centavos: int
    description: str
    occurred_on: date
    status: Literal["pending", "approved", "rejected"]
    review_reason: str | None


@app.get("/api/my/campaigns/{public_id}/funds", response_model=list[FundUpdateResponse])
def my_funds(public_id: str, db: Database, user: CurrentUser) -> list[FundUpdate]:
    result = owned_campaign(public_id, db, user.id)
    return sorted(result.fund_updates, key=lambda entry: entry.created_at, reverse=True)


@app.post("/api/my/campaigns/{public_id}/funds", response_model=FundUpdateResponse, status_code=201)
def report_funds(public_id: str, data: FundUpdateCreate, db: Database, user: CurrentUser) -> FundUpdate:
    result = owned_campaign(public_id, db, user.id)
    if result.status != "verified":
        raise HTTPException(409, "Fund updates require a verified campaign")
    entry = FundUpdate(public_id=str(uuid4()), campaign_id=result.id, kind=data.kind,
                       amount_centavos=int(data.amount * 100), description=data.description, occurred_on=data.occurred_on)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@app.get("/api/documents/{document_id}", response_model=DocumentWithExtraction)
def get_document(document_id: int, db: Database, admin: AdminUser) -> Document:
    doc = crud.get_document_by_id(db, document_id)

    if doc is None:
        raise HTTPException(404, "Document not found")

    return doc


@app.post(
    "/api/documents/{document_id}/extract",
    response_model=ExtractionResultResponse
)
async def extract_document(
    document_id: int,
    db: Database,
    admin: AdminUser,
) -> ExtractionResult:

    doc = crud.get_document_by_id(
        db,
        document_id
    )

    if doc is None:
        raise HTTPException(
            404,
            "Document not found"
        )

    try:
        result = await run_document_extraction(
            db,
            document_id
        )

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            404,
            str(exc)
        ) from exc

    except Exception as exc:
        raise HTTPException(
            500,
            f"Extraction failed: {exc}"
        ) from exc


@app.get(
    "/api/documents/{document_id}/extraction",
    response_model=ExtractionResultFull
)
def get_document_extraction(
    document_id: int,
    db: Database,
    admin: AdminUser,
) -> ExtractionResult:

    doc = crud.get_document_by_id(
        db,
        document_id
    )

    if doc is None:
        raise HTTPException(
            404,
            "Document not found"
        )

    result = crud.get_extraction_by_document(
        db,
        document_id
    )

    if result is None:
        raise HTTPException(
            404,
            "Extraction result not found for this document"
        )

    return result

class FundReview(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    status: Literal["approved", "rejected"]
    reason: str = Field(min_length=1, max_length=1000)


@app.patch("/api/admin/fund-updates/{public_id}", response_model=FundUpdateResponse)
def review_funds(public_id: str, data: FundReview, db: Database, admin: AdminUser) -> FundUpdate:
    entry = db.scalar(select(FundUpdate).where(FundUpdate.public_id == public_id))
    if entry is None:
        raise HTTPException(404, "Fund report not found")
    if entry.status != "pending":
        raise HTTPException(409, "Fund report already reviewed")
    entry.status = data.status
    entry.reviewed_by = admin.id
    entry.review_reason = data.reason
    db.commit()
    db.refresh(entry)
    return entry
