"""
PanataanPH CRUD Operations.

Provides all Create, Read, Update, Delete functions for the database layer.
FastAPI route handlers import these functions and pass in a SQLAlchemy Session.

Usage:
    from backend.crud import create_campaign, get_campaign_by_public_id
    from backend.database import get_db

    @router.post("/campaigns")
    def submit_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
        campaign = create_campaign(db, **data.model_dump())
        return campaign
"""

import uuid
from datetime import datetime

from sqlalchemy import and_, exists, or_, select, func as sql_func
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from backend.services.scoring import MIN_VERIFICATION_SCORE

from backend.models import (
    Campaign,
    Document,
    ExtractionResult,
    Review,
    Report,
    VerificationFinding,
)


# ============================================================================
# Campaign CRUD
# ============================================================================


def public_campaign_filter() -> ColumnElement[bool]:
    """Legacy reviewed demo rows have no owner; new submissions always have one."""
    latest_review = select(sql_func.max(Review.id)).where(Review.campaign_id == Campaign.id).correlate(Campaign).scalar_subquery()
    approved_exception = exists(select(Review.id).where(
        Review.id == latest_review,
        Review.decision == "verified",
        Review.new_status == "verified",
        Review.threshold_override.is_(True),
        Review.warnings_resolved.is_(True),
        sql_func.length(sql_func.trim(Review.override_reason)) > 0,
    ))
    return and_(
        Campaign.status == "verified",
        or_(Campaign.verification_score >= MIN_VERIFICATION_SCORE, approved_exception),
        or_(Campaign.owner_id.is_(None), Campaign.owner.has(verified=True)),
    )

def create_campaign(db: Session, *, commit: bool = True, **kwargs) -> Campaign:
    """
    Create a new campaign with status='pending' and a generated public_id.

    Pass campaign fields as keyword arguments (title, description, purpose, etc.).
    Use commit=False to include the creation in a caller-managed transaction.
    """
    campaign = Campaign(
        public_id=str(uuid.uuid4()),
        **kwargs,
    )
    if "status" not in kwargs:
        campaign.status = "pending"
    db.add(campaign)
    if commit:
        db.commit()
        db.refresh(campaign)
    else:
        db.flush()
    return campaign


def get_campaign_by_id(db: Session, campaign_id: int) -> Campaign | None:
    """Get a campaign by its internal integer ID."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    return db.execute(stmt).scalar_one_or_none()


def get_campaign_by_public_id(db: Session, public_id: str) -> Campaign | None:
    """Get a campaign by its public UUID (used in URLs and APIs)."""
    stmt = select(Campaign).where(Campaign.public_id == public_id)
    return db.execute(stmt).scalar_one_or_none()


def list_campaigns(
    db: Session,
    *,
    status: str | None = None,
    cause: str | None = None,
    location: str | None = None,
    urgency: str | None = None,
    search: str | None = None,
    public_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> list[Campaign]:
    """
    List campaigns with optional filtering, text search, and pagination.

    Args:
        status: Filter by campaign status (e.g., 'verified', 'pending').
        cause: Filter by cause category (e.g., 'disaster_relief').
        location: Filter by location (partial match).
        urgency: Filter by urgency level.
        search: Text search across title, description, organizer_name, organization_name.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
    """
    stmt = select(Campaign)

    if public_only:
        stmt = stmt.where(public_campaign_filter())

    if status is not None:
        stmt = stmt.where(Campaign.status == status)
    if cause is not None:
        stmt = stmt.where(Campaign.cause == cause)
    if location is not None:
        stmt = stmt.where(Campaign.location.ilike(f"%{location}%"))
    if urgency is not None:
        stmt = stmt.where(Campaign.urgency == urgency)
    if search is not None:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            Campaign.title.ilike(search_pattern)
            | Campaign.description.ilike(search_pattern)
            | Campaign.organizer_name.ilike(search_pattern)
            | Campaign.organization_name.ilike(search_pattern)
        )

    stmt = stmt.order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def count_campaigns(
    db: Session,
    *,
    status: str | None = None,
    cause: str | None = None,
    location: str | None = None,
    urgency: str | None = None,
    search: str | None = None,
    public_only: bool = False,
) -> int:
    """Count campaigns with the same filters as list_campaigns (without pagination)."""
    stmt = select(sql_func.count(Campaign.id))

    if public_only:
        stmt = stmt.where(public_campaign_filter())

    if status is not None:
        stmt = stmt.where(Campaign.status == status)
    if cause is not None:
        stmt = stmt.where(Campaign.cause == cause)
    if location is not None:
        stmt = stmt.where(Campaign.location.ilike(f"%{location}%"))
    if urgency is not None:
        stmt = stmt.where(Campaign.urgency == urgency)
    if search is not None:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            Campaign.title.ilike(search_pattern)
            | Campaign.description.ilike(search_pattern)
            | Campaign.organizer_name.ilike(search_pattern)
            | Campaign.organization_name.ilike(search_pattern)
        )

    result = db.execute(stmt).scalar()
    return result or 0


def update_campaign_status(
    db: Session,
    campaign_id: int,
    new_status: str,
    admin_notes: str | None = None,
) -> Campaign | None:
    """Update a campaign's status. Optionally update admin_notes."""
    campaign = get_campaign_by_id(db, campaign_id)
    if campaign is None:
        return None
    campaign.status = new_status
    if admin_notes is not None:
        campaign.admin_notes = admin_notes
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return campaign


