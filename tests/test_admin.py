"""Trust-boundary and human publication checks against isolated SQLite only."""

from pathlib import Path
from datetime import date, timedelta
from typing import Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import admin, auth, crud, database
from backend.database import Base, get_db
from backend.models import AccountReview, AuthSession, Document, DonationQRCode, User


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(admin.router)

    def get_test_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)


@pytest.fixture
def integrated_client(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    from backend import main

    monkeypatch.setattr(main, "STORAGE_ROOT", tmp_path / "private")

    def get_test_db() -> Iterator[Session]:
        yield db

    main.app.dependency_overrides[get_db] = get_test_db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


@pytest.fixture
def organizer(db: Session) -> User:
    user = User(name="Organizer", email="organizer@example.com", password_hash=auth.hash_password("example-password"), role="organizer", verified=False)
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def reviewer(db: Session) -> User:
    user = User(name="LGU Reviewer", email="lgu@example.com", password_hash=auth.hash_password("review-password"), role="lgu", verified=True)
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def campaign(db: Session, organizer: User):
    result = crud.create_campaign(db, owner_id=organizer.id, organizer_name=organizer.name, title="Flood Relief", description="Food packs for affected residents", purpose="Food packs", location="Marikina", beneficiaries="Displaced households", target_amount=5000, payment_method="GCash", payment_details="Verified destination")
    crud.create_document(db, result.id, "private/permit.pdf", "permit.pdf", "pdf", 20)
    return result


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_registration_cannot_grant_privileges_or_approve_account(client: TestClient, db: Session) -> None:
    data = {"name": "New Organizer", "email": "NEW@example.com", "password": "example-password"}
    assert client.post("/api/auth/register", json={**data, "role": "admin"}).status_code == 422
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert response.json()["role"] == "organizer"
    assert response.json()["verified"] is False
    assert "password" not in response.text
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/register", json=data).status_code == 409
    assert db.scalar(select(User)).password_hash.startswith("scrypt$")


def test_login_cookie_session_logout_and_csrf(client: TestClient, db: Session, organizer: User) -> None:
    data = {"email": organizer.email, "password": "example-password"}
    assert client.post("/api/auth/login", json={**data, "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/login", json=data, headers={"Origin": "https://attacker.example"}).status_code == 403
    response = client.post("/api/auth/login", json=data, headers={"Origin": "http://testserver"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    token = client.cookies.get(auth.SESSION_COOKIE)
    assert db.scalar(select(AuthSession)).token_hash != token
    assert client.get("/api/auth/me").json()["id"] == organizer.id
    assert client.post("/api/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert db.scalar(select(AuthSession)) is None


def test_admin_boundaries_and_account_audit(client: TestClient, db: Session, organizer: User, reviewer: User) -> None:
    assert client.get("/api/admin/accounts").status_code == 401
    login(client, organizer.email, "example-password")
    assert client.get("/api/admin/accounts").status_code == 403
    login(client, reviewer.email, "review-password")
    assert client.patch(f"/api/admin/accounts/{organizer.id}", json={"verified": True, "reason": "Identity evidence inspected"}).status_code == 200
    audit = db.scalar(select(AccountReview))
    assert organizer.verified and audit.reviewer_id == reviewer.id and audit.reason == "Identity evidence inspected"
    assert client.patch(f"/api/admin/accounts/{reviewer.id}", json={"verified": False, "reason": "Attempt privileged modification"}).status_code == 403


def test_approval_requires_human_review_score_and_verified_owner(client: TestClient, db: Session, campaign, reviewer: User) -> None:
    login(client, reviewer.email, "review-password")
    url = f"/api/admin/campaigns/{campaign.public_id}/review"
    approve = {"decision": "verified", "reason": "Evidence reviewed", "permits": True, "identity": True, "consistency": True, "warnings_resolved": True}
    assert client.post(url, json=approve).status_code == 409
    assert client.post(url, json={"decision": "under_review", "reason": "Begin evidence review"}).status_code == 200
    assert client.post(url, json=approve).status_code == 422
    assert campaign.status == "under_review" and len(campaign.reviews) == 1
    campaign.owner.verified = True
    db.commit()
    low_score = client.post(url, json={"decision": "verified", "reason": "Incomplete evidence", "warnings_resolved": True})
    assert low_score.status_code == 422 and "80" in low_score.json()["detail"]
    assert campaign.status == "under_review" and len(campaign.reviews) == 1
    # The numeric threshold cannot replace resolving donation discrepancies.
    assert client.post(url, json={**approve, "consistency": False, "history": True}).status_code == 422
    assert client.post(url, json={**approve, "warnings_resolved": False}).status_code == 422
    assert client.post(url, json={**approve, "override_threshold": True, "override_reason": "Unnecessary exception"}).status_code == 422
    result = client.post(url, json=approve)
    assert result.status_code == 200, result.text
    assert result.json()["verification_score"] == 90
    assert campaign.status == "verified"
    assert len(campaign.reviews) == 2
    assert sum(finding.points_awarded for finding in campaign.findings) == 90
    assert "storage_path" not in result.text
    assert client.post(url, json=approve).status_code == 409


def test_low_evidence_needs_information_records_reason_without_fraud(client: TestClient, campaign, reviewer: User) -> None:
    login(client, reviewer.email, "review-password")
    url = f"/api/admin/campaigns/{campaign.public_id}/review"
    client.post(url, json={"decision": "under_review", "reason": "Begin review"})
    response = client.post(url, json={"decision": "needs_information", "reason": "Supply applicable authorization and identity evidence"})
    assert response.status_code == 200
    assert response.json()["status"] == "needs_information"
    assert response.json()["verification_score"] == 20
    assert response.json()["reviews"][0]["reason"] == "Supply applicable authorization and identity evidence"


def test_private_document_access_is_authenticated_and_confined(client: TestClient, db: Session, campaign, reviewer: User, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import main

    root = tmp_path / "private"
    root.mkdir()
    private = root / "permit.pdf"
    private.write_bytes(b"%PDF-1.7 evidence")
    monkeypatch.setattr(main, "STORAGE_ROOT", root)
    document = campaign.documents[0]
    document.storage_path = str(private)
    db.commit()
    url = f"/api/admin/documents/{document.public_id}"
    assert client.get(url).status_code == 401
    login(client, reviewer.email, "review-password")
    response = client.get(url)
    assert response.status_code == 200 and response.content.startswith(b"%PDF-")
    assert response.headers["cache-control"] == "no-store"
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF- confidential")
    document.storage_path = str(outside)
    db.commit()
    assert client.get(url).status_code == 404


def test_additive_migration_keeps_existing_campaign_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO campaigns (id, title) VALUES (7, 'Preserved campaign')"))
        connection.execute(text("CREATE TABLE reviews (id INTEGER PRIMARY KEY, reason TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO reviews (id, reason) VALUES (3, 'Existing approval audit')"))
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "DATABASE_PATH", str(path))
    database.init_db()
    database.init_db()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title, owner_id FROM campaigns WHERE id = 7")).one() == ("Preserved campaign", None)
        assert connection.execute(text("SELECT reason, threshold_override, override_reason, warnings_resolved FROM reviews WHERE id = 3")).one() == ("Existing approval audit", 0, None, 0)
    engine.dispose()


def test_public_threshold_account_revocation_and_qr_boundary(integrated_client: TestClient, db: Session, campaign, reviewer: User, tmp_path: Path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    qr_path = root / "donation.png"
    qr_path.write_bytes(b"\x89PNG\r\n\x1a\nDonation destination")
    qr = DonationQRCode(public_id=str(uuid4()), campaign_id=campaign.id, label="GCash", storage_path=str(qr_path), file_type="png")
    db.add(qr)
    campaign.status = "verified"
    campaign.verification_score = 79
    campaign.owner.verified = True
    campaign.admin_notes = "Private reviewer feedback"
    db.commit()
    detail_url = f"/api/campaigns/{campaign.public_id}"
    qr_url = f"{detail_url}/qr/{qr.public_id}"
    assert integrated_client.get("/api/campaigns").json()["total"] == 0
    assert integrated_client.get(detail_url).status_code == 404
    assert integrated_client.get(qr_url).status_code == 404
    campaign.verification_score = 80
    db.commit()
    response = integrated_client.get(detail_url)
    assert response.status_code == 200, response.text
    assert "Private reviewer feedback" not in response.text
    assert integrated_client.get("/api/campaigns").json()["total"] == 1
    assert response.json()["qr_codes"] == [{"public_id": qr.public_id, "label": "GCash", "image_url": qr_url}]
    for private_key in ["documents", "storage_path", "organizer_email", "organizer_phone", "admin_notes", "score_breakdown", "owner"]:
        assert private_key not in response.json()
    assert integrated_client.get(qr_url).status_code == 200
    assert integrated_client.get(f"/api/campaigns/wrong/qr/{qr.public_id}").status_code == 404
    assert integrated_client.get(f"/api/admin/qr/{qr.public_id}").status_code == 401
    login(integrated_client, reviewer.email, "review-password")
    assert integrated_client.get(f"/api/admin/qr/{qr.public_id}").status_code == 200
    assert integrated_client.patch(f"/api/admin/accounts/{campaign.owner.id}", json={"verified": False, "reason": "Recheck submitted identity"}).status_code == 200
    assert integrated_client.get("/api/campaigns").json()["total"] == 0
    assert integrated_client.get(detail_url).status_code == 404
    assert integrated_client.get(qr_url).status_code == 404


def test_pending_qr_visible_only_to_reviewers_and_confined(integrated_client: TestClient, db: Session, campaign, reviewer: User, tmp_path: Path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    qr_path = root / "donation.png"
    qr_path.write_bytes(b"\x89PNG\r\n\x1a\nDonation destination")
    qr = DonationQRCode(public_id=str(uuid4()), campaign_id=campaign.id, label="Bank", storage_path=str(qr_path), file_type="png")
    db.add(qr)
    db.commit()
    assert integrated_client.get(f"/api/campaigns/{campaign.public_id}/qr/{qr.public_id}").status_code == 404
    login(integrated_client, campaign.owner.email, "example-password")
    assert integrated_client.get(f"/api/admin/qr/{qr.public_id}").status_code == 403
    login(integrated_client, reviewer.email, "review-password")
    detail = integrated_client.get(f"/api/admin/campaigns/{campaign.public_id}").json()
    assert detail["qr_codes"][0]["image_url"] == f"/api/admin/qr/{qr.public_id}"
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\nPrivate outside file")
    qr.storage_path = str(outside)
    db.commit()
    assert integrated_client.get(detail["qr_codes"][0]["image_url"]).status_code == 404


def test_funds_ownership_exact_cents_and_reviewed_only_transparency(integrated_client: TestClient, db: Session, campaign, reviewer: User) -> None:
    campaign.owner.verified = True
    campaign.status = "verified"
    campaign.verification_score = 90
    db.commit()
    funds_url = f"/api/my/campaigns/{campaign.public_id}/funds"
    public_url = f"/api/campaigns/{campaign.public_id}"
    report = {"kind": "received", "amount": "123.45", "description": "Donation batch deposited", "occurred_on": date.today().isoformat()}
    assert integrated_client.post(funds_url, json=report).status_code == 401
    login(integrated_client, reviewer.email, "review-password")
    # A privileged reviewer still cannot impersonate a campaign owner.
    assert integrated_client.get(funds_url).status_code == 404
    assert integrated_client.post(funds_url, json=report).status_code == 404
    login(integrated_client, campaign.owner.email, "example-password")
    result = integrated_client.post(funds_url, json=report)
    assert result.status_code == 201, result.text
    received = result.json()
    assert received["amount_centavos"] == 12345 and received["status"] == "pending"
    assert integrated_client.get(public_url).json()["transparency"]["received_centavos"] == 0
    assert integrated_client.patch(f"/api/admin/fund-updates/{received['public_id']}", json={"status": "approved", "reason": "Confirmed reported deposit"}).status_code == 403
    spent = integrated_client.post(funds_url, json={**report, "kind": "spent", "amount": "23.45", "description": "Food packs"}).json()
    rejected = integrated_client.post(funds_url, json={**report, "amount": "999.99", "description": "Duplicate donation batch"}).json()
    assert integrated_client.post(funds_url, json={**report, "amount": "1.001"}).status_code == 422
    assert integrated_client.post(funds_url, json={**report, "amount": "0"}).status_code == 422
    assert integrated_client.post(funds_url, json={**report, "occurred_on": (date.today() + timedelta(days=1)).isoformat()}).status_code == 422
    assert integrated_client.post(funds_url, json={**report, "status": "approved"}).status_code == 422
    login(integrated_client, reviewer.email, "review-password")
    for entry, status in [(received, "approved"), (spent, "approved"), (rejected, "rejected")]:
        url = f"/api/admin/fund-updates/{entry['public_id']}"
        assert integrated_client.patch(url, json={"status": status, "reason": "Human reviewed report"}).status_code == 200
        assert integrated_client.patch(url, json={"status": "approved", "reason": "Try second review"}).status_code == 409
    transparency = integrated_client.get(public_url).json()["transparency"]
    assert transparency["received_centavos"] == 12345
    assert transparency["spent_centavos"] == 2345
    assert transparency["balance_centavos"] == 10000
    assert len(transparency["entries"]) == 2
    assert all(entry["status"] == "approved" for entry in transparency["entries"])
    assert all("review_reason" not in entry and "reviewed_by" not in entry for entry in transparency["entries"])


def test_owned_campaign_list_excludes_other_organizers(integrated_client: TestClient, db: Session, campaign, organizer: User, reviewer: User) -> None:
    other = crud.create_campaign(db, owner_id=reviewer.id, organizer_name="Other owner", title="Other submission", description="Other", purpose="Relief", location="Leyte", target_amount=100)
    login(integrated_client, organizer.email, "example-password")
    items = integrated_client.get("/api/my/campaigns").json()
    assert [item["public_id"] for item in items] == [campaign.public_id]
    assert integrated_client.get(f"/api/my/campaigns/{other.public_id}/funds").status_code == 404


def test_threshold_exception_requires_verified_owner_resolved_warnings_and_audit(integrated_client: TestClient, db: Session, campaign, reviewer: User) -> None:
    login(integrated_client, reviewer.email, "review-password")
    url = f"/api/admin/campaigns/{campaign.public_id}/review"
    public_url = f"/api/campaigns/{campaign.public_id}"
    assert integrated_client.post(url, json={"decision": "under_review", "reason": "Manual review started"}).status_code == 200
    exception = {"decision": "verified", "reason": "Evidence manually inspected", "override_threshold": True, "override_reason": "Alternative corroborating evidence reviewed; missing document points remain visible", "warnings_resolved": True}
    assert integrated_client.post(url, json=exception).status_code == 422
    campaign.owner.verified = True
    db.commit()
    assert integrated_client.post(url, json={**exception, "override_threshold": False}).status_code == 422
    assert integrated_client.post(url, json={**exception, "warnings_resolved": False}).status_code == 422
    assert integrated_client.post(url, json={**exception, "override_reason": "   "}).status_code == 422
    assert integrated_client.post(url, json={**exception, "override_reason": None}).status_code == 422
    assert integrated_client.post(url, json={**exception, "decision": "needs_information"}).status_code == 422
    assert integrated_client.get(public_url).status_code == 404
    assert len(campaign.reviews) == 1 and campaign.status == "under_review"
    approved = integrated_client.post(url, json=exception)
    assert approved.status_code == 200, approved.text
    assert approved.json()["verification_score"] == 20
    audit = approved.json()["reviews"][0]
    assert audit["threshold_override"] and audit["warnings_resolved"]
    assert audit["override_reason"] == exception["override_reason"]
    assert audit["reason"] == exception["reason"]
    assert integrated_client.get(public_url).status_code == 200
    assert integrated_client.get("/api/campaigns").json()["total"] == 1
    assert integrated_client.post(url, json={"decision": "under_review", "reason": "Reopened after new concern"}).status_code == 200
    assert integrated_client.get(public_url).status_code == 404
    followup = integrated_client.post(url, json={"decision": "needs_information", "reason": "Await replacement evidence"})
    assert followup.status_code == 200
    assert followup.json()["reviews"][0]["threshold_override"] is False
    assert any(review["threshold_override"] for review in followup.json()["reviews"])
    # An old exception cannot republish after a newer decision superseded it.
    campaign.status = "verified"
    db.commit()
    assert integrated_client.get(public_url).status_code == 404


def test_requested_evidence_upload_reopens_review_privately_and_preserves_feedback(integrated_client: TestClient, db: Session, campaign, reviewer: User, tmp_path: Path) -> None:
    login(integrated_client, reviewer.email, "review-password")
    review_url = f"/api/admin/campaigns/{campaign.public_id}/review"
    integrated_client.post(review_url, json={"decision": "under_review", "reason": "Manual inspection started"})
    feedback = "Provide readable applicable authorization and organizer identity evidence"
    request = integrated_client.post(review_url, json={"decision": "needs_information", "reason": feedback})
    assert request.status_code == 200
    assert campaign.verification_score == 20 and len(campaign.findings) == 5
    old_audits = [(review.id, review.decision, review.reason) for review in campaign.reviews]
    upload_url = f"/api/my/campaigns/{campaign.public_id}/documents"
    file = ("documents", ("../../updated-permit.pdf", b"%PDF-1.7 readable authorization", "application/pdf"))
    # Even an administrator must use the organizer's own review workflow.
    assert integrated_client.post(upload_url, files=[file]).status_code == 404
    login(integrated_client, campaign.owner.email, "example-password")
    owner_campaign = integrated_client.get("/api/my/campaigns").json()[0]
    assert owner_campaign["status"] == "needs_information" and owner_campaign["admin_notes"] == feedback
    response = integrated_client.post(upload_url, files=[file])
    assert response.status_code == 201, response.text
    assert response.json() == {"public_id": campaign.public_id, "status": "under_review", "documents_received": 1}
    db.refresh(campaign)
    assert campaign.status == "under_review"
    assert campaign.verification_score is None and campaign.score_breakdown is None
    assert campaign.findings == []
    assert [(review.id, review.decision, review.reason) for review in campaign.reviews[:-1]] == old_audits
    assert campaign.reviews[-1].decision == "information_submitted"
    assert campaign.reviews[-1].previous_status == "needs_information"
    assert campaign.reviews[-1].new_status == "under_review"
    assert any(review.reason == feedback for review in campaign.reviews)
    owner_campaign = integrated_client.get("/api/my/campaigns").json()[0]
    assert owner_campaign["status"] == "under_review" and owner_campaign["admin_notes"] == feedback
    assert len(campaign.documents) == 2
    added = campaign.documents[-1]
    assert added.original_filename == "updated-permit.pdf"
    assert Path(added.storage_path).parent == tmp_path / "private"
    assert Path(added.storage_path).read_bytes() == b"%PDF-1.7 readable authorization"
    assert integrated_client.get(f"/api/campaigns/{campaign.public_id}").status_code == 404
    assert integrated_client.get(f"/api/admin/documents/{added.public_id}").status_code == 403


def test_requested_evidence_rejects_other_statuses_and_cleans_invalid_batch(integrated_client: TestClient, db: Session, campaign, tmp_path: Path) -> None:
    login(integrated_client, campaign.owner.email, "example-password")
    url = f"/api/my/campaigns/{campaign.public_id}/documents"
    valid = ("documents", ("permit.pdf", b"%PDF-1.7 readable authorization", "application/pdf"))
    for status in ["pending", "under_review", "verified", "rejected"]:
        campaign.status = status
        db.commit()
        assert integrated_client.post(url, files=[valid]).status_code == 409
        assert len(campaign.documents) == 1
    campaign.status = "needs_information"
    campaign.verification_score = 20
    campaign.score_breakdown = "Previously recorded findings"
    db.commit()
    invalid = ("documents", ("fake.pdf", b"not a PDF", "application/pdf"))
    response = integrated_client.post(url, files=[valid, invalid])
    assert response.status_code == 415
    db.refresh(campaign)
    assert campaign.status == "needs_information"
    assert campaign.verification_score == 20 and campaign.score_breakdown == "Previously recorded findings"
    assert len(campaign.documents) == 1
    assert len(db.scalars(select(Document).where(Document.campaign_id == campaign.id)).all()) == 1
    assert campaign.reviews == []
    assert list((tmp_path / "private").iterdir()) == []
