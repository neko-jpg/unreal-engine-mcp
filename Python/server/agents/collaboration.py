"""Shared-state and orchestration helpers for cooperative agent workflows.

The design follows current practical patterns: a supervisor chooses the control
mode, specialists own narrow work, handoffs are explicit, guardrails/tracing are
first-class, and evidence is written to a shared blackboard rather than hidden
inside free-form messages.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass
class AgentTask:
    task_id: str
    intent: str
    domains: List[str]
    mode: str
    created_at: float = field(default_factory=time.time)
    status: str = "running"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "domains": list(self.domains),
            "mode": self.mode,
            "created_at": self.created_at,
            "status": self.status,
        }


@dataclass
class AgentObservation:
    agent: str
    success: bool
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "success": self.success,
            "summary": self.summary,
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
        }


@dataclass
class OrchestrationDecision:
    mode: str
    reason: str
    agents: List[str]
    needs_critic: bool = False
    needs_shared_state: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "reason": self.reason,
            "agents": list(self.agents),
            "needs_critic": self.needs_critic,
            "needs_shared_state": self.needs_shared_state,
        }


class SharedBlackboard:
    """Structured shared state for multi-agent collaboration."""

    def __init__(self) -> None:
        self.tasks: Dict[str, AgentTask] = {}
        self.observations: Dict[str, List[AgentObservation]] = {}
        self.evidence: Dict[str, List[Dict[str, Any]]] = {}
        self.decisions: List[OrchestrationDecision] = []

    def start_task(self, intent: str, domains: Iterable[str], mode: str) -> AgentTask:
        task = AgentTask(
            task_id=f"task_{time.time_ns()}",
            intent=intent,
            domains=list(domains),
            mode=mode,
        )
        self.tasks[task.task_id] = task
        self.observations[task.task_id] = []
        self.evidence[task.task_id] = []
        return task

    def add_observation(self, task_id: str, observation: AgentObservation) -> None:
        self.observations.setdefault(task_id, []).append(observation)

    def add_evidence(self, task_id: str, evidence: Mapping[str, Any]) -> None:
        self.evidence.setdefault(task_id, []).append(dict(evidence))

    def finish_task(self, task_id: str, status: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = status

    def snapshot(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        if task_id is not None:
            return {
                "task": self.tasks.get(task_id).to_dict() if task_id in self.tasks else None,
                "observations": [o.to_dict() for o in self.observations.get(task_id, [])],
                "evidence": list(self.evidence.get(task_id, [])),
                "decisions": [d.to_dict() for d in self.decisions],
            }
        return {
            "tasks": {key: task.to_dict() for key, task in self.tasks.items()},
            "observations": {
                key: [obs.to_dict() for obs in values]
                for key, values in self.observations.items()
            },
            "evidence": {key: list(values) for key, values in self.evidence.items()},
            "decisions": [d.to_dict() for d in self.decisions],
        }


class CollaborationKernel:
    """Policy layer for supervisor/handoff/critic orchestration."""

    def __init__(self) -> None:
        self.blackboard = SharedBlackboard()

    def decide(self, intent: str, domains: List[str], agent_names: List[str]) -> OrchestrationDecision:
        text = intent.lower()
        if any(term in text for term in ("quality", "critique", "score", "sqop", "evaluate")):
            decision = OrchestrationDecision(
                mode="critic_loop",
                reason="quality-sensitive request needs observe/critique/refine feedback",
                agents=agent_names,
                needs_critic=True,
            )
        elif len(agent_names) >= 3:
            decision = OrchestrationDecision(
                mode="supervisor",
                reason="three or more specialists require centralized sequencing and shared state",
                agents=agent_names,
                needs_critic="validation" in domains or "quality" in domains,
            )
        elif len(agent_names) == 2:
            decision = OrchestrationDecision(
                mode="handoff",
                reason="two specialists can run sequentially with explicit context handoff",
                agents=agent_names,
            )
        else:
            decision = OrchestrationDecision(
                mode="single",
                reason="one specialist owns the workflow",
                agents=agent_names,
                needs_shared_state=False,
            )
        self.blackboard.decisions.append(decision)
        return decision

    def start(self, intent: str, domains: List[str], decision: OrchestrationDecision) -> AgentTask:
        return self.blackboard.start_task(intent, domains, decision.mode)

    def record_result(self, task_id: str, agent_name: str, result: Any) -> None:
        success = bool(getattr(result, "success", False))
        error = getattr(result, "error", None)
        data = getattr(result, "data", {}) or {}
        metrics = getattr(result, "metrics", {}) or {}
        warnings = list(getattr(result, "warnings", []) or [])
        summary = "ok" if success else str(error or "failed")
        self.blackboard.add_observation(
            task_id,
            AgentObservation(
                agent=agent_name,
                success=success,
                summary=summary,
                metrics=dict(metrics),
                warnings=warnings,
            ),
        )
        if isinstance(data, Mapping):
            evidence = {
                key: data[key]
                for key in ("quality_vector", "quality_gate", "validation", "final_metrics", "final_cave_metrics")
                if key in data
            }
            if evidence:
                self.blackboard.add_evidence(task_id, evidence)

    def finish(self, task_id: str, success: bool) -> Dict[str, Any]:
        self.blackboard.finish_task(task_id, "complete" if success else "failed")
        return self.blackboard.snapshot(task_id)

    def reflection(self, task_id: str) -> Dict[str, Any]:
        observations = self.blackboard.observations.get(task_id, [])
        failed = [obs for obs in observations if not obs.success]
        warnings = [warning for obs in observations for warning in obs.warnings]
        return {
            "failed_agents": [obs.agent for obs in failed],
            "warning_count": len(warnings),
            "needs_retry": bool(failed),
            "needs_human_review": len(failed) >= 2 or len(warnings) > 8,
        }
