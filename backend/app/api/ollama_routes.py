"""Ollama model management — list, pull (streaming SSE), delete."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
import logging

from backend.app.database import get_db
from backend.app.models.database import UserConfig

router = APIRouter(prefix="/api/v1/ollama", tags=["ollama"])
logger = logging.getLogger(__name__)

CURRENT_USER_ID = "test-user-123"


def _get_ollama_url(db: Session) -> str:
    config = db.query(UserConfig).filter(UserConfig.user_id == CURRENT_USER_ID).first()
    if config and config.ollama_url:
        return config.ollama_url.rstrip("/")
    return "http://localhost:11434"


class PullModelRequest(BaseModel):
    model: str
    insecure: bool = False


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """List all models installed in the user's Ollama instance."""
    url = _get_ollama_url(db)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{url}/api/tags")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama at {url}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/running")
async def running_models(db: Session = Depends(get_db)):
    """List models currently loaded in memory."""
    url = _get_ollama_url(db)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{url}/api/ps")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/pull")
async def pull_model(request: PullModelRequest, db: Session = Depends(get_db)):
    """Stream model pull progress from Ollama as Server-Sent Events."""
    url = _get_ollama_url(db)

    async def _stream():
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                async with client.stream(
                    "POST",
                    f"{url}/api/pull",
                    json={"name": request.model, "insecure": request.insecure},
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield f"data: {line}\n\n"
            yield 'data: {"status":"done"}\n\n'
        except Exception as e:
            yield f'data: {{"status":"error","error":"{str(e)}"}}\n\n'

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.delete("/model/{model_name:path}")
async def delete_model(model_name: str, db: Session = Depends(get_db)):
    """Delete a model from the Ollama instance."""
    url = _get_ollama_url(db)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.request("DELETE", f"{url}/api/delete", json={"name": model_name})
            r.raise_for_status()
            return {"ok": True, "model": model_name}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/model-info/{model_name:path}")
async def model_info(model_name: str, db: Session = Depends(get_db)):
    """Return size and details for a model available on the Ollama registry."""
    url = _get_ollama_url(db)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Try local first (already installed)
            r = await client.post(f"{url}/api/show", json={"name": model_name})
            if r.status_code == 200:
                data = r.json()
                size_bytes = data.get("size", 0)
                return {
                    "model": model_name,
                    "size_bytes": size_bytes,
                    "size_gb": round(size_bytes / (1024 ** 3), 2) if size_bytes else None,
                    "installed": True,
                    "details": data.get("details", {}),
                }
    except Exception:
        pass

    # Not installed: return estimated size from common model name patterns
    size_estimate = _estimate_model_size(model_name)
    return {
        "model": model_name,
        "size_bytes": None,
        "size_gb": size_estimate,
        "installed": False,
        "details": {},
    }


def _estimate_model_size(model_name: str) -> float | None:
    """Very rough download size estimate from model name. Returns GB or None."""
    name = model_name.lower()
    size_map = [
        ("70b", 42.0), ("34b", 20.0), ("13b", 7.4), ("8b", 4.7),
        ("7b", 4.1), ("3b", 2.0), ("2b", 1.3), ("1b", 0.8),
        ("0.5b", 0.4), ("405b", 240.0), ("72b", 45.0),
    ]
    for key, gb in size_map:
        if key in name:
            return gb
    # Quantization tweaks
    if "q4" in name or "q4_k_m" in name:
        return None  # already factored in above
    return None
