"""User configuration CRUD API — connectivity, models, LLM parameters."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
import httpx

from backend.app.database import get_db
from backend.app.models.database import UserConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["config"])

CURRENT_USER_ID = "test-user-123"


# ── Schemas ────────────────────────────────────────────────────────────────────

class UserConfigRequest(BaseModel):
    ollama_url: Optional[str] = None
    postgres_url: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    temperature: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    preferred_quantization: Optional[str] = None
    github_token: Optional[str] = None


class UserConfigResponse(BaseModel):
    ollama_url: str
    postgres_url: str
    llm_model: str
    embedding_model: str
    temperature: str
    max_tokens: int
    system_prompt: Optional[str]
    preferred_quantization: str
    github_token: Optional[str] = None


class ConnectionTestRequest(BaseModel):
    url: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_or_create_config(db: Session, user_id: str) -> UserConfig:
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    if not config:
        config = UserConfig(user_id=user_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def config_to_response(config: UserConfig) -> UserConfigResponse:
    return UserConfigResponse(
        ollama_url=config.ollama_url or "http://localhost:11434",
        postgres_url=config.postgres_url or "postgresql+psycopg2://postgres:password123@localhost:5432/vector_db",
        llm_model=config.llm_model or "",
        embedding_model=config.embedding_model or "nomic-embed-text",
        temperature=config.temperature or "0.2",
        max_tokens=config.max_tokens or 2048,
        system_prompt=config.system_prompt,
        preferred_quantization=config.preferred_quantization or "q4_K_M",
        github_token=config.github_token or None,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=UserConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    """Return current user configuration, creating defaults if none exist."""
    return config_to_response(get_or_create_config(db, CURRENT_USER_ID))


@router.put("/", response_model=UserConfigResponse)
async def save_config(request: UserConfigRequest, db: Session = Depends(get_db)):
    """Save (upsert) user configuration."""
    config = get_or_create_config(db, CURRENT_USER_ID)

    for field, value in request.dict(exclude_none=True).items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return config_to_response(config)


@router.post("/test/ollama")
async def test_ollama_connection(request: ConnectionTestRequest):
    """Test connectivity to an Ollama instance."""
    url = request.url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{url}/api/tags")
            if r.status_code == 200:
                data = r.json()
                model_count = len(data.get("models", []))
                return {"ok": True, "url": url, "models_available": model_count}
            return {"ok": False, "url": url, "error": f"HTTP {r.status_code}"}
    except httpx.ConnectError:
        return {"ok": False, "url": url, "error": "Connection refused — is Ollama running?"}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


@router.post("/test/postgres")
async def test_postgres_connection(request: ConnectionTestRequest):
    """Test connectivity to a PostgreSQL / pgvector database."""
    url = request.url
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}
