"""
PanataanPH Pydantic Schemas.

Request/response validation models for the FastAPI backend.
Uses Pydantic v2 with model_config = ConfigDict(from_attributes=True)
for seamless conversion from SQLAlchemy ORM objects.

Usage in a route:
    @router.post("/campaigns", response_model=CampaignResponse)
    def submit(data: CampaignCreate, db: Session = Depends(get_db)):
        campaign = create_campaign(db, **data.model_dump())
        return campaign  # Pydantic auto-converts the ORM object
"""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr


# ============================================================================
# Enums
# ============================================================================

class CampaignStatus(str, Enum):
    """Valid campaign statuses."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    NEEDS_INFORMATION = "needs_information"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UrgencyLevel(str, Enum):
    """Campaign urgency levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Campaign Schemas
# ============================================================================

class CampaignCreate(BaseModel):
    """Schema for creating a new campaign (organizer submission)."""

    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    # Organizer info
    organizer_name: str = Field(..., min_length=1, max_length=255)
    organizer_email: str | None = Field(default=None, max_length=255)
    organizer_phone: str | None = Field(default=None, max_length=50)

    # Organization info
    organization_name: str | None = Field(default=None, max_length=255)
    organization_registration_number: str | None = Field(default=None, max_length=100)

    # Campaign details
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1, max_length=255)
    cause: str | None = Field(default=None, max_length=100)
    location: str = Field(..., min_length=1, max_length=255)
    beneficiaries: str | None = None
    target_amount: float = Field(..., gt=0, description="Target fundraising amount in PHP")

    # Payment info
    payment_method: str | None = Field(default=None, max_length=100)
    payment_details: str | None = None

    # Urgency
    urgency: str = Field(default="normal")

    @field_validator("organizer_email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Basic email format check if provided."""
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        valid = {"low", "normal", "high", "critical"}
        if v not in valid:
            raise ValueError(f"Urgency must be one of: {', '.join(valid)}")
        return v


class CampaignUpdate(BaseModel):
    """Schema for partial campaign updates. All fields optional."""

    organizer_name: str | None = Field(default=None, max_length=255)
    organizer_email: str | None = Field(default=None, max_length=255)
    organizer_phone: str | None = Field(default=None, max_length=50)
    organization_name: str | None = Field(default=None, max_length=255)
    organization_registration_number: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    purpose: str | None = Field(default=None, max_length=255)
    cause: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    beneficiaries: str | None = None
    target_amount: float | None = Field(default=None, gt=0)
    payment_method: str | None = Field(default=None, max_length=100)
    payment_details: str | None = None
    urgency: str | None = None


class CampaignResponse(BaseModel):
    """Full campaign data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    organizer_name: str
    organizer_email: str | None
    organizer_phone: str | None
    organization_name: str | None
    organization_registration_number: str | None
    title: str
    description: str
    purpose: str
    cause: str | None
    location: str
    beneficiaries: str | None
    target_amount: float
    payment_method: str | None
    payment_details: str | None
    status: str
    urgency: str
    verification_score: int | None
    score_breakdown: str | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    """Lightweight campaign data for list/directory views."""

    model_config = ConfigDict(from_attributes=True)

    public_id: str
    title: str
    organizer_name: str
    organization_name: str | None
    purpose: str
    cause: str | None
    location: str
    status: str
    urgency: str
    verification_score: int | None
    created_at: datetime


class CampaignListPaginated(BaseModel):
    """Paginated campaign list response."""

    items: list[CampaignListResponse]
    total: int
    skip: int
    limit: int


class PublicFinding(BaseModel):
    """Public score values, excluding private reviewer notes."""

    model_config = ConfigDict(from_attributes=True)
    criterion: str
    points_awarded: int
    points_possible: int


class PublicQRCode(BaseModel):
    public_id: str
    label: str
    image_url: str


class PublicFundEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: str
    kind: Literal["received", "spent"]
    amount_centavos: int
    description: str
    occurred_on: date
    status: Literal["approved"]


class FundsTransparency(BaseModel):
    received_centavos: int = 0
    spent_centavos: int = 0
    balance_centavos: int = 0
    entries: list[PublicFundEntry] = Field(default_factory=list)


class PublicCampaign(CampaignListResponse):
    """Allowlisted public metadata; never documents, contacts, or admin notes."""

    description: str
    beneficiaries: str | None
    target_amount: float
    payment_method: str | None
    payment_details: str | None
    updated_at: datetime
    findings: list[PublicFinding]
    minimum_score: int = 80
    threshold_overridden: bool = False
    qr_codes: list[PublicQRCode] = Field(default_factory=list)
    transparency: FundsTransparency = Field(default_factory=FundsTransparency)


class SubmissionResponse(BaseModel):
    public_id: str
    status: Literal["pending"] = "pending"
    documents_received: int


# ============================================================================
# Document Schemas
# ============================================================================

class DocumentResponse(BaseModel):
    """Document metadata for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    campaign_id: int
    original_filename: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    uploaded_at: datetime


class DocumentWithExtraction(BaseModel):
    """Document with its extraction result (if available)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    campaign_id: int
    original_filename: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    uploaded_at: datetime
    extraction_result: "ExtractionResultResponse | None" = None


# ============================================================================
# Extraction Result Schemas
# ============================================================================

class ExtractionResultResponse(BaseModel):
    """
    Extracted document fields for API responses.

    Excludes raw_ocr_text and raw_llm_response by default
    since they can be very large. Use ExtractionResultFull
    for the admin detail view.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    document_type: str | None
    issuing_authority: str | None
    permit_number: str | None
    organization_name: str | None
    purpose: str | None
    issue_date: str | None
    expiration_date: str | None
    beneficiaries: str | None
    missing_fields: str | None
    confidence_notes: str | None
    processed_at: datetime


class ExtractionResultFull(ExtractionResultResponse):
    """Full extraction result including raw OCR text and LLM response (admin view)."""

    raw_ocr_text: str | None
    raw_llm_response: str | None


# ============================================================================
# Review Schemas
# ============================================================================

class ReviewCreate(BaseModel):
    """Schema for submitting an admin review decision."""

    admin_username: str = Field(..., min_length=1, max_length=100)
    decision: Literal["approved", "rejected", "needs_information", "under_review"]
    reason: str | None = None


class ReviewResponse(BaseModel):
    """Full review data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    admin_username: str
    decision: str
    reason: str | None
    previous_status: str | None
    new_status: str
    reviewed_at: datetime


# ============================================================================
# Report Schemas
# ============================================================================

class ReportCreate(BaseModel):
    """Schema for submitting a campaign report/concern."""

    reason: str = Field(..., min_length=1)
    reporter_name: str | None = Field(default=None, max_length=255)
    reporter_email: str | None = Field(default=None, max_length=255)

    @field_validator("reporter_email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class ReportResolve(BaseModel):
    """Schema for resolving a report."""

    admin_response: str = Field(..., min_length=1)
    status: Literal["reviewed", "dismissed"] = "reviewed"


class ReportResponse(BaseModel):
    """Full report data for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    reporter_name: str | None
    reporter_email: str | None
    reason: str
    status: str
    admin_response: str | None
    created_at: datetime
    resolved_at: datetime | None


# ============================================================================
# Verification Score Schemas
# ============================================================================

class FindingResponse(BaseModel):
    """A single criterion in the score breakdown."""

    model_config = ConfigDict(from_attributes=True)

    criterion: str
    points_awarded: int
    points_possible: int
    details: str | None


class ScoreResponse(BaseModel):
    """Complete verification score with per-criterion breakdown."""

    campaign_id: int
    total_score: int
    findings: list[FindingResponse]


# Resolve forward references
DocumentWithExtraction.model_rebuild()