def update_campaign_score(
    db: Session,
    campaign_id: int,
    score: int,
    score_breakdown_json: str,
) -> Campaign | None:
    """Update a campaign's verification score and breakdown."""
    campaign = get_campaign_by_id(db, campaign_id)
    if campaign is None:
        return None
    campaign.verification_score = score
    campaign.score_breakdown = score_breakdown_json
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return campaign


# ============================================================================
# Document CRUD
# ============================================================================

def create_document(
    db: Session,
    campaign_id: int,
    storage_path: str,
    original_filename: str,
    file_type: str,
    file_size_bytes: int,
    *,
    commit: bool = True,
) -> Document:
    """Create document metadata; commit=False leaves the transaction to the caller."""
    document = Document(
        public_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        storage_path=storage_path,
        original_filename=original_filename,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        processing_status="pending",
    )
    db.add(document)
    if commit:
        db.commit()
        db.refresh(document)
    else:
        db.flush()
    return document


def get_document_by_id(db: Session, document_id: int) -> Document | None:
    """Get a document by its internal integer ID."""
    stmt = select(Document).where(Document.id == document_id)
    return db.execute(stmt).scalar_one_or_none()


def get_document_by_public_id(db: Session, public_id: str) -> Document | None:
    """Get a document by its public UUID."""
    stmt = select(Document).where(Document.public_id == public_id)
    return db.execute(stmt).scalar_one_or_none()


