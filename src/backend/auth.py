"""Local accounts and revocable cookie sessions; no external identity provider."""

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuthSession, User
from backend.security import login_limiter, register_limiter, require_rate_limit

router = APIRouter(prefix="/api/auth", tags=["accounts"])
Database = Annotated[Session, Depends(get_db)]
SESSION_COOKIE = "panataanph_session"
SESSION_SECONDS = 8 * 60 * 60
ALLOWED_ORIGINS = {
    origin.strip().casefold()
    for origin in os.getenv("PANATAANPH_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}


def cleanup_expired_sessions(db: Session) -> int:
    """Delete expired AuthSession records and return count deleted."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    db.commit()
    return int(result.rowcount or 0)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    verified: bool


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Valid email required")
        return value


class RegisterInput(LoginInput):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name required")
        return value.strip()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, encoded: str) -> bool:
    algorithm, salt, expected = encoded.split("$")
    if algorithm != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(digest.hex(), expected)


def require_same_origin(request: Request) -> None:
    """Protect cookie-authenticated mutations, including login, against CSRF."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site request forbidden")
    source = request.headers.get("origin") or request.headers.get("referer")
    if source:
        try:
            origin = urlsplit(source)
        except ValueError as error:
            raise HTTPException(403, "Invalid request origin") from error
        origin_netloc = origin.netloc.lower()
        full_origin = f"{origin.scheme}://{origin.netloc}".casefold()
        direct_host = request.headers.get("host", "").lower()
        forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip().lower()

        is_same_host = origin_netloc in {direct_host, forwarded_host} if (direct_host or forwarded_host) else False
        is_allowed = origin_netloc in ALLOWED_ORIGINS or full_origin in ALLOWED_ORIGINS
        if not (is_same_host or is_allowed):
            raise HTTPException(403, "Cross-origin request forbidden")


def current_user(request: Request, db: Database) -> User:
    require_same_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if session is None or session.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(401, "Login required")
    return session.user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser) -> User:
    if user.role not in {"admin", "lgu"} or not user.verified:
        raise HTTPException(403, "Verified admin or LGU account required")
    return user


AdminUser = Annotated[User, Depends(admin_user)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(require_rate_limit(register_limiter, "register"))],
)
def register(data: RegisterInput, request: Request, db: Database) -> User:
    require_same_origin(request)
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role="organizer", verified=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Email already registered") from error
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=UserResponse,
    dependencies=[Depends(require_rate_limit(login_limiter, "login"))],
)
def login(data: LoginInput, request: Request, response: Response, db: Database) -> User:
    require_same_origin(request)
    cleanup_expired_sessions(db)
    user = db.scalar(select(User).where(User.email == data.email))
    # Do the same password work for unknown accounts to avoid a timing oracle.
    fallback = "scrypt$00000000000000000000000000000000$" + "0" * 128
    valid = check_password(data.password, user.password_hash if user else fallback)
    if user is None or not valid:
        raise HTTPException(401, "Email or password incorrect")
    old_token = request.cookies.get(SESSION_COOKIE)
    old_session = db.get(AuthSession, hashlib.sha256(old_token.encode()).hexdigest()) if old_token else None
    if old_session:
        db.delete(old_session)
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=SESSION_SECONDS)))
    db.commit()
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=is_secure, samesite="strict", path="/api")
    return user


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Database) -> None:
    require_same_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/api", httponly=True, samesite="strict")
