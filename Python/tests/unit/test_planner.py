"""Tests for the Plan-and-Execute planner module."""

from __future__ import annotations

import asyncio

import pytest

from server.agents.base_agent import AgentContext, AgentResult
from server.agents.planner import ExecutionPlan, PlanStep, TaskPlanner


class FakeOrchestrator:
    """Fake orchestrator for testing plan execution."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self._should_fail: set[str] = set()

    def fail_step(self, agent_name: str):
        self._should_fail.add(agent_name)

    async def delegate(self, agent_name: str, intent: str, context: AgentContext) -> AgentResult:
        self.calls.append((agent_name, intent))
        if agent_name in self._should_fail:
            return AgentResult(success=False, error=f"{agent_name} failed")
        return AgentResult(success=True, data={"agent": agent_name})


class TestPlanStep:
    def test_creation(self):
        step = PlanStep(step_id="s1", agent_name="a1", domain="lighting", intent="make it bright")
        assert step.status == "pending"
        assert step.dependencies == []
        assert step.result is None

    def test_to_dict(self):
        step = PlanStep(step_id="s1", agent_name="a1", domain="d1", intent="i1")
        step.status = "completed"
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["status"] == "completed"
        assert d["result"] is None


class TestExecutionPlan:
    def test_get_ready_steps_no_deps(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "lighting", "intent"),
            PlanStep("s2", "a2", "audio", "intent"),
        ])
        ready = plan.get_ready_steps()
        assert len(ready) == 2

    def test_get_ready_steps_with_deps(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "cave", "intent"),
            PlanStep("s2", "a2", "lighting", "intent", dependencies=["s1"]),
        ])
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

    def test_is_complete(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "d1", "intent"),
        ])
        assert not plan.is_complete()
        plan.steps[0].status = "completed"
        assert plan.is_complete()

    def test_all_succeeded(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "d1", "intent"),
            PlanStep("s2", "a2", "d2", "intent"),
        ])
        plan.steps[0].status = "completed"
        assert not plan.all_succeeded()
        plan.steps[1].status = "completed"
        assert plan.all_succeeded()

    def test_failed_steps(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "d1", "intent"),
            PlanStep("s2", "a2", "d2", "intent"),
        ])
        plan.steps[0].status = "failed"
        assert plan.failed_steps() == [plan.steps[0]]

    def test_get_step(self):
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "d1", "intent"),
        ])
        assert plan.get_step("s1") is not None
        assert plan.get_step("missing") is None


class TestTaskPlanner:
    def test_create_plan_basic(self):
        planner = TaskPlanner()
        plan = planner.create_plan("build a cave", [
            ("cave", "cave_domain"),
            ("lighting", "lighting_domain"),
        ])
        assert len(plan.steps) == 2
        assert plan.original_intent == "build a cave"

    def test_create_plan_adds_dependencies(self):
        planner = TaskPlanner()
        plan = planner.create_plan("build a cave", [
            ("cave", "cave_domain"),
            ("lighting", "lighting_domain"),
        ])
        cave_step = plan.get_step("step_00_cave")
        light_step = plan.get_step("step_01_lighting")
        assert cave_step is not None
        assert light_step is not None
        # cave must precede lighting
        assert light_step.dependencies == ["step_00_cave"]
        assert cave_step.dependencies == []

    def test_create_plan_no_deps_for_unrelated(self):
        planner = TaskPlanner()
        plan = planner.create_plan("build", [
            ("audio", "audio_domain"),
            ("ui", "ui_domain"),
        ])
        audio_step = plan.get_step("step_00_audio")
        ui_step = plan.get_step("step_01_ui")
        assert audio_step.dependencies == []
        assert ui_step.dependencies == []

    @pytest.mark.asyncio
    async def test_execute_plan_success(self):
        planner = TaskPlanner()
        orch = FakeOrchestrator()
        plan = planner.create_plan("build cave", [
            ("cave", "cave_domain"),
            ("lighting", "lighting_domain"),
        ])
        context = AgentContext()
        result = await planner.execute_plan(plan, context, orch)

        assert result.success
        assert len(orch.calls) == 2
        # cave must be called before lighting due to deps
        assert orch.calls[0][0] == "cave_domain"
        assert orch.calls[1][0] == "lighting_domain"

    @pytest.mark.asyncio
    async def test_execute_plan_parallel_independent(self):
        planner = TaskPlanner(max_parallel=3)
        orch = FakeOrchestrator()
        plan = planner.create_plan("build", [
            ("audio", "audio_domain"),
            ("ui", "ui_domain"),
            ("vfx", "vfx_domain"),
        ])
        context = AgentContext()
        result = await planner.execute_plan(plan, context, orch)

        assert result.success
        assert len(orch.calls) == 3
        # All independent, could run in parallel
        agents_called = {c[0] for c in orch.calls}
        assert agents_called == {"audio_domain", "ui_domain", "vfx_domain"}

    @pytest.mark.asyncio
    async def test_execute_plan_failure(self):
        planner = TaskPlanner()
        orch = FakeOrchestrator()
        orch.fail_step("lighting_domain")
        plan = planner.create_plan("build cave", [
            ("cave", "cave_domain"),
            ("lighting", "lighting_domain"),
        ])
        context = AgentContext()
        result = await planner.execute_plan(plan, context, orch)

        assert not result.success
        assert any("lighting_domain failed" in str(w) for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_plan_retry(self):
        planner = TaskPlanner()
        orch = FakeOrchestrator()
        orch.fail_step("cave_domain")
        plan = planner.create_plan("build cave", [
            ("cave", "cave_domain"),
        ])
        # Allow one retry
        plan.steps[0].max_retries = 1
        context = AgentContext()
        result = await planner.execute_plan(plan, context, orch)

        # First attempt fails, retry also fails (still in _should_fail)
        assert not result.success
        # Called twice: original + 1 retry
        assert orch.calls.count(("cave_domain", "build cave")) == 2

    @pytest.mark.asyncio
    async def test_execute_plan_stalled(self):
        planner = TaskPlanner()
        orch = FakeOrchestrator()
        plan = ExecutionPlan(steps=[
            PlanStep("s1", "a1", "d1", "intent", dependencies=["missing"]),
        ])
        context = AgentContext()
        result = await planner.execute_plan(plan, context, orch)

        assert not result.success
        assert "stalled" in result.error.lower()
