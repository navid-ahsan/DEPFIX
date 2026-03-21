"""Agent run and contract APIs for traceability and governance."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agents import (
    IntentAnalyzerAgent,
    DependencyExtractorAgent,
    DocScraperAgent,
    DataCleanerAgent,
    VectorManagerAgent,
    ErrorAnalyzerAgent,
    SolutionGeneratorAgent,
)
from backend.app.database import get_db
from backend.app.models.database import AgentRun, AgentRunStep

router = APIRouter(prefix="/api/v1/agent-runs", tags=["agent-runs"])

CURRENT_USER_ID = "test-user-123"


@router.get("/contracts")
async def list_agent_contracts():
    """Return explicit contracts for core pipeline agents."""
    agents = [
        IntentAnalyzerAgent(),
        DependencyExtractorAgent(),
        DocScraperAgent(),
        DataCleanerAgent(),
        VectorManagerAgent(),
        ErrorAnalyzerAgent(),
        SolutionGeneratorAgent(),
    ]
    return {
        "count": len(agents),
        "contracts": [agent.get_contract() for agent in agents],
    }


@router.get("")
async def list_runs(limit: int = 20, db: Session = Depends(get_db)):
    """List latest orchestration runs for the current user."""
    rows = (
        db.query(AgentRun)
        .filter(AgentRun.user_id == CURRENT_USER_ID)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(rows),
        "runs": [
            {
                "run_id": r.id,
                "status": r.status,
                "intent": r.intent,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "query_text": r.query_text,
                "metrics": r.metrics,
            }
            for r in rows
        ],
    }


@router.get("/{run_id}")
async def get_run_details(run_id: str, db: Session = Depends(get_db)):
    """Return full run graph, step statuses, and artifacts."""
    run = (
        db.query(AgentRun)
        .filter(AgentRun.id == run_id, AgentRun.user_id == CURRENT_USER_ID)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = (
        db.query(AgentRunStep)
        .filter(AgentRunStep.run_id == run_id)
        .order_by(AgentRunStep.step_order.asc())
        .all()
    )

    return {
        "run": {
            "run_id": run.id,
            "status": run.status,
            "query_text": run.query_text,
            "intent": run.intent,
            "selected_dependencies": run.selected_dependencies,
            "execution_plan": run.execution_plan,
            "run_graph": run.run_graph,
            "budget": run.budget,
            "metrics": run.metrics,
            "error_text": run.error_text,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        },
        "steps": [
            {
                "step_order": s.step_order,
                "agent_name": s.agent_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "latency_ms": s.latency_ms,
                "retry_count": s.retry_count,
                "input_snapshot": s.input_snapshot,
                "output_summary": s.output_summary,
                "tool_calls": s.tool_calls,
                "artifacts": s.artifacts,
                "error_text": s.error_text,
            }
            for s in steps
        ],
    }
