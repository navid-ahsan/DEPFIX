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


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize agent

        Args:
            name: Unique agent name
            description: Human-readable description
        """
        self.name = name
        self.description = description
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
        return True

    async def handle_error(self, context: AgentContext, error: Exception) -> AgentContext:
        """
        Handle execution errors gracefully
        """
        error_msg = f"Agent failed: {str(error)}"
        self.log_message(context, error_msg, level="error")
        self.status = AgentStatus.FAILED
        return context

    def __str__(self) -> str:
        return f"{self.name} ({self.status.value})"
