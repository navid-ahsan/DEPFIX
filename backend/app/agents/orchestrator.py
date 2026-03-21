"""
Orchestrator Agent - Master Coordinator
Manages the workflow and coordinates all specialized agents
"""

import asyncio
import logging
from time import perf_counter
from typing import Type, List

from .base import BaseAgent, AgentContext, AgentStatus

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Master orchestrator that manages the multi-agent workflow
    Coordinates execution, manages state, and handles communication between agents
    """

    def __init__(self):
        super().__init__(
            name="Orchestrator",
            description="Master workflow coordinator for multi-agent system"
        )
        self.agents: List[BaseAgent] = []
        self.execution_plan: List[str] = []  # Agent execution sequence
        self.current_step = 0

    def register_agent(self, agent: BaseAgent):
        """Register a new agent in the system"""
        self.agents.append(agent)
        self.logger.info(f"Registered agent: {agent.name}")

    def set_execution_plan(self, plan: List[str]):
        """
        Set the execution plan (sequence of agent names to run)

        Plan examples:
        - Discovery phase: ["IntentAnalyzer", "DependencyExtractor", "DocScraper"]
        - Preparation phase: ["DataCleaner", "VectorManager"]
        - Analysis phase: ["ErrorAnalyzer", "SolutionGenerator"]
        - Optional execution: ["CodeSuggester", "ApprovalManager", "CodeExecutor", "Evaluator"]
        """
        self.execution_plan = plan
        self.logger.info(f"Execution plan set: {' -> '.join(plan)}")

    def get_agent(self, name: str) -> BaseAgent:
        """Retrieve agent by name"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        raise ValueError(f"Agent not found: {name}")

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Execute the orchestration plan sequentially

        Workflow:
        1. Validate user input and intent
        2. Extract dependencies from intent
        3. Scrape documentation in parallel
        4. Clean and index documentation
        5. Wait for user error log upload
        6. Analyze error and generate solution
        7. Interactive loop: suggest fixes, get approval, execute
        8. Evaluate results
        """
        self.status = AgentStatus.RUNNING
        run_start = perf_counter()
        context.metadata.setdefault("agent_timings_ms", {})
        context.metadata.setdefault("execution_trace", [])
        self.log_message(context, f"Starting orchestration with {len(self.execution_plan)} agents")

        try:
            for agent_name in self.execution_plan:
                self.current_step += 1
                agent = self.get_agent(agent_name)

                self.log_message(
                    context,
                    f"[Step {self.current_step}/{len(self.execution_plan)}] Executing {agent_name}...",
                    level="info"
                )

                # Validate input for agent
                if not await agent.validate_input(context):
                    context.metadata["execution_trace"].append(
                        {
                            "agent": agent_name,
                            "status": "skipped",
                            "reason": "input_validation_failed",
                            "latency_ms": None,
                        }
                    )
                    self.log_message(
                        context,
                        f"Input validation failed for {agent_name}. Skipping.",
                        level="warning"
                    )
                    continue

                retry_policy = agent.contract.retry_policy
                max_attempts = max(1, retry_policy.max_attempts)
                last_error = None
                completed = False

                for attempt in range(1, max_attempts + 1):
                    try:
                        agent.status = AgentStatus.RUNNING
                        step_start = perf_counter()
                        context = await agent.execute(context)
                        elapsed_ms = (perf_counter() - step_start) * 1000
                        context.metadata["agent_timings_ms"][agent_name] = round(elapsed_ms, 2)
                        context.metadata["execution_trace"].append(
                            {
                                "agent": agent_name,
                                "status": "completed",
                                "reason": None,
                                "latency_ms": round(elapsed_ms, 2),
                                "retry_count": attempt - 1,
                                "fallback_applied": False,
                            }
                        )
                        agent.status = AgentStatus.COMPLETED
                        self.log_message(
                            context,
                            f"✓ {agent_name} completed successfully",
                            level="info"
                        )
                        completed = True
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt < max_attempts:
                            self.log_message(
                                context,
                                f"{agent_name} failed on attempt {attempt}/{max_attempts}; retrying.",
                                level="warning"
                            )
                            if retry_policy.backoff_ms > 0:
                                await asyncio.sleep(retry_policy.backoff_ms / 1000)
                            continue

                if completed:
                    continue

                agent.status = AgentStatus.FAILED
                fallback_mode = agent.contract.fallback_policy.mode
                if fallback_mode != "fail" and last_error is not None:
                    context = await agent.apply_fallback(context, last_error)
                    context.metadata["execution_trace"].append(
                        {
                            "agent": agent_name,
                            "status": "fallback",
                            "reason": str(last_error),
                            "latency_ms": None,
                            "retry_count": max_attempts - 1,
                            "fallback_applied": True,
                        }
                    )
                    self.logger.warning(f"Fallback applied for {agent_name}")
                    continue

                context.metadata["execution_trace"].append(
                    {
                        "agent": agent_name,
                        "status": "failed",
                        "reason": str(last_error) if last_error else "unknown_error",
                        "latency_ms": None,
                        "retry_count": max_attempts - 1,
                        "fallback_applied": False,
                    }
                )
                context = await agent.handle_error(context, last_error or RuntimeError("Unknown agent failure"))

                if self._is_critical_agent(agent_name):
                    self.logger.error(f"Critical agent failed: {agent_name}")
                    self.status = AgentStatus.FAILED
                    break

                self.logger.warning(f"Non-critical agent failed, continuing: {agent_name}")
                continue

            if self.status != AgentStatus.FAILED:
                self.status = AgentStatus.COMPLETED
                self.log_message(context, "✅ Orchestration completed successfully")
            context.metadata["orchestration_total_ms"] = round((perf_counter() - run_start) * 1000, 2)

        except Exception as e:
            self.status = AgentStatus.FAILED
            context.metadata["orchestration_total_ms"] = round((perf_counter() - run_start) * 1000, 2)
            self.log_message(context, f"Fatal orchestration error: {str(e)}", level="error")

        return context

    def _is_critical_agent(self, agent_name: str) -> bool:
        """Determine if agent failure should stop orchestration"""
        critical_agents = [
            "IntentAnalyzer",
            "ErrorAnalyzer",
            "SolutionGenerator",
        ]
        return agent_name in critical_agents

    def get_execution_status(self) -> dict:
        """Get current execution status"""
        return {
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": len(self.execution_plan),
            "agents_registered": len(self.agents),
            "agent_statuses": {agent.name: agent.status.value for agent in self.agents}
        }

    def reset(self):
        """Reset orchestrator for new execution cycle"""
        self.status = AgentStatus.IDLE
        self.current_step = 0
        for agent in self.agents:
            agent.status = AgentStatus.IDLE
        self.logger.info("Orchestrator reset")
