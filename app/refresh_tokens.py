"""Выдача и проверка opaque refresh-токенов (хранятся в БД в виде SHA-256 хеша)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
import os

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.utcnow()


def issue_token_pair(db: Session, user: User) -> dict[str, str]:
    """Создаёт access + refresh токены и сохраняет refresh в БД."""
    access_token = create_access_token(data={"sub": str(user.id)})
    plain_refresh = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(plain_refresh),
            expires_at=expires_at,
        )
    )
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": plain_refresh,
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, plain_refresh: str) -> dict[str, str]:
    """Ротация refresh-токена: старый отзывается, выдаётся новая пара."""
    token_hash = _hash_token(plain_refresh)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None or row.revoked_at is not None or row.expires_at < _utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    row.revoked_at = _utcnow()
    db.add(row)
    db.commit()
    return issue_token_pair(db, user)


def revoke_refresh_token(db: Session, plain_refresh: str) -> None:
    token_hash = _hash_token(plain_refresh)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is not None and row.revoked_at is None:
        row.revoked_at = _utcnow()
        db.add(row)
        db.commit()
