"""
Base Agent Class for Multi-Agent System
All specialized agents inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AgentContext:
    """Shared context across all agents in orchestration"""
    user_intent: Optional[str] = None
    user_id: Optional[str] = None
    session_id: str = field(default_factory=lambda: "session_default")

    # Discovery phase
    dependencies: List[str] = field(default_factory=list)
    detected_tech_stack: Dict[str, str] = field(default_factory=dict)  # name -> version

    # Preparation phase
    scraped_docs: Dict[str, Any] = field(default_factory=dict)  # dependency -> docs
    cleaned_docs: Dict[str, Any] = field(default_factory=dict)
    indexed_docs: bool = False

    # Analysis phase
    error_log: Optional[str] = None
    parsed_error: Optional[Dict[str, Any]] = None

    # Solution generation phase
    solution: Optional[str] = None
    suggested_fixes: List[Dict[str, Any]] = field(default_factory=list)

    # Execution phase
    approved_fix: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None

    # Metadata
    messages: List[str] = field(default_factory=list)  # Agent conversation log
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """Execution retry policy for a single agent."""
    max_attempts: int = 1
    backoff_ms: int = 0


@dataclass
class FallbackPolicy:
    """Fallback behavior after all retries are exhausted."""
    mode: str = "fail"  # fail | continue
    message: str = ""
    context_updates: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContract:
    """Explicit contract used for orchestration planning and validation."""
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)
    success_criteria: str = "Execution completed without error"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    fallback_policy: FallbackPolicy = field(default_factory=FallbackPolicy)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system
    """

    def __init__(self, name: str, description: str = "", contract: Optional[AgentContract] = None):
        """
        Initialize agent

        Args:
            name: Unique agent name
            description: Human-readable description
        """
        self.name = name
        self.description = description
        self.contract = contract or AgentContract()
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Execute agent's primary task

        Args:
            context: Shared orchestration context

        Returns:
            Updated context
        """
        pass

    def log_message(self, context: AgentContext, message: str, level: str = "info"):
        """Log message to context and logger"""
        formatted_msg = f"[{self.name}] {message}"
        context.messages.append(formatted_msg)

        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    async def validate_input(self, context:AgentContext) -> bool:
        """
        Validate required context before execution
        Override in subclasses
        """
        if self.contract.required_inputs:
            missing = [key for key in self.contract.required_inputs if not self._has_context_value(context, key)]
            if missing:
                self.logger.warning("Missing required input(s): %s", ", ".join(missing))
                return False
        return True

    def get_contract(self) -> Dict[str, Any]:
        """Return serializable contract snapshot for APIs/planners."""
        return {
            "agent": self.name,
            "description": self.description,
            "input_schema": self.contract.input_schema,
            "output_schema": self.contract.output_schema,
            "required_inputs": self.contract.required_inputs,
            "success_criteria": self.contract.success_criteria,
            "retry_policy": {
                "max_attempts": self.contract.retry_policy.max_attempts,
                "backoff_ms": self.contract.retry_policy.backoff_ms,
            },
            "fallback_policy": {
                "mode": self.contract.fallback_policy.mode,
                "message": self.contract.fallback_policy.message,
                "context_updates": self.contract.fallback_policy.context_updates,
            },
        }

    def _has_context_value(self, context: AgentContext, field_name: str) -> bool:
        if not hasattr(context, field_name):
            return False
        value = getattr(context, field_name)
        if value is None:
            return False
        if isinstance(value, (str, list, dict, tuple, set)) and len(value) == 0:
            return False
        return True

    async def handle_error(self, context: AgentContext, error: Exception) -> AgentContext:
        """
        Handle execution errors gracefully
        """
        error_msg = f"Agent failed: {str(error)}"
        self.log_message(context, error_msg, level="error")
        self.status = AgentStatus.FAILED
        return context

    async def apply_fallback(self, context: AgentContext, error: Exception) -> AgentContext:
        """Apply contract-defined fallback after retries are exhausted."""
        fallback = self.contract.fallback_policy
        if fallback.mode == "fail":
            return context

        for field_name, value in fallback.context_updates.items():
            setattr(context, field_name, value)

        context.metadata.setdefault("fallbacks", []).append(
            {
                "agent": self.name,
                "mode": fallback.mode,
                "reason": str(error),
            }
        )
        message = fallback.message or f"Applied fallback for {self.name} after retries were exhausted"
        self.log_message(context, message, level="warning")
        return context

    def __str__(self) -> str:
        return f"{self.name} ({self.status.value})"
