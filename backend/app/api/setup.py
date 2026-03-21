"""Setup and onboarding API endpoints."""

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.database import User, UserConfig
from backend.app.services.setup_service import (
    AVAILABLE_DEPENDENCIES,
    get_available_dependencies,
    select_dependencies,
    load_docs_from_local_jsonl,
    get_setup_status,
    check_doc_availability,
    mark_phase1_complete,
)
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

# ---------------------------------------------------------------------------
# In-memory doc-fetch status store (per user).  Keyed by user_id.
# Sufficient for a single-instance deployment; replace with DB/cache if scaled.
# ---------------------------------------------------------------------------
_fetch_status: Dict[str, Dict[str, Any]] = {}


# Schemas
class DependencyResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    category: str
    documentation_url: str
    repository_url: str


class SelectDependenciesRequest(BaseModel):
    dependency_names: List[str]
    custom_dependencies: Optional[List["CustomDependency"]] = []
    fetch_depth: Optional[str] = "balanced"   # "quick" | "balanced" | "full"


class CustomDependency(BaseModel):
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None


class SetupStatusResponse(BaseModel):
    phase1_completed: bool
    phase2_completed: bool
    phase3_completed: bool
    rag_ready: bool
    selected_dependencies: List[str] | None
    last_error: str | None


class DocLoadingStatusResponse(BaseModel):
    dependency: str
    status: str  # available, loading, completed, failed
    chunks_loaded: int


# Endpoints

@router.get("/dependencies", response_model=List[DependencyResponse])
async def list_dependencies(db: Session = Depends(get_db)):
    """Get list of all available dependencies."""
    return get_available_dependencies(db)


