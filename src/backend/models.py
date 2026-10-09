"""
PanataanPH SQLAlchemy ORM Models.

Defines all database tables for the PanataanPH relief campaign
verification platform. Uses SQLAlchemy 2.0 Mapped column style.

Tables:
    - campaigns: Relief campaign submissions
    - documents: Uploaded supporting document metadata
    - extraction_results: AI-extracted fields from documents
    - reviews: Admin review decisions and history
    - reports: User-submitted campaign reports
    - verification_findings: Per-criterion score breakdown
"""

from datetime import date, datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    """Organizer or explicitly provisioned administrator/LGU account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="organizer")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuthSession(Base):
    """Only session token digests are retained in SQLite."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user: Mapped["User"] = relationship("User")


class AccountReview(Base):
    __tablename__ = "account_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================================
# Campaigns
# ============================================================================

class Campaign(Base):
    """A relief drive or fundraiser submitted for verification."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # Organizer information
    organizer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organizer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organizer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Organization information
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Campaign details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    cause: Mapped[str | None] = mapped_column(String(100), nullable=True)  # disaster_relief, medical, education, etc.
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiaries: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Payment information
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification status & scoring
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    verification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User | None"] = relationship("User")
    qr_codes: Mapped[list["DonationQRCode"]] = relationship(
        "DonationQRCode", back_populates="campaign", cascade="all, delete-orphan"
    )
    fund_updates: Mapped[list["FundUpdate"]] = relationship(
        "FundUpdate", back_populates="campaign", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="campaign", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="campaign", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="campaign", cascade="all, delete-orphan"
    )
    findings: Mapped[list["VerificationFinding"]] = relationship(
        "VerificationFinding", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Campaign(id={self.id}, public_id='{self.public_id}', "
            f"title='{self.title[:40]}...', status='{self.status}')>"
        )


# ============================================================================
# Documents
# ============================================================================

class DonationQRCode(Base):
    """Public donation QR image, distinct from confidential evidence."""

    __tablename__ = "donation_qr_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="qr_codes")


class FundUpdate(Base):
    """Organizer reported cash received/spent, published after human review."""

    __tablename__ = "fund_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="fund_updates")


class Document(Base):
    """Metadata for an uploaded supporting document (PDF, image, etc.)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)

    # File metadata (actual file lives on the filesystem, NOT in the DB)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, png, jpg, etc.
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Processing status
    processing_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed

    # Timestamp
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="documents")
    extraction_result: Mapped["ExtractionResult | None"] = relationship(
        "ExtractionResult", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, public_id='{self.public_id}', "
            f"filename='{self.original_filename}', status='{self.processing_status}')>"
        )


# ============================================================================
# Extraction Results
# ============================================================================

class ExtractionResult(Base):
    """
    Structured data extracted from a document via OCR + LLM.

    All extracted fields are nullable because documents may
    legitimately omit them. The LLM must return null for missing
    information rather than inventing values.
    """

    __tablename__ = "extraction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), unique=True, nullable=False
    )

    # Extracted fields (all nullable — documents may not contain every field)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permit_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # YYYY-MM-DD
    expiration_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # YYYY-MM-DD
    beneficiaries: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array string

    # Raw data for admin inspection & debugging
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # Raw JSON from Ollama
    confidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="extraction_result")

    def __repr__(self) -> str:
        return (
            f"<ExtractionResult(id={self.id}, document_id={self.document_id}, "
            f"doc_type='{self.document_type}')>"
        )


# ============================================================================
# Reviews
# ============================================================================

class Review(Base):
    """
    An admin review decision for a campaign.

    Each review records a status transition and the admin's reasoning.
    Multiple reviews may exist per campaign to form a review history.
    """

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)

    admin_username: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # approved, rejected, needs_information, under_review
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status transition tracking
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # Timestamp
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="reviews")

    def __repr__(self) -> str:
        return (
            f"<Review(id={self.id}, campaign_id={self.campaign_id}, "
            f"decision='{self.decision}', by='{self.admin_username}')>"
        )


# ============================================================================
# Reports
# ============================================================================

class Report(Base):
    """
    A user-submitted report/concern about a campaign.

    Reports trigger admin review — they do NOT automatically
    label a campaign as fraudulent.
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)

    reporter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Report status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, dismissed
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="reports")

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, campaign_id={self.campaign_id}, "
            f"status='{self.status}')>"
        )


# ============================================================================
# Verification Findings
# ============================================================================

class VerificationFinding(Base):
    """
    A single criterion in the evidence completeness score breakdown.

    Score criteria (max 100 points total):
        - permits:      30 points — Applicable permits or authorizations
        - identity:     20 points — Organizer identity and registration info
        - consistency:  20 points — Consistency of organizer and payment details
        - completeness: 20 points — Campaign information completeness
        - history:      10 points — Previously reviewed campaign history
    """

    __tablename__ = "verification_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)

    criterion: Mapped[str] = mapped_column(String(100), nullable=False)  # permits, identity, consistency, completeness, history
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    points_possible: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="findings")

    def __repr__(self) -> str:
        return (
            f"<VerificationFinding(id={self.id}, campaign_id={self.campaign_id}, "
            f"criterion='{self.criterion}', score={self.points_awarded}/{self.points_possible})>"
        )
