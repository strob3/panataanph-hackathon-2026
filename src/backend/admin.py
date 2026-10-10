"""Authenticated human review with private evidence and auditable decisions."""

import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from backend import crud
from backend.auth import AdminUser, Database, UserResponse
from backend.models import AccountReview, Campaign, Document, User, VerificationFinding
from backend.services.llm import EXTRACTION_FIELDS, sanitize_extracted_data
from backend.schemas import ReportResolve
from backend.services.scoring import MIN_VERIFICATION_SCORE, score_campaign

router = APIRouter(prefix="/api/admin", tags=["admin review"])
Status = Literal["pending", "under_review", "needs_information", "verified", "rejected"]


class AccountDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verified: bool
    reason: str = Field(min_length=1, max_length=4000)


class CampaignDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["under_review", "needs_information", "verified", "rejected"]
    reason: str = Field(min_length=1, max_length=4000)
    permits: bool = False
    identity: bool = False
    consistency: bool = False
    history: bool = False
    override_threshold: bool = False
    override_reason: str | None = Field(default=None, max_length=4000)
    warnings_resolved: bool = False


def campaign_summary(campaign: Campaign) -> dict:
    names = ["id", "public_id", "title", "status", "organizer_name", "location", "target_amount", "verification_score", "created_at"]
    return {**{name: getattr(campaign, name) for name in names}, "owner": UserResponse.model_validate(campaign.owner).model_dump() if campaign.owner else None}


def campaign_detail(campaign: Campaign) -> dict:
    names = ["description", "purpose", "cause", "beneficiaries", "organizer_email", "organizer_phone", "organization_name", "organization_registration_number", "payment_method", "payment_details", "urgency", "updated_at"]
    documents = []
    extraction_names = ["document_type", "issuing_authority", "permit_number", "organization_name", "purpose", "issue_date", "expiration_date", "beneficiaries", "missing_fields", "confidence_notes", "raw_ocr_text"]
    for document in campaign.documents:
        extraction = None
        if document.extraction_result:
            extraction = {name: getattr(document.extraction_result, name) for name in extraction_names}
            supported = sanitize_extracted_data(extraction, raw_text=extraction["raw_ocr_text"] or "")
            extraction.update({name: getattr(supported, name) for name in EXTRACTION_FIELDS})
            extraction["missing_fields"] = json.dumps(supported.missing_fields)
        documents.append({
            "id": document.id,
            "public_id": document.public_id,
            "original_filename": document.original_filename,
            "file_type": document.file_type,
            "file_size_bytes": document.file_size_bytes,
            "processing_status": document.processing_status,
            "url": f"/api/admin/documents/{document.public_id}",
            "extraction": extraction,
        })
    return {
        **campaign_summary(campaign),
        **{name: getattr(campaign, name) for name in names},
        "minimum_score": MIN_VERIFICATION_SCORE,
        "documents": documents,
        "qr_codes": [{"public_id": qr.public_id, "label": qr.label, "image_url": f"/api/admin/qr/{qr.public_id}"} for qr in campaign.qr_codes],
        "findings": [{name: getattr(finding, name) for name in ["criterion", "points_awarded", "points_possible", "details"]} for finding in campaign.findings],
        "reviews": [{name: getattr(review, name) for name in ["admin_username", "decision", "reason", "previous_status", "new_status", "reviewed_at", "threshold_override", "override_reason", "warnings_resolved"]} for review in sorted(campaign.reviews, key=lambda review: review.id, reverse=True)],
        "fund_updates": [{name: getattr(update, name) for name in ["public_id", "kind", "amount_centavos", "description", "occurred_on", "status", "review_reason", "created_at"]} for update in sorted(campaign.fund_updates, key=lambda update: update.id, reverse=True)],
        "reports": [
            {
                "id": report.id,
                "reason": report.reason,
                "reporter_name": report.reporter_name,
                "reporter_email": report.reporter_email,
                "status": report.status,
                "admin_response": report.admin_response,
                "created_at": report.created_at,
                "resolved_at": report.resolved_at,
            }
            for report in sorted(campaign.reports, key=lambda r: r.id, reverse=True)
        ],
    }


@router.get("/accounts")
def accounts(db: Database, user: AdminUser, skip: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 100) -> dict:
    users = db.scalars(select(User).order_by(User.verified, User.created_at.desc(), User.id.desc()).offset(skip).limit(limit)).all()
    return {"items": [UserResponse.model_validate(account) for account in users], "total": db.scalar(select(func.count(User.id))), "skip": skip, "limit": limit}