def get_documents_by_campaign(db: Session, campaign_id: int) -> list[Document]:
    """Get all documents belonging to a campaign."""
    stmt = (
        select(Document)
        .where(Document.campaign_id == campaign_id)
        .order_by(Document.uploaded_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update_document_status(
    db: Session,
    document_id: int,
    processing_status: str,
) -> Document | None:
    """Update a document's processing status (pending, processing, completed, failed)."""
    document = get_document_by_id(db, document_id)
    if document is None:
        return None
    document.processing_status = processing_status
    db.commit()
    db.refresh(document)
    return document


# ============================================================================
# Extraction Result CRUD
# ============================================================================

def create_extraction_result(db: Session, document_id: int, **kwargs) -> ExtractionResult:
    """
    Create an extraction result for a processed document.

    Pass extracted fields as keyword arguments (document_type, issuing_authority, etc.).
    """
    result = ExtractionResult(document_id=document_id, **kwargs)
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_extraction_by_document(db: Session, document_id: int) -> ExtractionResult | None:
    """Get the extraction result for a specific document."""
    stmt = select(ExtractionResult).where(ExtractionResult.document_id == document_id)
    return db.execute(stmt).scalar_one_or_none()


def update_extraction_result(db: Session, extraction_id: int, **fields) -> ExtractionResult | None:
    """Update specific fields on an extraction result."""
    stmt = select(ExtractionResult).where(ExtractionResult.id == extraction_id)
    result = db.execute(stmt).scalar_one_or_none()
    if result is None:
        return None
    for key, value in fields.items():
        if hasattr(result, key):
            setattr(result, key, value)
    db.commit()
    db.refresh(result)
    return result


# ============================================================================
# Review CRUD
# ============================================================================

def create_review(
    db: Session,
    campaign_id: int,
    admin_username: str,
    decision: str,
    reason: str | None,
    previous_status: str | None,
    new_status: str,
    *,
    threshold_override: bool = False,
    override_reason: str | None = None,
    warnings_resolved: bool = False,
) -> Review:
    """
    Record an admin review decision for a campaign.

    This also updates the campaign's status to new_status.
    """
    review = Review(
        campaign_id=campaign_id,
        admin_username=admin_username,
        decision=decision,
        reason=reason,
        previous_status=previous_status,
        new_status=new_status,
        threshold_override=threshold_override,
        override_reason=override_reason,
        warnings_resolved=warnings_resolved,
    )
    db.add(review)

    # Also update the campaign status
    campaign = get_campaign_by_id(db, campaign_id)
    if campaign is not None:
        campaign.status = new_status
        campaign.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(review)
    return review


def get_reviews_by_campaign(db: Session, campaign_id: int) -> list[Review]:
    """Get all reviews for a campaign, ordered newest first."""
    stmt = (
        select(Review)
        .where(Review.campaign_id == campaign_id)
        .order_by(Review.reviewed_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


# ============================================================================
# Report CRUD
# ============================================================================

def create_report(
    db: Session,
    campaign_id: int,
    reason: str,
    reporter_name: str | None = None,
    reporter_email: str | None = None,
) -> Report:
    """Create a user-submitted report about a campaign."""
    report = Report(
        campaign_id=campaign_id,
        reason=reason,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_reports_by_campaign(db: Session, campaign_id: int) -> list[Report]:
    """Get all reports for a specific campaign."""
    stmt = (
        select(Report)
        .where(Report.campaign_id == campaign_id)
        .order_by(Report.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_pending_reports(db: Session) -> list[Report]:
    """Get all unresolved reports for the admin dashboard."""
    stmt = (
        select(Report)
        .where(Report.status == "pending")
        .order_by(Report.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def resolve_report(
    db: Session,
    report_id: int,
    admin_response: str,
    status: str = "reviewed",
) -> Report | None:
    """Resolve a report with an admin response."""
    stmt = select(Report).where(Report.id == report_id)
    report = db.execute(stmt).scalar_one_or_none()
    if report is None:
        return None
    report.admin_response = admin_response
    report.status = status
    report.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report


# ============================================================================
# Verification Findings CRUD
# ============================================================================

def create_finding(
    db: Session,
    campaign_id: int,
    criterion: str,
    points_awarded: int,
    points_possible: int,
    details: str | None = None,
) -> VerificationFinding:
    """Create a single verification finding (one score criterion)."""
    finding = VerificationFinding(
        campaign_id=campaign_id,
        criterion=criterion,
        points_awarded=points_awarded,
        points_possible=points_possible,
        details=details,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def get_findings_by_campaign(db: Session, campaign_id: int) -> list[VerificationFinding]:
    """Get all verification findings for a campaign."""
    stmt = (
        select(VerificationFinding)
        .where(VerificationFinding.campaign_id == campaign_id)
        .order_by(VerificationFinding.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_findings_by_campaign(db: Session, campaign_id: int) -> None:
    """Delete all findings for a campaign (used before score recalculation)."""
    stmt = select(VerificationFinding).where(VerificationFinding.campaign_id == campaign_id)
    findings = db.execute(stmt).scalars().all()
    for finding in findings:
        db.delete(finding)
    db.commit()
