"""Plan-and-Execute mode for long-term agent tasks.

References:
- Plan-and-Execute achieves 5.3x token reduction vs ReAct
- LangGraph planner-executor pattern
- DAG-based execution with dependency resolution

Usage:
    planner = TaskPlanner()
    plan = planner.create_plan(intent, domains=["cave", "lighting"])
    result = await planner.execute_plan(plan, context, orchestrator)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from server.agents.base_agent import AgentContext, AgentResult

logger = logging.getLogger("agents.planner")


# ---------------------------------------------------------------------------
# Domain coordination graph
# ---------------------------------------------------------------------------

# If domain A appears before domain B, A must execute before B.
_DOMAIN_DEPENDENCIES: Dict[str, List[str]] = {
    "cave": ["lighting"],
    "architecture": ["landscape"],
    "lighting": ["atmosphere"],
    "landscape": ["foliage"],
    "foliage": ["validation"],
    "npc": ["validation"],
    "vfx": ["validation"],
    "audio": ["validation"],
    "gameplay": ["validation"],
}


def _domain_must_precede(a: str, b: str) -> bool:
    """Return True if domain *a* must execute before domain *b*."""
    return b in _DOMAIN_DEPENDENCIES.get(a, [])


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    step_id: str
    agent_name: str
    domain: str
    intent: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | completed | failed
    result: Optional[AgentResult] = None
    retry_count: int = 0
    max_retries: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_name": self.agent_name,
            "domain": self.domain,
            "intent": self.intent,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionPlan:
    """A DAG of plan steps."""

    steps: List[PlanStep] = field(default_factory=list)
    original_intent: str = ""

    def get_ready_steps(self) -> List[PlanStep]:
        """Return steps whose dependencies are all completed."""
        completed = {s.step_id for s in self.steps if s.status == "completed"}
        return [
            s for s in self.steps
            if s.status == "pending" and all(d in completed for d in s.dependencies)
        ]

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def is_complete(self) -> bool:
        return all(s.status in ("completed", "failed") for s in self.steps)

    def all_succeeded(self) -> bool:
        return all(s.status == "completed" for s in self.steps)

    def failed_steps(self) -> List[PlanStep]:
        return [s for s in self.steps if s.status == "failed"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_intent": self.original_intent,
            "steps": [s.to_dict() for s in self.steps],
            "complete": self.is_complete(),
            "all_succeeded": self.all_succeeded(),
        }


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class TaskPlanner:
    """Creates and executes plans for complex multi-domain intents."""

    def __init__(self, max_parallel: int = 3) -> None:
        self.max_parallel = max_parallel

    def create_plan(
        self,
        intent: str,
        domain_agents: List[tuple[str, str]],
    ) -> ExecutionPlan:
        """Build an ExecutionPlan from an intent and selected domain agents.

        Args:
            intent: Original user intent
            domain_agents: List of (domain, agent_name) tuples

        Returns:
            ExecutionPlan with dependency-resolved steps
        """
        steps: List[PlanStep] = []
        domain_to_step_id: Dict[str, str] = {}

        # Create a step for each domain agent
        for idx, (domain, agent_name) in enumerate(domain_agents):
            step_id = f"step_{idx:02d}_{domain}"
            steps.append(
                PlanStep(
                    step_id=step_id,
                    agent_name=agent_name,
                    domain=domain,
                    intent=intent,
                )
            )
            domain_to_step_id[domain] = step_id

        # Add dependencies based on domain coordination rules
        for step in steps:
            for other in steps:
                if step.step_id == other.step_id:
                    continue
                if _domain_must_precede(other.domain, step.domain):
                    dep_id = domain_to_step_id.get(other.domain)
                    if dep_id and dep_id not in step.dependencies:
                        step.dependencies.append(dep_id)

        return ExecutionPlan(steps=steps, original_intent=intent)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: AgentContext,
        orchestrator: Any,
    ) -> AgentResult:
        """Execute a plan by delegating to the orchestrator.

        Steps are executed in parallel up to ``max_parallel`` where
        dependencies allow.

        Args:
            plan: ExecutionPlan to run
            context: AgentContext
            orchestrator: MasterOrchestrator with sub-agents registered

        Returns:
            Consolidated AgentResult
        """
        results: List[AgentResult] = []

        while not plan.is_complete():
            ready = plan.get_ready_steps()
            if not ready:
                # Deadlock or circular dependency
                failed = plan.failed_steps()
                return AgentResult(
                    success=False,
                    error="Plan execution stalled — no ready steps",
                    data={"plan": plan.to_dict(), "failed_steps": [s.step_id for s in failed]},
                )

            # Respect max_parallel limit
            batch = ready[: self.max_parallel]
            logger.info(
                "Executing plan batch: %s",
                ", ".join(f"{s.step_id}({s.domain})" for s in batch),
            )

            # Run batch concurrently
            batch_results = await asyncio.gather(
                *[self._execute_step(s, context, orchestrator) for s in batch],
                return_exceptions=True,
            )

            for step, outcome in zip(batch, batch_results):
                if isinstance(outcome, Exception):
                    step.status = "failed"
                    step.result = AgentResult(
                        success=False,
                        error=f"Step {step.step_id} threw {outcome}",
                    )
                    results.append(step.result)
                else:
                    step.result = outcome
                    if outcome.success:
                        step.status = "completed"
                    else:
                        step.status = "failed"
                        if step.retry_count < step.max_retries:
                            step.retry_count += 1
                            step.status = "pending"
                            logger.warning(
                                "Retrying step %s (attempt %d/%d)",
                                step.step_id,
                                step.retry_count,
                                step.max_retries,
                            )
                    results.append(outcome)

        # Final result
        merged = self._merge_step_results(results)
        merged.data["execution_plan"] = plan.to_dict()
        return merged

    async def _execute_step(
        self,
        step: PlanStep,
        context: AgentContext,
        orchestrator: Any,
    ) -> AgentResult:
        """Delegate a single plan step to the orchestrator."""
        return await orchestrator.delegate(
            step.agent_name,
            step.intent,
            context,
        )

    def _merge_step_results(self, results: List[AgentResult]) -> AgentResult:
        """Merge multiple step results into one AgentResult."""
        merged = AgentResult()
        merged.success = all(r.success for r in results)
        for r in results:
            if r.error:
                merged.warnings.append(r.error)
            merged.warnings.extend(r.warnings)
            merged.data.update(r.data)
            merged.metrics.update(r.metrics)
        return merged
