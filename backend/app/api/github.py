"""GitHub/GitLab integration and error log upload endpoints."""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models.database import User, Log
from backend.app.services.github_service import GitHubService, APIKeyManager
from backend.app.services.log_service import ErrorLogUploadService, ErrorLogAnalyzer

router = APIRouter(prefix="/api/v1", tags=["github", "logs"])


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