@router.post("/select")
async def select_deps_endpoint(
    request: SelectDependenciesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """User selects dependencies for Phase 1. Triggers background doc fetching."""

    # TODO: Get current user from auth context
    user_id = "test-user-123"

    # Validate preset dependencies exist (custom deps skip this check)
    available = get_available_dependencies(db)
    available_names = {dep["name"] for dep in available}
    custom_names = {c.name for c in (request.custom_dependencies or [])}

    invalid_deps = set(request.dependency_names) - available_names - custom_names
    if invalid_deps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dependencies: {invalid_deps}",
        )

    # Store selection
    from backend.app.models.database import User
    user = User(id=user_id, username="test", email="test@test.com")
    setup = select_dependencies(db, user, request.dependency_names)

    # Initialise fetch-status tracking
    all_dep_names = list(request.dependency_names) + [c.name for c in (request.custom_dependencies or [])]
    _fetch_status[user_id] = {name: {"status": "pending"} for name in all_dep_names}

    # Retrieve stored GitHub token (used for authenticated API calls)
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    github_token = config.github_token if config else None

    # Resolve max_files from fetch_depth
    from backend.app.services.docs_fetcher import DEPTH_PRESETS
    fetch_depth = (request.fetch_depth or "balanced").lower()
    max_files = DEPTH_PRESETS.get(fetch_depth, DEPTH_PRESETS["balanced"])

    # Build lookup: dep_name -> known repository_url (for custom deps with explicit URL)
    custom_url_map = {
        c.name: c.repository_url
        for c in (request.custom_dependencies or [])
        if c.repository_url
    }

    async def _do_fetch() -> None:
        from backend.app.services.docs_fetcher import fetch_and_save_docs, resolve_github_url
        from pathlib import Path

        # Known repo URLs from AVAILABLE_DEPENDENCIES
        known_urls = {k: v.get("repository_url") for k, v in AVAILABLE_DEPENDENCIES.items()}

        for dep_name in all_dep_names:
            _fetch_status[user_id][dep_name]["status"] = "fetching"
            try:
                repo_url = await resolve_github_url(
                    dep_name,
                    custom_repo_url=custom_url_map.get(dep_name),
                    known_urls=known_urls,
                )
                if repo_url:
                    result = await fetch_and_save_docs(dep_name, repo_url, github_token, max_files=max_files)
                else:
                    # No GitHub URL — check if we already have a local JSONL
                    local = Path(f"data/documents/{dep_name}.jsonl")
                    if local.exists():
                        result = {"status": "done", "chunks": 0, "files": 0, "requests_used": 0, "source": "local"}
                    else:
                        result = {"status": "error", "message": "No GitHub URL found and no local docs available", "chunks": 0, "files": 0, "requests_used": 0}
                _fetch_status[user_id][dep_name] = result
            except Exception as exc:
                _fetch_status[user_id][dep_name] = {"status": "error", "message": str(exc), "chunks": 0, "files": 0, "requests_used": 0}
    async def _do_fetch() -> None:
        import asyncio
        from backend.app.services.docs_fetcher import (
            fetch_and_save_docs, resolve_github_url, check_rate_limit,
        )
        from pathlib import Path

        known_urls = {k: v.get("repository_url") for k, v in AVAILABLE_DEPENDENCIES.items()}

        for dep_name in all_dep_names:
            _fetch_status[user_id][dep_name]["status"] = "fetching"
            try:
                # ── pre-fetch rate-limit guard ──────────────────────────────
                rl = await check_rate_limit(github_token)
                needed = max_files + 2  # 1 tree request + file requests
                if rl["remaining"] < needed:
                    wait_secs = rl["reset_in_sec"] + 10  # small buffer
                    reset_min = max(1, wait_secs // 60)
                    _fetch_status[user_id][dep_name]["status"] = "pending"
                    _fetch_status[user_id][dep_name]["message"] = (
                        f"Rate limited — pausing {reset_min} min then continuing"
                    )
                    # Wait for the rate limit window to reset, then retry
                    await asyncio.sleep(min(wait_secs, 3660))
                    _fetch_status[user_id][dep_name]["status"] = "fetching"
                    _fetch_status[user_id][dep_name].pop("message", None)

                repo_url = await resolve_github_url(
                    dep_name,
                    custom_repo_url=custom_url_map.get(dep_name),
                    known_urls=known_urls,
                )
                if repo_url:
                    result = await fetch_and_save_docs(dep_name, repo_url, github_token, max_files=max_files)
                else:
                    local = Path(f"data/documents/{dep_name}.jsonl")
                    if local.exists():
                        result = {"status": "done", "chunks": 0, "files": 0, "requests_used": 0, "source": "local"}
                    else:
                        result = {
                            "status": "warning",
                            "message": "No GitHub URL found and no local docs available",
                            "chunks": 0, "files": 0, "requests_used": 0,
                        }
                _fetch_status[user_id][dep_name] = result
            except Exception as exc:
                _fetch_status[user_id][dep_name] = {
                    "status": "error", "message": str(exc), "chunks": 0, "files": 0, "requests_used": 0,
                }
    background_tasks.add_task(_do_fetch)

    doc_availability = check_doc_availability(request.dependency_names)

    return {
        "message": "Dependencies selected. Documentation fetch started in background.",
        "selected": request.dependency_names,
        "custom": [c.name for c in (request.custom_dependencies or [])],
        "docs_available_locally": doc_availability,
        "fetch_status_url": "/api/v1/setup/fetch-docs/status",
    }


@router.get("/github-rate-limit")
async def get_github_rate_limit(db: Session = Depends(get_db)):
    """
    Return current GitHub API rate limit status for the stored token (or
    unauthenticated if no token is configured).

    Response:
      {
        "remaining":     int,   — requests left in current window
        "limit":         int,   — total requests per window (60 or 5000)
        "reset_at":      int,   — Unix timestamp when window resets
        "reset_in_min":  int,   — minutes until reset
        "authenticated": bool,  — True when a stored GitHub token is in use
        "can_fetch":     bool,  — True when remaining >= 5 (at least 1 dep worth)
      }
    """
    import time as _time

    user_id = "test-user-123"
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    github_token = (config.github_token if config else None) or os.getenv("GITHUB_TOKEN")

    headers: dict = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DEPFIX/1.0",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get("https://api.github.com/rate_limit", headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("rate", {})
            remaining = data.get("remaining", 0)
            limit     = data.get("limit", 60)
            reset_at  = data.get("reset", 0)
            reset_in  = max(0, int((reset_at - _time.time()) / 60))
            return {
                "remaining":    remaining,
                "limit":        limit,
                "reset_at":     reset_at,
                "reset_in_min": reset_in,
                "authenticated": bool(github_token),
                "can_fetch":    remaining >= 5,
            }
    except Exception:
        pass

    return {
        "remaining": 0, "limit": 60, "reset_at": 0, "reset_in_min": 0,
        "authenticated": bool(github_token), "can_fetch": False,
        "error": "Could not reach GitHub API",
    }


@router.get("/fetch-docs/status")
async def get_fetch_docs_status():
    """
    Return per-dependency documentation fetch progress for the current session.

    Response shape:
      {
        "all_done": bool,
        "deps": {
          "<name>": {
            "status": "pending" | "fetching" | "done" | "warning" | "error",
            "chunks": int,
            "files":  int,
            "message": str   // only on warning/error
          }
        }
      }
    """
    user_id = "test-user-123"
    deps = _fetch_status.get(user_id, {})
    done_statuses = {"done", "warning", "error"}
    all_done = bool(deps) and all(v.get("status") in done_statuses for v in deps.values())
    return {"all_done": all_done, "deps": deps}


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status_endpoint(
    db: Session = Depends(get_db),
):
    """Get current setup status for user."""
    # TODO: Get user from auth context
    user_id = "test-user-123"
    
    from backend.app.models.database import SetupStatus
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    
    if not setup:
        # Return default setup status if not found
        return {
            "phase1_completed": False,
            "phase2_completed": False,
            "phase3_completed": False,
            "rag_ready": False,
            "selected_dependencies": None,
            "last_error": None,
        }
    
    return {
        "phase1_completed": setup.phase1_completed,
        "phase2_completed": setup.phase2_completed,
        "phase3_completed": setup.phase3_completed,
        "rag_ready": setup.rag_ready,
        "selected_dependencies": setup.selected_dependencies,
        "last_error": setup.last_error,
    }


@router.get("/docs/{dependency_name}")
async def get_dependency_docs(
    dependency_name: str,
    db: Session = Depends(get_db),
):
    """Load docs for specific dependency from local storage."""
    
    # Load from local jsonl
    doc_data = load_docs_from_local_jsonl(dependency_name)
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documentation not found for {dependency_name}",
        )
    
    return {
        "dependency": dependency_name,
        "total_chunks": doc_data["total_chunks"],
        "sample_chunks": doc_data["sample_chunks"],
        "ready_for_embedding": doc_data["ready_for_embedding"],
        "next_step": "These docs will be embedded and indexed to vector DB in Phase 2",
    }


