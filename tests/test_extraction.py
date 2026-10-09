"""Tests for local AI document extraction pipeline."""

import json
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pypdf import PageObject, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import crud, main
from backend.database import Base, get_db
from backend.models import Campaign, Document
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
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a valid PDF file with selectable text for testing."""
    pdf_path = tmp_path / "test_permit.pdf"
    writer = PdfWriter()
    # Add a blank page with some text annot
    page = PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page)
    with pdf_path.open("wb") as f:
        writer.write(f)
    return pdf_path


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
