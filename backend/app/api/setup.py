"""Setup and onboarding API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.database import User
from backend.app.services.setup_service import (
    get_available_dependencies,
    select_dependencies,
    load_docs_from_local_jsonl,
    get_setup_status,
    check_doc_availability,
    mark_phase1_complete,
)
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


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
    db: Session = Depends(get_db),
):
    """User selects dependencies for Phase 1."""
    
    # TODO: Get current user from auth context
    # For now, use a test user ID
    user_id = "test-user-123"
    
    # Validate dependencies exist
    available = get_available_dependencies(db)
    available_names = {dep["name"] for dep in available}
    
    invalid_deps = set(request.dependency_names) - available_names
    if invalid_deps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dependencies: {invalid_deps}",
        )
    
    # Store selection (create a mock user object for now)
    from backend.app.models.database import User
    user = User(id=user_id, username="test", email="test@test.com")
    setup = select_dependencies(db, user, request.dependency_names)
    
    # Check doc availability
    doc_availability = check_doc_availability(request.dependency_names)
    
    return {
        "message": "Dependencies selected successfully",
        "selected": request.dependency_names,
        "docs_available": doc_availability,
        "next_step": "GET /api/v1/setup/status to monitor doc loading",
    }


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
