import json
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import crud, main
from backend.database import Base, get_db
from backend.models import Campaign, Document


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

    def database() -> Iterator[Session]:
        yield db

    main.app.dependency_overrides[get_db] = database
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def campaign_data() -> dict:
    return {
        "organizer_name": "Test Organizer",
        "organizer_email": "private@example.com",
        "organizer_phone": "09170000000",
        "title": "Flood Relief",
        "description": "Food for displaced families",
        "purpose": "Food packs",
        "cause": "disaster_relief",
        "location": "Marikina",
        "target_amount": 5000,
    }


def test_directory_only_returns_verified_and_filters(client: TestClient, db: Session, campaign_data: dict) -> None:
    verified = crud.create_campaign(db, **campaign_data, status="verified", admin_notes="Confidential")
    pending = crud.create_campaign(db, **{**campaign_data, "title": "Pending campaign"})
    for status in ["under_review", "needs_information", "rejected"]:
        crud.create_campaign(db, **campaign_data, status=status)
    result = client.get("/api/campaigns").json()
    assert result["total"] == 1
    assert result["items"][0]["public_id"] == verified.public_id
    assert client.get("/api/campaigns", params={"search": "Flood", "location": "Marik", "cause": "disaster_relief"}).json()["total"] == 1
    assert client.get("/api/campaigns", params={"search": "unknown"}).json()["total"] == 0
    assert client.get("/api/campaigns", params={"location": "Leyte"}).json()["total"] == 0
    assert client.get("/api/campaigns", params={"status": "pending"}).json()["items"][0]["status"] == "verified"
    assert client.get(f"/api/campaigns/{pending.public_id}").status_code == 404
    assert client.get("/api/campaigns/missing").status_code == 404
    assert client.get("/api/campaigns", params={"limit": 101}).status_code == 422
    assert client.get("/api/campaigns", params={"skip": -1}).status_code == 422


def test_public_detail_excludes_private_evidence(client: TestClient, db: Session, campaign_data: dict) -> None:
    campaign = crud.create_campaign(db, **campaign_data, status="verified", admin_notes="Private note", verification_score=30)
    crud.create_document(db, campaign.id, "private/id.pdf", "id.pdf", "pdf", 123)
    crud.create_finding(db, campaign.id, "permits", 30, 30, "Sensitive reviewer detail")
    result = client.get(f"/api/campaigns/{campaign.public_id}")
    assert result.status_code == 200
    public = result.json()
    assert public["verification_score"] == 30
    assert public["findings"] == [{"criterion": "permits", "points_awarded": 30, "points_possible": 30}]
    for name in ["organizer_email", "organizer_phone", "admin_notes", "documents", "score_breakdown", "organization_registration_number"]:
        assert name not in public
    assert "private" not in result.text.lower()
    assert client.get("/storage/id.pdf").status_code == 404


def test_submission_saves_privately_without_approving(client: TestClient, db: Session, campaign_data: dict) -> None:
    response = client.post("/api/submissions", data={"campaign": json.dumps({**campaign_data, "status": "verified", "verification_score": 100})}, files=[
        ("documents", ("../../permit.pdf", b"%PDF-1.7\nTest evidence", "application/pdf")),
        ("documents", ("payment.png", b"\x89PNG\r\n\x1a\nTest evidence", "image/png")),
    ])
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["documents_received"] == 2
    campaign = db.scalars(select(Campaign)).one()
    assert campaign.status == "pending"
    assert campaign.verification_score is None
    documents = db.scalars(select(Document)).all()
    assert len(documents) == 2
    assert documents[0].original_filename == "permit.pdf"
    assert documents[0].processing_status == "pending"
    for document in documents:
        path = Path(document.storage_path)
        assert path.parent == main.STORAGE_ROOT
        assert path.exists()
    assert client.get("/api/campaigns").json()["total"] == 0
    assert client.get(f"/api/campaigns/{campaign.public_id}").status_code == 404


@pytest.mark.parametrize("filename,contents,mime,status", [
    ("unsafe.exe", b"MZ", "application/octet-stream", 415),
    ("fake.pdf", b"not a pdf", "application/pdf", 415),
    ("empty.pdf", b"", "application/pdf", 415),
    ("wrong.png", b"%PDF-1.7", "image/png", 415),
    ("permit.pdf", b"%PDF-" + b"x" * main.MAX_FILE_BYTES, "application/pdf", 413),
], ids=["unsupported-extension", "invalid-pdf", "empty-file", "mismatched-signature", "oversized-file"])
def test_upload_limits_and_types(client: TestClient, db: Session, campaign_data: dict, filename: str, contents: bytes, mime: str, status: int) -> None:
    response = client.post("/api/submissions", data={"campaign": json.dumps(campaign_data)}, files={"documents": (filename, contents, mime)})
    assert response.status_code == status
    assert db.scalars(select(Campaign)).all() == []
    assert not main.STORAGE_ROOT.exists() or list(main.STORAGE_ROOT.iterdir()) == []


def test_later_invalid_file_cleans_previous_files(client: TestClient, db: Session, campaign_data: dict) -> None:
    response = client.post("/api/submissions", data={"campaign": json.dumps(campaign_data)}, files=[
        ("documents", ("good.pdf", b"%PDF-1.7", "application/pdf")),
        ("documents", ("bad.pdf", b"not a pdf", "application/pdf")),
    ])
    assert response.status_code == 415
    assert list(main.STORAGE_ROOT.iterdir()) == []
    assert db.scalars(select(Campaign)).all() == []


def test_database_failure_rolls_back_and_removes_files(client: TestClient, db: Session, campaign_data: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_commit() -> None:
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Database unavailable"):
        client.post("/api/submissions", data={"campaign": json.dumps(campaign_data)}, files={"documents": ("permit.pdf", b"%PDF-1.7", "application/pdf")})
    assert db.scalars(select(Campaign)).all() == []
    assert db.scalars(select(Document)).all() == []
    assert list(main.STORAGE_ROOT.iterdir()) == []


def test_submission_validation(client: TestClient, db: Session, campaign_data: dict) -> None:
    file = ("permit.pdf", b"%PDF-1.7", "application/pdf")
    for payload in ["not-json", json.dumps({**campaign_data, "target_amount": -1}), json.dumps({**campaign_data, "target_amount": float("inf")}), json.dumps({**campaign_data, "title": "   "}), json.dumps({**campaign_data, "urgency": "invalid"}), json.dumps({**campaign_data, "organizer_email": "invalid"})]:
        assert client.post("/api/submissions", data={"campaign": payload}, files={"documents": file}).status_code == 422
    assert client.post("/api/submissions", data={"campaign": json.dumps(campaign_data)}).status_code == 422
    assert client.post("/api/submissions", data={"campaign": json.dumps(campaign_data)}, files=[("documents", file)] * 5).status_code == 422
    assert db.scalars(select(Campaign)).all() == []
