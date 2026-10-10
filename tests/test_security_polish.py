"""Tests for deployment polish: rate limiting and session cleanup."""

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend import auth
from backend.database import Base, get_db
from backend.models import AuthSession, User
from backend.security import InMemoryRateLimiter, require_rate_limit


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_in_memory_rate_limiter_logic() -> None:
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=0.5)
    key = "user_1"

    # First 3 allowed
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True

    # 4th rejected
    assert limiter.is_allowed(key) is False

    # Different key allowed
    assert limiter.is_allowed("user_2") is True

    # After window expires, allowed again
    time.sleep(0.55)
    assert limiter.is_allowed(key) is True


def test_cleanup_expired_sessions(db: Session) -> None:
    # Create user
    user = User(
        name="Test User",
        email="cleanup@example.com",
        password_hash=auth.hash_password("password12345"),
        role="organizer",
        verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Active session (expires in 1 hour)
    active = AuthSession(
        token_hash="active_hash",
        user_id=user.id,
        expires_at=now + timedelta(hours=1),
    )
    # Expired session (expired 1 hour ago)
    expired1 = AuthSession(
        token_hash="expired_hash_1",
        user_id=user.id,
        expires_at=now - timedelta(hours=1),
    )
    # Expired session (expired 1 minute ago)
    expired2 = AuthSession(
        token_hash="expired_hash_2",
        user_id=user.id,
        expires_at=now - timedelta(minutes=1),
    )

    db.add_all([active, expired1, expired2])
    db.commit()

    deleted = auth.cleanup_expired_sessions(db)
    assert deleted == 2

    # Check database state
    remaining = db.query(AuthSession).all()
    assert len(remaining) == 1
    assert remaining[0].token_hash == "active_hash"


def test_rate_limit_http_429(monkeypatch: pytest.MonkeyPatch) -> None:
    test_app = FastAPI()
    test_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60.0)

    # Force enable rate limiter for this specific test
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("backend.security.RATE_LIMIT_ENABLED", True)

    @test_app.get(
        "/test-endpoint",
        dependencies=[Depends(require_rate_limit(test_limiter, "test_action"))],
    )
    def endpoint() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(test_app)

    # Requests 1 and 2 succeed
    res1 = client.get("/test-endpoint")
    assert res1.status_code == 200

    res2 = client.get("/test-endpoint")
    assert res2.status_code == 200

    # Request 3 should trigger 429
    res3 = client.get("/test-endpoint")
    assert res3.status_code == 429
    assert "Too many test_action requests" in res3.json()["detail"]
    assert "retry-after" in res3.headers
