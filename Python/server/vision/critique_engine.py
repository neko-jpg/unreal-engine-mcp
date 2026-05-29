"""Multimodal critique engine with math-metric fusion.

The class is structured for VLM integration, but has a deterministic local
path so unit and E2E tests do not require external API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from server.vision.visual_metrics import compute_metrics_for_path


@dataclass
class VlmRubric:
    rubric_id: str
    goal: str
    criteria: List[str] = field(default_factory=list)


@dataclass
class CritiqueResult:
    rubric_id: str
    score: float
    math_driven: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    visual_metrics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rubric_id": self.rubric_id,
            "score": self.score,
            "math_driven": self.math_driven,
            "issues": list(self.issues),
            "suggestions": list(self.suggestions),
            "visual_metrics": list(self.visual_metrics),
            "semantic_score": max(0.0, min(self.score / 100.0, 1.0)),
        }


class CritiqueEngine:
    """Visual critique with objective metric overrides."""

    def __init__(self, vlm_client: Any = None) -> None:
        self.vlm_client = vlm_client

    async def critique(
        self,
        image_paths: List[str],
        rubric: VlmRubric,
        math_metrics: Mapping[str, Any],
    ) -> CritiqueResult:
        visual_metrics = [compute_metrics_for_path(path).to_dict() for path in image_paths]
        math_issues = self._math_issues(math_metrics)
        visual_issues = self._visual_issues(visual_metrics)
        issues = math_issues + visual_issues
        suggestions = self._suggestions(issues)
        visual_score = self._visual_proxy_score(visual_metrics)
        math_score = self._math_score(math_metrics)

        # VLM integration: if client provided and images available, call VLM
        vlm_score = None
        if self.vlm_client and image_paths:
            vlm_score = await self._call_vlm(image_paths, rubric, math_metrics)
            if vlm_score is not None:
                score = math_score * 0.50 + visual_score * 0.20 + vlm_score * 0.30
            else:
                score = math_score * 0.70 + visual_score * 0.30
        else:
            score = math_score * 0.70 + visual_score * 0.30

        if any(issue.get("severity") == "critical" for issue in issues):
            score = min(score, 62.0)
        return CritiqueResult(
            rubric_id=rubric.rubric_id,
            score=round(score, 2),
            math_driven=bool(math_issues),
            issues=issues,
            suggestions=suggestions,
            visual_metrics=visual_metrics,
        )

    def _math_issues(self, math_metrics: Mapping[str, Any]) -> List[Dict[str, Any]]:
        checks = [
            ("flat_surface_ratio", float(math_metrics.get("flat_surface_ratio", 0.0) or 0.0), 0.35, "max"),
            ("curvature_entropy", float(math_metrics.get("curvature_entropy", 0.0) or 0.0), 0.45, "min"),
            ("arch_score", float(math_metrics.get("arch_score", 0.0) or 0.0), 0.55, "min"),
            ("detail_density_per_m2", float(math_metrics.get("detail_density_per_m2", 0.0) or 0.0), 1.5, "min"),
        ]
        issues: List[Dict[str, Any]] = []
        for metric, value, threshold, direction in checks:
            failed = value > threshold if direction == "max" else value < threshold
            if failed:
                issues.append(
                    {
                        "type": "math",
                        "metric": metric,
                        "value": round(value, 3),
                        "threshold": threshold,
                        "severity": "critical" if metric in {"flat_surface_ratio", "curvature_entropy"} else "major",
                    }
                )
        return issues

    def _suggestions(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        metrics = {issue.get("metric") for issue in issues}
        if "flat_surface_ratio" in metrics or "curvature_entropy" in metrics:
            suggestions.extend(
                [
                    {"type": "param", "parameter": "sdf_warp_strength", "delta": "+0.25"},
                    {"type": "param", "parameter": "noise_octaves", "delta": "+2"},
                    {"type": "param", "parameter": "normal_strength", "delta": "+0.8"},
                ]
            )
        if "arch_score" in metrics:
            suggestions.extend(
                [
                    {"type": "param", "parameter": "ceiling_warp_strength", "delta": "+0.25"},
                    {"type": "agent", "agent": "pcg_domain", "intent": "add stalactites on ceiling"},
                ]
            )
        if "detail_density_per_m2" in metrics:
            suggestions.append({"type": "param", "parameter": "stalactite_density", "delta": "+0.45"})
        return suggestions

    def _math_score(self, math_metrics: Mapping[str, Any]) -> float:
        flat = float(math_metrics.get("flat_surface_ratio", 0.0) or 0.0)
        curvature = float(math_metrics.get("curvature_entropy", 0.0) or 0.0)
        arch = float(math_metrics.get("arch_score", 0.0) or 0.0)
        detail = min(float(math_metrics.get("detail_density_per_m2", 0.0) or 0.0) / 3.0, 1.0)
        return max(0.0, min((1.0 - flat) * 24.0 + curvature * 28.0 + arch * 24.0 + detail * 24.0, 100.0))

    def _visual_proxy_score(self, visual_metrics: List[Dict[str, Any]]) -> float:
        valid = [m for m in visual_metrics if not m.get("note")]
        if not valid:
            return 55.0
        contrast = sum(float(m.get("contrast", 0.0) or 0.0) for m in valid) / len(valid)
        darkness = sum(1.0 - float(m.get("luminance_mean", 0.5) or 0.5) for m in valid) / len(valid)
        cool = sum(max(0.0, float(m.get("blue_cyan_bias", 0.0) or 0.0)) for m in valid) / len(valid)
        return max(0.0, min((contrast * 0.45 + darkness * 0.40 + cool * 0.15) * 100.0, 100.0))

    def _visual_issues(self, visual_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate issues from pixel-level visual analysis."""
        valid = [m for m in visual_metrics if not m.get("note")]
        if not valid:
            return []
        issues: List[Dict[str, Any]] = []
        avg_contrast = sum(float(m.get("contrast", 0.0) or 0.0) for m in valid) / len(valid)
        avg_luminance = sum(float(m.get("luminance_mean", 0.5) or 0.5) for m in valid) / len(valid)
        avg_color_var = sum(float(m.get("color_variance", 0.1) or 0.1) for m in valid) / len(valid)
        if avg_contrast < 0.30:
            issues.append({"type": "visual", "description": "Scene is too flat, lacks depth", "metric": "contrast", "value": round(avg_contrast, 3), "severity": "major"})
        if avg_luminance > 0.80:
            issues.append({"type": "visual", "description": "Scene is overexposed", "metric": "luminance_mean", "value": round(avg_luminance, 3), "severity": "major"})
        if avg_color_var < 0.05:
            issues.append({"type": "visual", "description": "Scene lacks color variation", "metric": "color_variance", "value": round(avg_color_var, 3), "severity": "minor"})
        return issues

    async def _call_vlm(self, image_paths: List[str], rubric: VlmRubric, math_metrics: Mapping[str, Any]) -> Optional[float]:
        """Call VLM API with images and rubric. Returns score 0-100 or None on failure."""
        try:
            prompt = f"Evaluate this scene: {rubric.goal}\n"
            prompt += "Criteria:\n"
            for c in rubric.criteria:
                prompt += f"- {c}\n"
            prompt += f"\nMath metrics (objective):\n"
            for key in ("flat_surface_ratio", "curvature_entropy", "arch_score", "detail_density_per_m2"):
                val = math_metrics.get(key)
                if val is not None:
                    prompt += f"- {key}: {val}\n"
            prompt += "\nScore 0-100. Return only the number."
            response = await self.vlm_client.evaluate(image_paths, prompt)
            score = float(response)
            return max(0.0, min(score, 100.0))
        except Exception:
            return None


DEFAULT_CAVE_RUBRIC = VlmRubric(
    rubric_id="cave_shape",
    goal="Evaluate whether the scene reads as a high-quality dramatic cave.",
    criteria=[
        "cave-like tunnel/chamber silhouette",
        "non-boxy walls and arched ceiling",
        "readable depth and hero composition",
        "credible wet stone material and detail distribution",
        "dramatic contrast with fog and motivated light sources",
    ],
)