@router.post("/complete-phase1")
async def complete_phase1(
    db: Session = Depends(get_db),
):
    """Mark Phase 1 as complete."""
    # TODO: Get user from auth context
    user_id = "test-user-123"
    
    from backend.app.models.database import SetupStatus, User
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    
    if not setup:
        user = User(id=user_id, username="test", email="test@test.com")
        setup = SetupStatus(user_id=user_id)
        db.add(setup)
    
    setup.phase1_completed = True
    from datetime import datetime
    setup.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(setup)
    
    return {
        "message": "Phase 1 completed",
        "phase1_completed": setup.phase1_completed,
        "next_step": "Proceed to Phase 2: Embedding and Vector DB indexing",
    }


# ---------------------------------------------------------------------------
# Docs health check
# ---------------------------------------------------------------------------

_DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"


def _classify_source(source: str) -> str:
    if "/app/data/" in source or (source and source.startswith("/")):
        return "old_local"
    if "raw.githubusercontent.com" in source:
        return "github_raw"
    return "other"


@router.get("/docs-health")
async def get_docs_health():
    """
    Return per-dependency documentation health: chunk counts, data freshness,
    and top sections.  Used by the UI to detect stale data and suggest re-fetches.
    """
    result = {}
    for jsonl_path in sorted(_DOCS_DIR.glob("*.jsonl")):
        dep = jsonl_path.stem
        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
            records = [json.loads(l) for l in lines if l.strip()]
        except Exception:
            records = []

        if not records:
            result[dep] = {"chunks": 0, "source_type": "empty", "sections": [], "stale": True}
            continue

        source_types = Counter(_classify_source(r.get("source", "")) for r in records)
        sections = list({r.get("section", "") for r in records if r.get("section")})[:8]

        is_stale = source_types.get("old_local", 0) > 0

        result[dep] = {
            "chunks": len(records),
            "source_type": "old_local" if is_stale else "github_raw",
            "sections": sections,
            "stale": is_stale,
        }

    return {"deps": result}
