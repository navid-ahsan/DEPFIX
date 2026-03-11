"""GitHub Actions webhook endpoint — receives CI/CD workflow log payloads,
persists them to the database, and automatically triggers RAG analysis."""

import asyncio
import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db, SessionLocal
from backend.app.models.database import Log, User, DEPFIXApiKey
from backend.app.services.security import verify_key

router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)

_WEBHOOK_SECRET = os.environ.get("DEPFIX_WEBHOOK_SECRET", "")


# ── payload / response models ─────────────────────────────────────────────────

class GitHubActionsPayload(BaseModel):
    workflow_name: str
    run_id: str
    repository: str
    log_content: str
    branch: Optional[str] = "main"
    commit_sha: Optional[str] = None
    conclusion: Optional[str] = None   # "failure" | "success" | etc.


class WebhookResponse(BaseModel):
    received: bool
    log_id: str
    status: str
    message: str
    received_at: str


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_user_from_api_key(api_key_value: str, db: Session) -> Optional[User]:
    """Look up the User that owns a DEPFIX API key."""
    active_keys = db.query(DEPFIXApiKey).filter(DEPFIXApiKey.is_active == True).all()
    for record in active_keys:
        if verify_key(api_key_value, record.key_hash):
            try:
                record.last_used_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()
            return record.user
    return None


def _get_or_create_system_user(db: Session) -> User:
    """Return the dev/system user, creating it if needed."""
    user = db.query(User).filter(User.id == "test-user-123").first()
    if not user:
        user = User(id="test-user-123", username="testuser", email="test@test.com")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ── background analysis task ──────────────────────────────────────────────────

