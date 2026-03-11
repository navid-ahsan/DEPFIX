"""GitHub/GitLab integration and error log upload endpoints."""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db, SessionLocal
from backend.app.models.database import User, Log, UserConfig
from backend.app.services.github_service import GitHubService, APIKeyManager
from backend.app.services.log_service import ErrorLogUploadService, ErrorLogAnalyzer

router = APIRouter(prefix="/api/v1", tags=["github", "logs"])


# ── schemas ───────────────────────────────────────────────────────────────────

class AuthorizeRequest(BaseModel):
    service: str  # github or gitlab
    access_token: str
    gitlab_url: Optional[str] = "https://gitlab.com"


class RepositoryResponse(BaseModel):
    name: str
    full_name: str
    url: str
    description: Optional[str]


class LogResponse(BaseModel):
    id: str
    filename: str
    file_format: str
    file_size_bytes: int
    error_count: int
    primary_error_type: Optional[str]
    is_processed: bool
    created_at: str


class UserInfoResponse(BaseModel):
    login: str
    name: Optional[str]
    avatar_url: Optional[str]


# ── helpers ───────────────────────────────────────────────────────────────────

_DEV_USER_ID = "test-user-123"


async def get_current_user() -> User:
    test_user = User(id=_DEV_USER_ID, username="testuser", email="test@test.com")
    return test_user


def _get_github_token(db: Session, user_id: str) -> Optional[str]:
    """Return the stored GitHub token for the user, or None."""
    cfg = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    return cfg.github_token if cfg else None


# ── background task ───────────────────────────────────────────────────────────

async def _analyze_github_log(log_id: str, user_id: str) -> None:
    """Background task: run error extraction + RAG analysis on a persisted log."""
    from backend.app.services.rag_service import RAGEngine, PipelineNotReadyError

    db: Session = SessionLocal()
    try:
        log = db.query(Log).filter(Log.id == log_id).first()
        if not log:
            return

        analysis = ErrorLogAnalyzer.extract_errors(log.content, log.file_format)
        log.error_count = analysis["error_count"]
        log.primary_error_type = analysis.get("primary_error_type")
        log.primary_error_category = analysis.get("primary_error_category")
        log.extracted_errors = analysis
        log.error_summary = analysis
        log.is_processed = True
        db.commit()

        try:
            engine = RAGEngine(db)
            await engine.analyze_error_and_generate_fix(log_id=log_id, user_id=user_id)
        except PipelineNotReadyError:
            pass  # Pipeline not ready yet — user can re-trigger from the dashboard
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Background analysis failed for %s: %s", log_id, e)
    finally:
        db.close()


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/github/authorize")
async def authorize_github(
    request: AuthorizeRequest,
    db: Session = Depends(get_db),
):
    """Authorize with GitHub/GitLab and store the access token for API calls."""
    user_id = _DEV_USER_ID

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()

    # Store hashed key for verification
    APIKeyManager.store_api_key(db, user, request.service, request.access_token)

    # Also persist the plaintext token in UserConfig for outbound API calls
    cfg = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    if not cfg:
        cfg = UserConfig(user_id=user_id)
        db.add(cfg)

    if request.service == "github":
        cfg.github_token = request.access_token
        db.commit()

        github = GitHubService(request.access_token)
        user_info = await github.get_user_info()
        if not user_info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub token")

        return {"message": "GitHub authorized successfully", "service": "github", "user": user_info}

    elif request.service == "gitlab":
        cfg.gitlab_token = request.access_token
        cfg.gitlab_url = request.gitlab_url
        db.commit()
        return {"message": "GitLab authorized successfully", "service": "gitlab"}

    else:
        raise HTTPException(status_code=400, detail=f"Service '{request.service}' not supported")


@router.get("/github/user", response_model=UserInfoResponse)
async def get_github_user(db: Session = Depends(get_db)):
    """Get authenticated GitHub user info."""
    token = _get_github_token(db, _DEV_USER_ID)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No GitHub token stored")

    github = GitHubService(token)
    user_info = await github.get_user_info()
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token invalid")
    return user_info


@router.get("/github/repos", response_model=List[RepositoryResponse])
async def get_github_repos(db: Session = Depends(get_db)):
    """Get user's GitHub repositories."""
    token = _get_github_token(db, _DEV_USER_ID)
    if not token:
        return []
    github = GitHubService(token)
    repos = await github.get_repositories()
    return repos or []


# ── NEW: fetch workflow runs & pull logs directly from GitHub ─────────────────

