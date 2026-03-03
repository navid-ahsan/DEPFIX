"""
Orchestrator Agent - Master Coordinator
Manages the workflow and coordinates all specialized agents
"""

from typing import Type, List
import logging
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
                    self.log_message(
                        context,
                        f"Input validation failed for {agent_name}. Skipping.",
                        level="warning"
                    )
                    continue

                # Execute agent
                try:
                    agent.status = AgentStatus.RUNNING
                    context = await agent.execute(context)
                    agent.status = AgentStatus.COMPLETED

                    self.log_message(
                        context,
                        f"✓ {agent_name} completed successfully",
                        level="info"
                    )

                except Exception as e:
                    agent.status = AgentStatus.FAILED
                    context = await agent.handle_error(context, e)

                    # Decide whether to continue or fail
                    if self._is_critical_agent(agent_name):
                        self.logger.error(f"Critical agent failed: {agent_name}")
                        self.status = AgentStatus.FAILED
                        break
                    else:
                        self.logger.warning(f"Non-critical agent failed, continuing: {agent_name}")
                        continue

            self.status = AgentStatus.COMPLETED
            self.log_message(context, "✅ Orchestration completed successfully")

        except Exception as e:
            self.status = AgentStatus.FAILED
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
