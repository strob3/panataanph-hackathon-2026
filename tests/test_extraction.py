"""Tests for local AI document extraction pipeline."""

import json
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from fastapi.testclient import TestClient
from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import crud, main
from backend.auth import hash_password
from backend.database import Base, get_db
from backend.models import Campaign, Document, User
from backend.services import llm, ocr
from backend.services.pipeline import run_document_extraction


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(main, "STORAGE_ROOT", tmp_path / "private")
    monkeypatch.setattr("backend.database.init_db", lambda: None)

    def database() -> Iterator[Session]:
        yield db

    main.app.dependency_overrides[get_db] = database
    reviewer = User(name="Reviewer", email="reviewer@example.com", password_hash=hash_password("review-password"), role="admin", verified=True)
    db.add(reviewer)
    db.commit()
    browser = TestClient(main.app)
    assert browser.post("/api/auth/login", json={"email": reviewer.email, "password": "review-password"}).status_code == 200
    yield browser
    main.app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a valid PDF with selectable text without an extra dependency."""
    pdf_path = tmp_path / "test_permit.pdf"
    writer = PdfWriter()
    page = PageObject.create_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 16 Tf 72 700 Td (DSWD permit SP-999 for relief operations) Tj ET")
    page[NameObject("/Contents")] = stream
    writer.add_page(page)
    with pdf_path.open("wb") as f:
        writer.write(f)
    return pdf_path


def test_submission_automatically_extracts_selectable_pdf(client: TestClient, db: Session, sample_pdf: Path) -> None:
    client.post("/api/auth/register", json={"name": "Organizer", "email": "organizer@example.com", "password": "organizer-password"})
    client.post("/api/auth/login", json={"email": "organizer@example.com", "password": "organizer-password"})
    payload = {"organizer_name": "Organizer", "title": "Relief", "description": "Food packs", "purpose": "Food", "location": "Manila", "target_amount": 1000}
    with patch("backend.services.llm.call_ollama_extraction", side_effect=llm.OllamaUnavailableError("offline")):
        response = client.post("/api/submissions", data={"campaign": json.dumps(payload)}, files={"documents": ("permit.pdf", sample_pdf.read_bytes(), "application/pdf")})
    assert response.status_code == 201
    db.expire_all()
    document = db.query(Document).one()
    assert document.processing_status == "completed"
    assert "DSWD permit SP-999" in document.extraction_result.raw_ocr_text
    assert document.campaign.status == "pending"
    assert document.campaign.verification_score is None


def test_extraction_endpoints_require_reviewer(client: TestClient) -> None:
    client.post("/api/auth/logout")
    paths = [("get", "/api/documents/1"), ("get", "/api/documents/1/extraction"), ("post", "/api/documents/1/extract")]
    for method, path in paths:
        assert getattr(client, method)(path).status_code == 401
    client.post("/api/auth/register", json={"name": "Organizer", "email": "organizer@example.com", "password": "organizer-password"})
    client.post("/api/auth/login", json={"email": "organizer@example.com", "password": "organizer-password"})
    for method, path in paths:
        assert getattr(client, method)(path).status_code == 403


def test_sanitize_extracted_data() -> None:
    raw = {
        "document_type": "Solicitation Permit",
        "issuing_authority": "DSWD",
        "permit_number": "DSWD-SB-SP-00123-2026",
        "organization_name": "Tulong Kabataan Foundation",
        "purpose": "Relief Operations",
        "issue_date": "null",
        "expiration_date": "",
        "beneficiaries": None,
    }
    sanitized = llm.sanitize_extracted_data(raw)
    assert sanitized.document_type == "Solicitation Permit"
    assert sanitized.issuing_authority == "DSWD"
    assert sanitized.permit_number == "DSWD-SB-SP-00123-2026"
    assert sanitized.issue_date is None
    assert sanitized.expiration_date is None
    assert sanitized.beneficiaries is None
    assert "issue_date" in sanitized.missing_fields
    assert "expiration_date" in sanitized.missing_fields
    assert "beneficiaries" in sanitized.missing_fields


@pytest.mark.anyio
async def test_ollama_extraction_disables_thinking() -> None:
    with patch("backend.services.llm.httpx.AsyncClient") as client_class:
        client = client_class.return_value.__aenter__.return_value
        client.post.return_value = httpx.Response(200, json={"message": {"content": '{"permit_number": "SP-999"}'}})
        fields, _ = await llm.call_ollama_extraction("Permit SP-999")
    assert client.post.call_args.kwargs["json"]["think"] is False
    assert fields.permit_number == "SP-999"
    assert fields.issue_date is None


def test_extracted_fields_must_appear_in_source_text() -> None:
    source = "Organization: Bayanihan\n Relief Group\nPermit: SP-9999\nIssued: September 15, 2026"
    fields = llm.sanitize_extracted_data({
        "organization_name": "Bayanihan Relief Group",
        "permit_number": "SP-999",
        "issuing_authority": "DSWD",
        "issue_date": "2026-09-15",
        "purpose": "Disaster relief operations",
        "confidence_notes": "This appears to be an official permit.",
    }, raw_text=source)
    assert fields.organization_name == "Bayanihan Relief Group"
    assert fields.permit_number is None
    assert fields.issuing_authority is None
    assert fields.issue_date is None
    assert fields.purpose is None
    assert fields.confidence_notes is None
    assert "permit_number" in fields.missing_fields
    literal = llm.sanitize_extracted_data({"permit_number": "SP-9999", "issue_date": "September 15, 2026"}, raw_text=source)
    assert literal.permit_number == "SP-9999"
    assert literal.issue_date == "September 15, 2026"


@pytest.mark.anyio
async def test_model_fabrications_are_removed_before_returning() -> None:
    source = "GCash\nRecipient: Juan dela Cruz\nFood packs for flood victims"
    with patch("backend.services.llm.httpx.AsyncClient") as client_class:
        client = client_class.return_value.__aenter__.return_value
        client.post.return_value = httpx.Response(200, json={"message": {"content": json.dumps({
            "document_type": "Solicitation Permit", "issuing_authority": "DSWD",
            "organization_name": "Tulong Kabataan Foundation", "permit_number": "DSWD-SB-SP-00123-2026",
            "purpose": "Food packs for flood victims",
        })}})
        fields, _ = await llm.call_ollama_extraction(source)
    assert fields.purpose == "Food packs for flood victims"
    assert fields.document_type is None
    assert fields.issuing_authority is None
    assert fields.organization_name is None
    assert fields.permit_number is None


def test_admin_filters_unsupported_values_from_saved_extractions(client: TestClient, db: Session, tmp_path: Path) -> None:
    campaign = crud.create_campaign(db, organizer_name="Organizer", title="Relief", description="Food packs", purpose="Food", location="Manila", target_amount=1000)
    document = crud.create_document(db, campaign.id, str(tmp_path / "payment.png"), "payment.png", "png", 1)
    original = crud.create_extraction_result(db, document.id,
        raw_ocr_text="GCash\nFood packs for flood victims", purpose="Food packs for flood victims",
        document_type="Solicitation Permit", permit_number="DSWD-SB-SP-00123-2026", issuing_authority="DSWD")
    response = client.get(f"/api/admin/campaigns/{campaign.public_id}")
    assert response.status_code == 200
    extraction = response.json()["documents"][0]["extraction"]
    assert extraction["purpose"] == "Food packs for flood victims"
    assert extraction["document_type"] is None
    assert extraction["permit_number"] is None
    assert extraction["issuing_authority"] is None
    assert extraction["raw_ocr_text"] == "GCash\nFood packs for flood victims"
    assert "permit_number" in json.loads(extraction["missing_fields"])
    assert original.permit_number == "DSWD-SB-SP-00123-2026"


def test_clean_extracted_text() -> None:
    dirty = "Line 1 \r\n\r\n\r\n\r\n Line 2   with   spaces\x00"
    cleaned = ocr.clean_extracted_text(dirty)
    assert "\x00" not in cleaned
    assert "Line 1\n\nLine 2 with spaces" == cleaned


def test_extract_text_from_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ocr.extract_text_from_file(tmp_path / "missing.pdf", "pdf")


def test_extract_text_from_file_unsupported(tmp_path: Path) -> None:
    dummy = tmp_path / "dummy.docx"
    dummy.write_text("dummy")
    text, method = ocr.extract_text_from_file(dummy, "docx")
    assert text == ""
    assert method == "unsupported_type"


def test_paddleocr_reads_all_pages(tmp_path: Path) -> None:
    with patch("backend.services.ocr.get_ocr") as engine:
        engine.return_value.predict.return_value = iter([
            {"rec_texts": ["Permit SP-123", ""]},
            {"rec_texts": ["Beneficiaries: displaced families"]},
        ])
        assert ocr.extract_image_ocr(tmp_path / "scanned.pdf") == "Permit SP-123\nBeneficiaries: displaced families"
        engine.return_value.predict.assert_called_once_with(str(tmp_path / "scanned.pdf"))


def test_ocr_failure_is_not_silently_empty(tmp_path: Path) -> None:
    with patch("backend.services.ocr.get_ocr", side_effect=RuntimeError("model unavailable")):
        with pytest.raises(ocr.TextExtractionError, match="model unavailable"):
            ocr.extract_image_ocr(tmp_path / "image.png")


def test_short_selectable_pdf_needs_no_ocr(tmp_path: Path) -> None:
    path = tmp_path / "short.pdf"
    path.touch()
    with patch("backend.services.ocr.extract_pdf_selectable_text", return_value="Permit SP-1"):
        with patch("backend.services.ocr.extract_image_ocr") as image_ocr:
            assert ocr.extract_text_from_file(path, "pdf") == ("Permit SP-1", "pdf_text")
            image_ocr.assert_not_called()


@pytest.mark.anyio
async def test_failed_text_extraction_skips_llm_and_can_retry(db: Session, tmp_path: Path) -> None:
    campaign = crud.create_campaign(db, organizer_name="Organizer", title="Relief", description="Food packs", purpose="Food", location="Manila", target_amount=1000)
    path = tmp_path / "image.png"
    path.touch()
    document = crud.create_document(db, campaign.id, str(path), "image.png", "png", 1)
    with patch("backend.services.ocr.extract_text_from_file", side_effect=ocr.TextExtractionError("OCR dependencies missing")):
        with patch("backend.services.llm.call_ollama_extraction", new_callable=AsyncMock) as model:
            result = await run_document_extraction(db, document.id)
            model.assert_not_called()
    assert document.processing_status == "failed"
    assert result.raw_ocr_text is None
    assert result.permit_number is None
    assert "OCR dependencies missing" in result.confidence_notes
    with patch("backend.services.ocr.extract_text_from_file", return_value=("Permit SP-1", "paddleocr")):
        with patch("backend.services.llm.call_ollama_extraction", side_effect=llm.OllamaUnavailableError("offline")):
            retried = await run_document_extraction(db, document.id)
    assert retried.id == result.id
    assert retried.raw_ocr_text == "Permit SP-1"
    assert document.processing_status == "completed"


@pytest.mark.anyio
async def test_run_document_extraction_with_mock_llm(db: Session, tmp_path: Path) -> None:
    # Create test campaign and document
    campaign = crud.create_campaign(
        db,
        organizer_name="Juan dela Cruz",
        title="Flood Aid",
        description="Help Marikina",
        purpose="Food distribution",
        location="Marikina",
        target_amount=10000.0,
    )

    doc_file = tmp_path / "permit.pdf"
    doc_file.write_bytes(b"%PDF-1.4 sample content with dummy permit bytes")

    doc = crud.create_document(
        db,
        campaign_id=campaign.id,
        storage_path=str(doc_file),
        original_filename="permit.pdf",
        file_type="pdf",
        file_size_bytes=len(doc_file.read_bytes()),
    )

    mock_fields = llm.ExtractedDocumentFields(
        document_type="Solicitation Permit",
        issuing_authority="DSWD Central Office",
        permit_number="DSWD-SB-SP-00123-2026",
        organization_name="Tulong Kabataan",
        purpose="Disaster Relief",
        issue_date="2026-09-15",
        expiration_date="2026-12-15",
        beneficiaries="Typhoon victims",
        missing_fields=[],
    )

    with patch("backend.services.ocr.extract_text_from_file", return_value=("Sample text from permit", "pdf_text")):
        with patch("backend.services.llm.call_ollama_extraction", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (mock_fields, json.dumps(mock_fields.model_dump()))
            result = await run_document_extraction(db, doc.id)

    assert result.document_id == doc.id
    assert result.permit_number == "DSWD-SB-SP-00123-2026"
    assert result.issuing_authority == "DSWD Central Office"
    assert result.organization_name == "Tulong Kabataan"

    # Verify document processing_status updated
    updated_doc = crud.get_document_by_id(db, doc.id)
    assert updated_doc is not None
    assert updated_doc.processing_status == "completed"


@pytest.mark.anyio
async def test_run_document_extraction_offline_fallback(db: Session, tmp_path: Path) -> None:
    campaign = crud.create_campaign(
        db,
        organizer_name="Maria Santos",
        title="Bayanihan Drive",
        description="Medical mission",
        purpose="Medicine supply",
        location="Cebu",
        target_amount=20000.0,
    )

    doc_file = tmp_path / "cert.pdf"
    doc_file.write_bytes(b"%PDF-1.4 dummy pdf bytes")

    doc = crud.create_document(
        db,
        campaign_id=campaign.id,
        storage_path=str(doc_file),
        original_filename="cert.pdf",
        file_type="pdf",
        file_size_bytes=len(doc_file.read_bytes()),
    )

    with patch("backend.services.ocr.extract_text_from_file", return_value=("Certificate of Registration text", "pdf_text")):
        with patch(
            "backend.services.llm.call_ollama_extraction",
            side_effect=llm.OllamaUnavailableError("Ollama not running"),
        ):
            result = await run_document_extraction(db, doc.id, allow_offline_fallback=True)

    assert result.document_id == doc.id
    assert result.raw_ocr_text == "Certificate of Registration text"
    assert "LLM offline" in (result.confidence_notes or "")

    updated_doc = crud.get_document_by_id(db, doc.id)
    assert updated_doc is not None
    assert updated_doc.processing_status == "completed"


def test_api_extraction_endpoints(client: TestClient, db: Session, tmp_path: Path) -> None:
    campaign = crud.create_campaign(
        db,
        organizer_name="Test Org",
        title="Relief Drive",
        description="Help now",
        purpose="Food",
        location="Manila",
        target_amount=5000.0,
    )

    doc_file = tmp_path / "test_doc.pdf"
    doc_file.write_bytes(b"%PDF-1.4 dummy bytes")

    doc = crud.create_document(
        db,
        campaign_id=campaign.id,
        storage_path=str(doc_file),
        original_filename="test_doc.pdf",
        file_type="pdf",
        file_size_bytes=len(doc_file.read_bytes()),
    )

    # Document details before extraction
    get_res = client.get(f"/api/documents/{doc.id}")
    assert get_res.status_code == 200
    assert get_res.json()["processing_status"] == "pending"
    assert get_res.json()["extraction_result"] is None

    # Extraction before run should 404
    no_ext = client.get(f"/api/documents/{doc.id}/extraction")
    assert no_ext.status_code == 404

    # Run extraction via API (mocking Ollama call)
    mock_fields = llm.ExtractedDocumentFields(
        document_type="Solicitation Permit",
        issuing_authority="DSWD",
        permit_number="SP-999",
        missing_fields=[],
    )

    with patch("backend.services.ocr.extract_text_from_file", return_value=("DSWD permit SP-999", "pdf_text")):
        with patch("backend.services.llm.call_ollama_extraction", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (mock_fields, '{"permit_number": "SP-999"}')
            extract_res = client.post(f"/api/documents/{doc.id}/extract")

    assert extract_res.status_code == 200
    data = extract_res.json()
    assert data["permit_number"] == "SP-999"
    assert data["issuing_authority"] == "DSWD"

    # Get extraction full
    ext_res = client.get(f"/api/documents/{doc.id}/extraction")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()
    assert ext_data["permit_number"] == "SP-999"
    assert ext_data["raw_ocr_text"] == "DSWD permit SP-999"

    # Nonexistent document
    assert client.post("/api/documents/9999/extract").status_code == 404
    assert client.get("/api/documents/9999/extraction").status_code == 404