@router.get("/github/workflow-runs/{owner}/{repo}")
async def list_workflow_runs(
    owner: str,
    repo: str,
    limit: int = 10,
    failed_only: bool = True,
    db: Session = Depends(get_db),
):
    """List recent GitHub Actions workflow runs for a repository.

    When `failed_only=true` (default) only returns runs with conclusion=failure.
    """
    token = _get_github_token(db, _DEV_USER_ID)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No GitHub token — authorize first via POST /api/v1/github/authorize",
        )

    github = GitHubService(token)
    runs = await github.get_workflow_runs(owner, repo, limit=limit)
    if runs is None:
        raise HTTPException(status_code=502, detail="Failed to reach GitHub API")

    if failed_only:
        runs = [r for r in runs if r.get("conclusion") == "failure"]

    return {"repository": f"{owner}/{repo}", "runs": runs, "count": len(runs)}


@router.post("/github/workflow-runs/{owner}/{repo}/{run_id}/analyze")
async def fetch_and_analyze_run_logs(
    owner: str,
    repo: str,
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Fetch logs for a GitHub Actions run directly from the GitHub API and
    trigger RAG analysis — no need to send logs manually.

    Returns immediately with `log_id`; poll
    `GET /api/v1/webhook/github-actions/status/{log_id}` for results.
    """
    token = _get_github_token(db, _DEV_USER_ID)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No GitHub token — authorize first via POST /api/v1/github/authorize",
        )

    github = GitHubService(token)
    log_content = await github.get_workflow_logs(owner, repo, run_id)
    if not log_content:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Could not fetch logs for run {run_id}. "
                "The run may still be in progress or logs may have expired (GitHub keeps them 90 days)."
            ),
        )

    # Get/create dev user
    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if not user:
        user = User(id=_DEV_USER_ID, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()

    # Persist log
    filename = f"gh_{owner}_{repo}_{run_id}.log"
    log = Log(
        user_id=user.id,
        filename=filename,
        content=log_content[:200_000],   # cap at 200 KB
        file_format="log",
        file_size_bytes=len(log_content.encode()),
        is_processed=False,
        error_count=0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    background_tasks.add_task(_analyze_github_log, log.id, user.id)

    return {
        "status": "analyzing",
        "log_id": log.id,
        "run_id": run_id,
        "repository": f"{owner}/{repo}",
        "message": (
            f"Pulled {len(log_content)} bytes from GitHub. "
            f"Poll GET /api/v1/webhook/github-actions/status/{log.id} for results."
        ),
    }


# ── log upload / management ───────────────────────────────────────────────────

@router.post("/logs/upload")
async def upload_error_log(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an error log file.
    
    Accepts: .log, .txt, .json, .jsonl, .csv files
    Max size: 50MB
    """
    user_id = _DEV_USER_ID

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()
        db.refresh(user)

    content = await file.read()
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "txt"

    is_valid, error_msg = ErrorLogUploadService.validate_uploaded_file(file.filename, len(content))
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    log = ErrorLogUploadService.process_uploaded_file(db, user, file.filename, content, file_ext)
    if not log:
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")

    return {
        "message": "Log uploaded successfully",
        "log_id": log.id,
        "filename": log.filename,
        "error_count": log.error_count,
        "primary_error_type": log.primary_error_type,
    }


@router.get("/logs", response_model=List[LogResponse])
async def get_error_logs(db: Session = Depends(get_db), limit: int = 50):
    """Get user's uploaded error logs."""
    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if not user:
        return []

    logs = ErrorLogUploadService.get_user_logs(db, user, limit)
    return [
        {
            "id": log.id,
            "filename": log.filename,
            "file_format": log.file_format,
            "file_size_bytes": log.file_size_bytes or 0,
            "error_count": log.error_count or 0,
            "primary_error_type": log.primary_error_type,
            "is_processed": log.is_processed,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.delete("/logs/{log_id}")
async def delete_error_log(log_id: str, db: Session = Depends(get_db)):
    """Delete an error log."""
    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    success = ErrorLogUploadService.delete_log(db, log_id, user)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")

    return {"message": "Log deleted successfully"}


@router.get("/logs/{log_id}")
async def get_error_log(log_id: str, db: Session = Depends(get_db)):
    """Get details of a specific error log."""
    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    log = db.query(Log).filter(Log.id == log_id, Log.user_id == user.id).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")

    return {
        "id": log.id,
        "filename": log.filename,
        "content": log.content,
        "file_format": log.file_format,
        "file_size_bytes": log.file_size_bytes,
        "error_count": log.error_count,
        "primary_error_type": log.primary_error_type,
        "is_processed": log.is_processed,
        "error_summary": log.error_summary,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# Schemas
class AuthorizeRequest(BaseModel):
    service: str  # github or gitlab
    access_token: str
    gitlab_url: Optional[str] = "https://gitlab.com"


class RepositoryResponse(BaseModel):
    name: str
    full_name: str
    url: str
    description: Optional[str]


class LogResponse(BaseModel):
    id: str
    filename: str
    file_format: str
    file_size_bytes: int
    error_count: int
    primary_error_type: Optional[str]
    is_processed: bool
    created_at: str


class UserInfoResponse(BaseModel):
    login: str
    name: Optional[str]
    avatar_url: Optional[str]


# Helper function to get current user (placeholder)
async def get_current_user() -> User:
    """Get authenticated user - TODO: Implement proper auth."""
    # For now, return test user
    test_user = User(id="test-user-123", username="testuser", email="test@test.com")
    return test_user


@router.post("/github/authorize")
async def authorize_github(
    request: AuthorizeRequest,
    db: Session = Depends(get_db),
):
    """
    Authorize with GitHub/GitLab.
    
    This is called after the user authorizes via OAuth.
    Typically called from frontend after OAuth callback.
    """
    user_id = "test-user-123"  # TODO: Get from auth context
    
    # Get user or create test user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()
    
    # Store API key
    api_key = APIKeyManager.store_api_key(
        db,
        user,
        request.service,
        request.access_token,
    )
    
    if request.service == "github":
        # Verify it works by getting user info
        github = GitHubService(request.access_token)
        user_info = await github.get_user_info()
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub token",
            )
        
        return {
            "message": "GitHub authorized successfully",
            "service": "github",
            "user": user_info,
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service '{request.service}' not supported",
        )


@router.get("/github/user", response_model=UserInfoResponse)
async def get_github_user(
    db: Session = Depends(get_db),
):
    """Get authenticated GitHub user info."""
    user_id = "test-user-123"  # TODO: Get from auth
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    # TODO: Get stored access token from secure vault
    # For now, return mock data
    return {
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
    }


@router.get("/github/repos", response_model=List[RepositoryResponse])
async def get_github_repos(
    db: Session = Depends(get_db),
):
    """Get user's GitHub repositories."""
    user_id = "test-user-123"  # TODO: Get from auth
    
    # TODO: Get stored access token
    # For now, return empty list
    return []


@router.post("/logs/upload")
async def upload_error_log(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an error log file.
    
    Accepts: .log, .txt, .json, .jsonl, .csv files
    Max size: 50MB
    """
    user_id = "test-user-123"  # TODO: Get from auth
    
    # Get or create user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="testuser", email="test@test.com")
        db.add(user)
        db.commit()
    
    # Read file
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}",
        )
    
    # Validate file
    is_valid, error_msg = ErrorLogUploadService.validate_uploaded_file(
        file.filename,
        len(content),
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    # Store file
    file_format = file.filename.split('.')[-1].lower()
    log = ErrorLogUploadService.process_uploaded_file(
        db,
        user,
        file.filename,
        content,
        file_format,
    )
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store log",
        )
    
    # Analyze log
    ErrorLogAnalyzer.update_log_analysis(db, log)
    db.refresh(log)
    
    return {
        "message": "Log uploaded successfully",
        "log_id": log.id,
        "filename": log.filename,
        "error_count": log.error_count,
        "primary_error_type": log.primary_error_type,
    }


@router.get("/logs", response_model=List[LogResponse])
async def get_error_logs(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Get user's uploaded error logs."""
    user_id = "test-user-123"  # TODO: Get from auth
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    logs = ErrorLogUploadService.get_user_logs(db, user, limit)
    
    return [
        {
            "id": log.id,
            "filename": log.filename,
            "file_format": log.file_format,
            "file_size_bytes": log.file_size_bytes,
            "error_count": log.error_count or 0,
            "primary_error_type": log.primary_error_type,
            "is_processed": log.is_processed,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.delete("/logs/{log_id}")
async def delete_error_log(
    log_id: str,
    db: Session = Depends(get_db),
):
    """Delete an error log."""
    user_id = "test-user-123"  # TODO: Get from auth
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    success = ErrorLogUploadService.delete_log(db, log_id, user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found",
        )
    
    return {"message": "Log deleted successfully"}


@router.get("/logs/{log_id}")
async def get_error_log(
    log_id: str,
    db: Session = Depends(get_db),
):
    """Get details of a specific error log."""
    user_id = "test-user-123"  # TODO: Get from auth
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    log = db.query(Log).filter(
        Log.id == log_id,
        Log.user_id == user.id,
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found",
        )
    
    return {
        "id": log.id,
        "filename": log.filename,
        "content": log.content,
        "file_format": log.file_format,
        "file_size_bytes": log.file_size_bytes,
        "error_count": log.error_count,
        "primary_error_type": log.primary_error_type,
        "is_processed": log.is_processed,
        "error_summary": log.error_summary,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