@router.patch("/accounts/{account_id}", response_model=UserResponse)
def review_account(account_id: int, data: AccountDecision, db: Database, reviewer: AdminUser) -> User:
    account = db.get(User, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")
    if account.role != "organizer":
        raise HTTPException(403, "Privileged accounts are managed locally")
    account.verified = data.verified
    db.add(AccountReview(user_id=account.id, reviewer_id=reviewer.id, verified=data.verified, reason=data.reason))
    db.commit()
    return account


@router.get("/campaigns")
def campaigns(db: Database, user: AdminUser, status: Status | None = None, skip: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 100) -> dict:
    return {"items": [campaign_summary(item) for item in crud.list_campaigns(db, status=status, skip=skip, limit=limit)], "total": crud.count_campaigns(db, status=status), "skip": skip, "limit": limit}


@router.get("/campaigns/{public_id}")
def campaign(public_id: str, db: Database, user: AdminUser) -> dict:
    result = crud.get_campaign_by_public_id(db, public_id)
    if result is None:
        raise HTTPException(404, "Campaign not found")
    return campaign_detail(result)


@router.get("/documents/{public_id}")
def document(public_id: str, db: Database, user: AdminUser) -> FileResponse:
    # Local import shares the configured upload root without circular imports.
    from backend.main import STORAGE_ROOT

    result = db.scalar(select(Document).where(Document.public_id == public_id))
    if result is None:
        raise HTTPException(404, "Document not found")
    path = Path(result.storage_path).resolve()
    if not path.is_relative_to(STORAGE_ROOT.resolve()) or not path.is_file():
        raise HTTPException(404, "Document not found")
    media_types = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg"}
    return FileResponse(path, filename=result.original_filename, media_type=media_types.get(result.file_type, "application/octet-stream"), headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/campaigns/{public_id}/review")
def review_campaign(public_id: str, data: CampaignDecision, db: Database, reviewer: AdminUser) -> dict:
    result = crud.get_campaign_by_public_id(db, public_id)
    if result is None:
        raise HTTPException(404, "Campaign not found")
    transitions = {
        "pending": {"under_review"},
        "under_review": {"needs_information", "verified", "rejected"},
        "needs_information": {"under_review"},
        "verified": {"under_review"},
        "rejected": {"under_review"},
    }
    if data.decision not in transitions.get(result.status, set()):
        raise HTTPException(409, "Start or reopen review before making a final decision")
    findings = score_campaign(result, permits=data.permits, identity=data.identity, consistency=data.consistency, history=data.history)
    score = sum(item["points_awarded"] for item in findings)
    if data.override_threshold and data.decision != "verified":
        raise HTTPException(422, "Threshold exceptions apply only to an approval decision")
    if data.decision == "verified":
        if result.owner is None or not result.owner.verified:
            raise HTTPException(422, "Organizer account must be verified before publication")
        if not data.warnings_resolved:
            raise HTTPException(422, "Review and resolve warnings or major inconsistencies before approval")
        if data.override_threshold:
            if score >= MIN_VERIFICATION_SCORE:
                raise HTTPException(422, "Threshold exception is unnecessary when the score reaches the minimum")
            if not data.override_reason:
                raise HTTPException(422, "Record a nonblank reason for the threshold exception")
        elif score < MIN_VERIFICATION_SCORE:
            raise HTTPException(422, f"Evidence completeness score must reach {MIN_VERIFICATION_SCORE}; current score: {score}")
        elif not (data.permits and data.identity and data.consistency):
            raise HTTPException(422, "Confirm applicable authorizations, organizer identity, and donation detail consistency")
    result.findings.clear()
    for finding in findings:
        result.findings.append(VerificationFinding(**finding))
    result.verification_score = score
    result.score_breakdown = json.dumps(findings)
    previous_status = result.status
    # Existing helper commits findings, score and status together with the audit.
    crud.create_review(db, result.id, f"{reviewer.id}:{reviewer.email}"[:100], data.decision, data.reason, previous_status, data.decision,
                       threshold_override=data.override_threshold, override_reason=data.override_reason if data.override_threshold else None,
                       warnings_resolved=data.warnings_resolved)
    db.refresh(result)
    return campaign_detail(result)


@router.post("/reports/{report_id}/resolve")
def resolve_campaign_report(
    report_id: int,
    data: ReportResolve,
    db: Database,
    user: AdminUser,
) -> dict:
    result = crud.resolve_report(db, report_id, data.admin_response, data.status)
    if result is None:
        raise HTTPException(404, "Report not found")
    return {"status": "ok", "report_id": report_id, "report_status": result.status}

