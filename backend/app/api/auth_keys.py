"""DEPFIX API key management.

These keys are used by CI/CD pipelines to authenticate with the webhook
and by external tools calling the DEPFIX API.
"""

import os
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.database import DEPFIXApiKey, User
from backend.app.services.security import hash_key, verify_key

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Hardcoded dev user until NextAuth session is wired through
_DEV_USER_ID = "test-user-123"


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_dev_user(db: Session) -> User:
    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if not user:
        user = User(id=_DEV_USER_ID, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ── auth dependency (used by protected endpoints) ─────────────────────────────

def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency — validates X-API-Key header and returns the owner User.

    Raises 401 if the key is missing, unknown, or revoked.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Load all active keys for cheap iteration; keys are hashed so we must verify each
    active_keys = (
        db.query(DEPFIXApiKey)
        .filter(DEPFIXApiKey.is_active == True)
        .all()
    )
    for record in active_keys:
        if verify_key(x_api_key, record.key_hash):
            # Update last-used timestamp (fire-and-forget — don't fail on error)
            try:
                record.last_used_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()
            return record.user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# ── request / response schemas ────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str  # e.g. "GitHub Actions – backend repo"


class KeySummary(BaseModel):
    id: str
    name: str
    is_active: bool
    last_used_at: Optional[str]
    created_at: str


class CreateKeyResponse(BaseModel):
    id: str
    name: str
    key: str          # Returned ONCE — store it securely
    created_at: str
    message: str


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/keys", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateKeyRequest,
    db: Session = Depends(get_db),
):
    """Generate a new DEPFIX API key.

    The plaintext key is returned **once** — save it immediately.
    Subsequent requests only return metadata.
    """
    user = _get_or_create_dev_user(db)

    # Generate a cryptographically random key: "depfix_" prefix + 40 hex chars
    raw_key = "depfix_" + secrets.token_hex(20)

    record = DEPFIXApiKey(
        user_id=user.id,
        name=request.name,
        key_hash=hash_key(raw_key),
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return CreateKeyResponse(
        id=record.id,
        name=record.name,
        key=raw_key,
        created_at=record.created_at.isoformat(),
        message="Store this key securely — it will not be shown again.",
    )


@router.get("/keys", response_model=List[KeySummary])
async def list_api_keys(db: Session = Depends(get_db)):
    """List all API keys for the current user (no secrets returned)."""
    user = _get_or_create_dev_user(db)
    keys = (
        db.query(DEPFIXApiKey)
        .filter(DEPFIXApiKey.user_id == user.id)
        .order_by(DEPFIXApiKey.created_at.desc())
        .all()
    )
    return [
        KeySummary(
            id=k.id,
            name=k.name,
            is_active=k.is_active,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
    """Revoke (soft-delete) an API key."""
    user = _get_or_create_dev_user(db)
    record = (
        db.query(DEPFIXApiKey)
        .filter(DEPFIXApiKey.id == key_id, DEPFIXApiKey.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Key not found")

    record.is_active = False
    db.commit()
