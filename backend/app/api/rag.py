"""RAG query and evaluation API endpoints."""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from backend.app.database import get_db
from backend.app.services.rag_service import RAGEngine
from backend.app.models.database import Query, Log
from backend.app.agents import OrchestratorAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

# Hardcoded user for now (TODO: Get from NextAuth session)
CURRENT_USER_ID = "test-user-123"


# ==================== REQUEST MODELS ====================

class AnalyzeErrorLogRequest(BaseModel):
    """Request model for error log analysis."""
    log_id: str
    dependencies: Optional[List[str]] = None


# ==================== PHASE 4: ERROR LOG ANALYSIS & RAG ====================

@router.post("/analyze-error-log")
async def analyze_error_log(
    request: AnalyzeErrorLogRequest,
    db: Session = Depends(get_db)
):
    """Analyze error log and generate fix suggestions using RAG.
    
    Args:
        request: AnalyzeErrorLogRequest with log_id and optional dependencies
        db: Database session
    
    Returns:
        Generated fix suggestions with retrieved documentation context
    """
    try:
        # Verify log exists and belongs to user
        log = db.query(Log).filter(
            Log.id == request.log_id,
            Log.user_id == CURRENT_USER_ID
        ).first()
        
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        
        if not log.is_processed:
            raise HTTPException(status_code=400, detail="Log not yet processed/analyzed")
        
        # Run RAG analysis (async — Ollama calls are run in thread pool)
        engine = RAGEngine(db)
        result = await engine.analyze_error_and_generate_fix(
            log_id=request.log_id,
            user_id=CURRENT_USER_ID,
            selected_dependencies=request.dependencies
        )
        
        logger.info(f"✓ RAG analysis complete for log {request.log_id}")
        
        return {
            "status": "success",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/{query_id}")
async def get_query_result(
    query_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve RAG query result and fix suggestions.
    
    Args:
        query_id: ID of query to retrieve
    
    Returns:
        Query details including fix suggestions and metadata
    """
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == CURRENT_USER_ID
        ).first()
        
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        log = db.query(Log).filter(Log.id == query.log_id).first()
        
        return {
            "status": "success",
            "data": {
                "query_id": query.id,
                "log_id": query.log_id,
                "log_filename": log.filename if log else None,
                "created_at": query.created_at.isoformat(),
                "query_intent": query.query_intent,
                "generated_response": query.generated_response,
                "suggested_fixes": query.suggested_fixes,
                "is_response_approved": query.is_response_approved,
                "is_evaluated": query.is_evaluated,
                "evaluation_score": query.evaluation_score
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries")
async def list_user_queries(
    log_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all RAG queries for current user.
    
    Args:
        log_id: Optional filter by specific log
    
    Returns:
        List of queries with summary information
    """
    try:
        query_builder = db.query(Query).filter(Query.user_id == CURRENT_USER_ID)
        
        if log_id:
            query_builder = query_builder.filter(Query.log_id == log_id)
        
        queries = query_builder.order_by(Query.created_at.desc()).all()
        
        return {
            "status": "success",
            "count": len(queries),
            "data": [
                {
                    "query_id": q.id,
                    "log_id": q.log_id,
                    "created_at": q.created_at.isoformat(),
                    "query_intent": q.query_intent,
                    "has_response": q.generated_response is not None,
                    "is_approved": q.is_response_approved
                }
                for q in queries
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-fix/{query_id}")
async def approve_fix(
    query_id: str,
    fix_index: int = 0,
    feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Approve a suggested fix.
    
    Args:
        query_id: ID of query with fix
        fix_index: Index of fix in suggested_fixes list
        feedback: Optional user feedback
    
    Returns:
        Updated query object
    """
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == CURRENT_USER_ID
        ).first()
        
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        if not query.suggested_fixes or fix_index >= len(query.suggested_fixes):
            raise HTTPException(status_code=400, detail="Invalid fix index")
        
        # Mark as approved
        query.is_response_approved = True
        query.accepted_fix = query.suggested_fixes[fix_index]
        
        # Store evaluation if provided
        if feedback:
            query.evaluation_feedback = feedback
            query.is_evaluated = True
        
        db.commit()
        
        logger.info(f"✓ Fix approved for query {query_id}")
        
        return {
            "status": "success",
            "message": "Fix approved",
            "query_id": query.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving fix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject-fix/{query_id}")
async def reject_fix(
    query_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reject a suggested fix.
    
    Args:
        query_id: ID of query with fix
        reason: Reason for rejection
    
    Returns:
        Updated query object
    """
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == CURRENT_USER_ID
        ).first()
        
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        query.is_response_approved = False
        
        if reason:
            query.evaluation_feedback = reason
            query.is_evaluated = True
        
        db.commit()
        
        logger.info(f"✓ Fix rejected for query {query_id}")
        
        return {
            "status": "success",
            "message": "Fix rejected",
            "query_id": query.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting fix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXISTING RAG ENDPOINTS ====================


class QueryRequest:
    """RAG query request."""

    def __init__(
        self,
        query_text: str,
        dependencies: List[str],
        log_id: Optional[str] = None,
        intent: str = "guidance",
    ):
        self.query_text = query_text
        self.dependencies = dependencies
        self.log_id = log_id
        self.intent = intent


@router.post("/query", response_model=dict)
async def rag_query(
    query_text: str,
    dependencies: List[str],
    log_id: Optional[str] = None,
    intent: str = "guidance",
) -> dict:
    """Execute a RAG query with retrieved context and LLM generation.

    Args:
        query_text: User query text
        dependencies: List of relevant dependencies
        log_id: Optional log file ID for context
        intent: Query intent (guidance, fix, analysis)

    Returns:
        Generated response with retrieved context
    """
    try:
        # Build orchestrator with all agents
        from backend.app.agents import (
            IntentAnalyzerAgent,
            DependencyExtractorAgent,
            DocScraperAgent,
            DataCleanerAgent,
            VectorManagerAgent,
            ErrorAnalyzerAgent,
            SolutionGeneratorAgent,
            AgentContext,
        )

        orchestrator = OrchestratorAgent()
        # register all agents in the desired order
        for AgentClass in [
            IntentAnalyzerAgent,
            DependencyExtractorAgent,
            DocScraperAgent,
            DataCleanerAgent,
            VectorManagerAgent,
            ErrorAnalyzerAgent,
            SolutionGeneratorAgent,
        ]:
            orchestrator.register_agent(AgentClass())

        orchestrator.set_execution_plan([
            "IntentAnalyzer",
            "DependencyExtractor",
            "DocScraper",
            "DataCleaner",
            "VectorManager",
            "ErrorAnalyzer",
            "SolutionGenerator",
        ])

        # prepare shared context
        context = AgentContext(
            user_intent=query_text,
            dependencies=dependencies,
        )
        if log_id:
            # placeholder: load log by id from storage
            context.error_log = log_id

        context = await orchestrator.execute(context)

        query_id = f"query_{datetime.utcnow().timestamp()}"

        return {
            "success": True,
            "query_id": query_id,
            "query": query_text,
            "dependencies": dependencies,
            "intent": intent,
            "response": context.solution,
            "parsed_error": context.parsed_error,
            "scraped_libraries": list(context.scraped_docs.keys()) if context.scraped_docs else [],
            "metadata": context.metadata,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error processing RAG query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}",
        )


@router.get("/query/{query_id}", response_model=dict)
async def get_query_result(query_id: str) -> dict:
    """Retrieve a previous query result.

    Args:
        query_id: Query ID

    Returns:
        Query result with response and metadata
    """
    try:
        # TODO: Query from database
        return {
            "success": True,
            "query_id": query_id,
            "query": "How do I fix PyTorch import errors?",
            "response": "Here's what I found...",
            "context_chunks": [],
            "is_evaluated": False,
            "evaluation_score": None,
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error retrieving query: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )


@router.post("/query/{query_id}/evaluate", response_model=dict)
async def evaluate_response(
    query_id: str,
    score: int,
    feedback: Optional[str] = None,
) -> dict:
    """Evaluate a generated response.

    Args:
        query_id: Query ID
        score: Evaluation score (1-5)
        feedback: User feedback text

    Returns:
        Evaluation recorded response
    """
    try:
        if not (1 <= score <= 5):
            raise ValueError("Score must be between 1 and 5")

        # TODO: Save evaluation to database

        logger.info(f"Evaluated query {query_id} with score {score}")

        return {
            "success": True,
            "query_id": query_id,
            "score": score,
            "feedback_received": feedback is not None,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error evaluating response: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error evaluating response: {str(e)}",
        )


@router.get("/query/history", response_model=dict)
async def get_query_history(
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Get user's query history.

    Args:
        limit: Number of results
        offset: Pagination offset

    Returns:
        List of previous queries
    """
    try:
        # TODO: Query from database
        queries = [
            {
                "query_id": "query_1",
                "query": "How to fix PyTorch version mismatch?",
                "created_at": "2024-01-15T10:30:00Z",
                "score": 5,
            },
            {
                "query_id": "query_2",
                "query": "ImportError when importing transformers",
                "created_at": "2024-01-14T15:45:00Z",
                "score": 4,
            },
        ]

        return {
            "success": True,
            "total": len(queries),
            "queries": queries[offset : offset + limit],
        }

    except Exception as e:
        logger.error(f"Error retrieving query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving history: {str(e)}",
        )


@router.post("/suggest-fix", response_model=dict)
async def suggest_code_fix(
    query_id: str,
    error_log: str,
) -> dict:
    """Suggest code fixes for an error.

    Args:
        query_id: Query ID
        error_log: Error log content

    Returns:
        Code fix suggestions
    """
    try:
        # TODO: Run CodeSuggesterAgent

        return {
            "success": True,
            "query_id": query_id,
            "suggestions": [
                {
                    "description": "Upgrade torch to 2.0+",
                    "code_before": "import torch",
                    "code_after": "# Ensure torch >= 2.0\nimport torch",
                    "confidence": 0.95,
                }
            ],
            "estimated_fix_time": "< 5 minutes",
        }

    except Exception as e:
        logger.error(f"Error suggesting fixes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error suggesting fixes: {str(e)}",
        )


@router.post("/approve-fix", response_model=dict)
async def approve_and_execute_fix(
    query_id: str,
    fix_index: int,
    background_tasks: BackgroundTasks,
) -> dict:
    """Approve and execute a suggested fix.

    Args:
        query_id: Query ID
        fix_index: Index of fix to execute
        background_tasks: FastAPI background tasks

    Returns:
        Execution status
    """
    try:
        # TODO: Run CodeExecutorAgent in background

        logger.info(f"Approved fix for query {query_id}")

        return {
            "success": True,
            "query_id": query_id,
            "fix_id": fix_index,
            "status": "executing",
            "message": "Fix is being applied, results will be available shortly",
        }

    except Exception as e:
        logger.error(f"Error executing fix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing fix: {str(e)}",
        )


@router.get("/batch-evaluate/{run_id}", response_model=dict)
async def batch_evaluate(run_id: str) -> dict:
    """Get evaluation metrics for a batch run.

    Args:
        run_id: Batch run ID

    Returns:
        Aggregated evaluation metrics
    """
    try:
        # TODO: Query evaluation metrics from database

        return {
            "success": True,
            "run_id": run_id,
            "total_queries": 100,
            "avg_score": 4.2,
            "perfect_score_count": 65,
            "accuracy": 0.92,
        }

    except Exception as e:
        logger.error(f"Error retrieving batch evaluation: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
