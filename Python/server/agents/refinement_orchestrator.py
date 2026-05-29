"""Generate-observe-critique-optimize loop."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent
from server.agents.refinement_compiler import RefinementCompiler
from server.observation.scene_observer import SceneObserver
from server.quality.cave_math_metrics import compute_cave_math_metrics
from server.quality.quality_gate import QualityGate
from server.quality.quality_vector import QualityVectorBuilder
from server.vision.critique_engine import DEFAULT_CAVE_RUBRIC, CritiqueEngine


class RefinementOrchestrator:
    """Runs generate -> observe -> critique -> optimize -> refine."""

    def __init__(self, agent: Optional[BaseAgent] = None) -> None:
        self.agent = agent
        self.observer = SceneObserver()
        self.critique_engine = CritiqueEngine()
        self.vector_builder = QualityVectorBuilder()
        self.quality_gate = QualityGate()
        self.compiler = RefinementCompiler()

    async def run(
        self,
        intent: str,
        context: AgentContext,
        max_iterations: int = 3,
        quality_threshold: float = 70.0,
        strategy: str = "single",
    ) -> AgentResult:
        history = []
        final_vector: Dict[str, Any] = {}
        final_gate = None
        warnings = []
        for iteration in range(max_iterations):
            generation = await self._generate_or_refine(intent, context, iteration)
            observation = self.observer.observe(
                scene_id=context.scene_id,
                scene_type=context.metadata.get("scene_type", "cave"),
                intent=intent,
                iteration=iteration,
                context=context.metadata,
            )
            math_scores = compute_cave_math_metrics(observation)
            critique = await self.critique_engine.critique([], DEFAULT_CAVE_RUBRIC, math_scores)
            final_vector = self.vector_builder.build(math_scores, critique.to_dict(), observation)
            final_gate = self.quality_gate.check(final_vector, observation)
            history.append(final_vector)
            context.metadata["quality_history"] = history
            if final_vector["overall"] >= quality_threshold and final_gate.passed:
                return AgentResult(
                    success=True,
                    data={
                        "final_score": final_vector["overall"],
                        "iterations": iteration + 1,
                        "quality_vector": final_vector,
                        "gate_result": final_gate.to_dict(),
                        "generation": generation.to_dict() if hasattr(generation, "to_dict") else generation,
                    },
                )
            refinement_plan = self.compiler.compile(final_vector, observation, final_gate, critique.to_dict())
            context.metadata["refinement_plan"] = refinement_plan
            warnings.append(f"iteration {iteration + 1}: score={final_vector['overall']}, blockers={final_gate.blockers}")

        return AgentResult(
            success=True,
            data={
                "final_score": final_vector.get("overall", 0.0),
                "iterations": max_iterations,
                "quality_vector": final_vector,
                "gate_result": final_gate.to_dict() if final_gate else {},
                "quality_history": history,
            },
            warnings=[f"Max iterations reached. Final score: {final_vector.get('overall', 0.0)}"] + warnings,
        )

    async def _generate_or_refine(self, intent: str, context: AgentContext, iteration: int) -> AgentResult:
        if self.agent is None:
            return AgentResult(success=True, data={"mode": "observe_only", "iteration": iteration})

        # Build params from refinement plan if available
        params: Dict[str, Any] = {
            "mood": "creepy",
            "resolution": 48,
            "force_geometry": iteration == 0,
        }
        refinement_plan = context.metadata.get("refinement_plan", [])
        for action in refinement_plan:
            if isinstance(action, dict):
                for p in action.get("params", action.get("parameter_updates", [])):
                    if isinstance(p, dict):
                        params.update(p)
                    elif isinstance(action.get("params"), dict):
                        params.update(action["params"])
                        break

        result = await self.agent.call_tool_async(
            "scene_cave_generate_or_refine",
            scene_id=context.scene_id,
            mood=params.get("mood", "creepy"),
            target=context.target or "cave",
            max_refine_iterations=1,
            cave_score_threshold=0.75,
            force_geometry=params.get("force_geometry", iteration == 0),
            resolution=int(params.get("resolution", 48)),
            include_preview=False,
        )
        return AgentResult(success=result.get("success", True), data={"raw_result": result})