async def _run_auto_analysis(log_id: str, user_id: str, repository: str, commit_sha: Optional[str]) -> None:
    """Background task: extract errors from the saved log and run RAG analysis.

    Uses a fresh DB session so it can run independently of the request session.
    Posts a GitHub commit status when a token is available.
    """
    from backend.app.services.log_service import ErrorLogAnalyzer
    from backend.app.services.rag_service import RAGEngine, PipelineNotReadyError
    from backend.app.services.github_service import GitHubService, APIKeyManager

    db: Session = SessionLocal()
    try:
        log = db.query(Log).filter(Log.id == log_id).first()
        if not log:
            logger.error("Auto-analysis: log %s not found", log_id)
            return

        # Step 1 — extract errors and mark as processed
        analysis = ErrorLogAnalyzer.extract_errors(log.content, log.file_format)
        log.error_count = analysis["error_count"]
        log.primary_error_type = analysis.get("primary_error_type")
        log.primary_error_category = analysis.get("primary_error_category")
        log.extracted_errors = analysis
        log.error_summary = analysis
        log.is_processed = True
        db.commit()
        logger.info("✓ Error extraction complete for log %s (%d errors)", log_id, log.error_count)

        # Step 2 — RAG analysis (may be skipped if embeddings not yet ready)
        try:
            engine = RAGEngine(db)
            result = await engine.analyze_error_and_generate_fix(
                log_id=log_id,
                user_id=user_id,
            )
            logger.info("✓ RAG analysis complete for log %s → query %s", log_id, result["query_id"])
            analysis_status = "fix_available"
            gh_state = "success"
            gh_description = "DEPFIX: fix suggestion ready — check the dashboard"

        except PipelineNotReadyError as e:
            logger.warning("RAG pipeline not ready for log %s: %s", log_id, e)
            analysis_status = "pipeline_not_ready"
            gh_state = "pending"
            gh_description = "DEPFIX: embeddings not indexed yet — analysis queued"

        except Exception as e:
            logger.error("RAG analysis failed for log %s: %s", log_id, e, exc_info=True)
            analysis_status = "analysis_failed"
            gh_state = "failure"
            gh_description = "DEPFIX: analysis error — check server logs"

        # Step 3 — post GitHub commit status (best-effort)
        if commit_sha and repository and "/" in repository:
            try:
                owner, repo = repository.split("/", 1)
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    from backend.app.models.database import APIKey
                    api_key_record = db.query(APIKey).filter(
                        APIKey.user_id == user_id,
                        APIKey.service == "github",
                        APIKey.is_active == True,
                    ).first()
                    if api_key_record:
                        # Stored key is hashed — we can't reverse it here.
                        # GitHub status posting requires the plaintext token which
                        # is only available at authorize-time.
                        logger.info(
                            "GitHub commit status posting skipped "
                            "(stored token is hashed; future work: use a secrets vault)"
                        )
            except Exception as e:
                logger.warning("Failed to post GitHub commit status: %s", e)

    except Exception as e:
        logger.error("Unexpected error in auto-analysis for log %s: %s", log_id, e, exc_info=True)
    finally:
        db.close()


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/github-actions", response_model=WebhookResponse)
async def github_actions_webhook(
    payload: GitHubActionsPayload,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Receive a CI/CD failure log, persist it to the database, and kick off
    automatic RAG analysis in the background.

    **Authentication:** Include your DEPFIX API key in the `X-API-Key` header
    (generate one at `POST /api/v1/auth/keys`).  If no key is provided the
    request is accepted but attributed to the system/dev user.

    **GitHub Actions example:**
    ```yaml
    - name: Send failure log to DEPFIX
      if: failure()
      run: |
        curl -sX POST "${{ secrets.DEPFIX_URL }}/api/v1/webhook/github-actions" \\
          -H "Content-Type: application/json" \\
          -H "X-API-Key: ${{ secrets.DEPFIX_API_KEY }}" \\
          -d '{
            "workflow_name": "${{ github.workflow }}",
            "run_id":        "${{ github.run_id }}",
            "repository":    "${{ github.repository }}",
            "log_content":   "'"$(cat build.log | head -c 50000)"'",
            "branch":        "${{ github.ref_name }}",
            "commit_sha":    "${{ github.sha }}",
            "conclusion":    "failure"
          }'
    ```
    """
    if not payload.log_content.strip():
        raise HTTPException(status_code=422, detail="log_content must not be empty")

    # Resolve the calling user from the API key (optional — falls back to dev user)
    user: Optional[User] = None
    if x_api_key:
        user = _resolve_user_from_api_key(x_api_key, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked X-API-Key",
            )
    if not user:
        user = _get_or_create_system_user(db)

    # Persist log to database
    filename = f"{payload.repository.replace('/', '_')}_{payload.run_id}.log"
    log = Log(
        user_id=user.id,
        filename=filename,
        content=payload.log_content,
        file_format="log",
        file_size_bytes=len(payload.log_content.encode()),
        is_processed=False,
        error_count=0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    logger.info(
        "Webhook: persisted log %s — repo=%s workflow=%s run_id=%s bytes=%d",
        log.id, payload.repository, payload.workflow_name, payload.run_id, len(payload.log_content),
    )

    # Schedule background analysis (non-blocking)
    background_tasks.add_task(
        _run_auto_analysis,
        log.id,
        user.id,
        payload.repository,
        payload.commit_sha,
    )

    return WebhookResponse(
        received=True,
        log_id=log.id,
        status="analyzing",
        message=(
            f"Log saved ({len(payload.log_content)} bytes). "
            f"RAG analysis started — poll GET /api/v1/rag/queries?log_id={log.id} for results."
        ),
        received_at=datetime.utcnow().isoformat(),
    )


@router.get("/github-actions/status/{log_id}")
async def webhook_analysis_status(log_id: str, db: Session = Depends(get_db)):
    """Poll the analysis status for a previously submitted webhook log."""
    from backend.app.models.database import Query

    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    query = (
        db.query(Query)
        .filter(Query.log_id == log_id)
        .order_by(Query.created_at.desc())
        .first()
    )

    if not log.is_processed:
        state = "processing"
    elif query is None:
        state = "queued"
    elif query.generated_response:
        state = "complete"
    else:
        state = "analyzing"

    return {
        "log_id": log_id,
        "state": state,
        "is_processed": log.is_processed,
        "error_count": log.error_count,
        "primary_error_type": log.primary_error_type,
        "query_id": query.id if query else None,
        "has_fix": bool(query and query.suggested_fixes),
    }


@router.get("/github-actions/config")
async def webhook_config():
    """Return the webhook URL and required payload schema for CI configuration."""
    return {
        "endpoint": "/api/v1/webhook/github-actions",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-API-Key": "<your DEPFIX API key from POST /api/v1/auth/keys>",
        },
        "required_fields": ["workflow_name", "run_id", "repository", "log_content"],
        "optional_fields": ["branch", "commit_sha", "conclusion"],
        "poll_status": "GET /api/v1/webhook/github-actions/status/{log_id}",
        "view_fix": "GET /api/v1/rag/queries?log_id={log_id}",
    }
