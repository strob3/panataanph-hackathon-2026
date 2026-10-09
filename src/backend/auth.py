"""Password, session, and role helpers for local PanataanPH accounts."""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Account, AuthSession

SESSION_COOKIE = "panataan_session"
SESSION_DAYS = 7
PASSWORD_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def create_session(db: Session, account: Account, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.add(AuthSession(account_id=account.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("PANATAANPH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/api",
    )


def get_current_account(request: Request, db: Session) -> Account:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Log in to continue")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    account = db.execute(
        select(Account)
        .join(AuthSession, AuthSession.account_id == Account.id)
        .where(
            AuthSession.token_hash == token_hash,
            AuthSession.expires_at > datetime.now(timezone.utc),
            Account.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")
    return account


def delete_session(request: Request, db: Session, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = db.execute(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        ).scalar_one_or_none()
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/api", httponly=True, samesite="lax")
