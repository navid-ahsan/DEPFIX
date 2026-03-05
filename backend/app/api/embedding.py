"""Embedding and indexing API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models.database import SetupStatus
from backend.app.services.embedding_service import embed_all_selected_dependencies

router = APIRouter(prefix="/api/v1/embedding", tags=["embedding"])


# Schemas
class StartEmbeddingRequest(BaseModel):
    dependency_names: List[str]


class EmbeddingStatusResponse(BaseModel):
    status: str  # pending, in_progress, completed, failed
    dependencies: dict
    progress_percent: int


async def background_embedding_task(
    db: Session,
    user_id: str,
    dependency_names: List[str],
):
    """Background task to embed documents."""
    try:
        await embed_all_selected_dependencies(db, user_id, dependency_names)
    except Exception as e:
        # Update status on error
        setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
        if setup:
            setup.embeddings_status = "failed"
            setup.last_error = str(e)
            from datetime import datetime
            setup.updated_at = datetime.utcnow()
            db.commit()


@router.post("/start")
async def start_embedding(
    request: StartEmbeddingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start embedding process for selected dependencies."""
    user_id = "test-user-123"  # TODO: Get from auth context
    
    if not request.dependency_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No dependencies specified",
        )
    
    # Update status to in_progress
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    if setup:
        setup.embeddings_status = "in_progress"
        from datetime import datetime
        setup.updated_at = datetime.utcnow()
        db.commit()
    
    # Add background task
    background_tasks.add_task(
        background_embedding_task,
        db,
        user_id,
        request.dependency_names,
    )
    
    return {
        "message": "Embedding started",
        "dependencies": request.dependency_names,
        "status": "in_progress",
        "next_step": "Poll /api/v1/embedding/status to monitor progress",
    }


@router.get("/status", response_model=EmbeddingStatusResponse)
async def get_embedding_status(
    db: Session = Depends(get_db),
):
    """Get current embedding status."""
    user_id = "test-user-123"  # TODO: Get from auth context
    
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    
    if not setup:
        return {
            "status": "pending",
            "dependencies": {},
            "progress_percent": 0,
        }
    
    # Calculate progress
    selected_count = len(setup.selected_dependencies) if setup.selected_dependencies else 0
    completed_count = 1 if setup.phase2_completed else 0
    progress = int((completed_count / selected_count * 100)) if selected_count > 0 else 0
    
    return {
        "status": setup.embeddings_status or "pending",
        "dependencies": setup.selected_dependencies or [],
        "progress_percent": progress,
    }


@router.post("/complete-phase2")
async def complete_phase2(
    db: Session = Depends(get_db),
):
    """Mark Phase 2 as complete."""
    user_id = "test-user-123"  # TODO: Get from auth context
    
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user_id).first()
    if setup:
        setup.phase2_completed = True
        from datetime import datetime
        setup.updated_at = datetime.utcnow()
        db.commit()
    
    return {
        "message": "Phase 2 completed",
        "phase2_completed": True,
        "next_step": "Proceed to Phase 3: GitHub/GitLab connection",
    }
