"""A/B comparison for scene observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from server.quality.cave_math_metrics import compute_cave_math_metrics
from server.quality.quality_vector import QualityVectorBuilder
from server.vision.critique_engine import DEFAULT_CAVE_RUBRIC, CritiqueEngine, VlmRubric


@dataclass
class ComparisonResult:
    winner: str
    reasoning: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"winner": self.winner, "reasoning": dict(self.reasoning)}


class ABComparison:
    async def compare(
        self,
        variant_a: Any,
        variant_b: Any,
        rubric: VlmRubric = DEFAULT_CAVE_RUBRIC,
    ) -> ComparisonResult:
        math_a = compute_cave_math_metrics(variant_a)
        math_b = compute_cave_math_metrics(variant_b)
        vector_builder = QualityVectorBuilder()
        q_a = vector_builder.build(math_a, {}, variant_a)
        q_b = vector_builder.build(math_b, {}, variant_b)
        math_winner = "a" if q_a["overall"] >= q_b["overall"] else "b"

        engine = CritiqueEngine()
        vlm_a = await engine.critique([], rubric, math_a)
        vlm_b = await engine.critique([], rubric, math_b)
        vlm_winner = "a" if vlm_a.score >= vlm_b.score else "b"
        weighted_a = q_a["overall"] * 0.7 + vlm_a.score * 0.3
        weighted_b = q_b["overall"] * 0.7 + vlm_b.score * 0.3
        winner = "a" if weighted_a >= weighted_b else "b"
        return ComparisonResult(
            winner=winner,
            reasoning={
                "math_winner": math_winner,
                "vlm_winner": vlm_winner,
                "weighted_a": round(weighted_a, 2),
                "weighted_b": round(weighted_b, 2),
                "quality_a": q_a,
                "quality_b": q_b,
            },
        )
