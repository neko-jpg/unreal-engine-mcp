"""Quality vector construction for scene optimization."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _score(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        value = float(value)
        return _clamp(value / 100.0 if value > 1.0 else value)
    return default


class QualityVectorBuilder:
    """Build a multidimensional quality vector from math and VLM scores."""

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "semantic_score": 0.18,
        "shape_score": 0.18,
        "composition_score": 0.12,
        "detail_score": 0.14,
        "material_score": 0.12,
        "lighting_score": 0.10,
        "topology_score": 0.08,
        "technical_score": 0.05,
        "performance_score": 0.03,
    }

    def build(
        self,
        math_metrics: Mapping[str, Any],
        vlm_scores: Optional[Mapping[str, Any]] = None,
        observation: Optional[Any] = None,
        weights: Optional[Mapping[str, float]] = None,
    ) -> Dict[str, Any]:
        vlm_scores = vlm_scores or {}
        weights = dict(weights or self.DEFAULT_WEIGHTS)
        metrics = dict(math_metrics)

        flat = _score(metrics.get("flat_surface_ratio"))
        curvature = _score(metrics.get("curvature_entropy"))
        arch = _score(metrics.get("arch_score"))
        shape_score = _clamp(curvature * 0.42 + arch * 0.38 + (1.0 - flat) * 0.20)

        detail_density = _score(float(metrics.get("detail_density_per_m2", 0.0) or 0.0) / 3.0)
        detail_distribution = _score(metrics.get("detail_distribution_score"))
        stalactites = _score(float(metrics.get("stalactite_count", 0.0) or 0.0) / 24.0)
        detail_score = _clamp(detail_density * 0.45 + detail_distribution * 0.35 + stalactites * 0.20)

        material_score = self._material_score(metrics, observation)
        lighting_score = _clamp(
            _score(metrics.get("lighting_contrast_score")) * 0.60
            + _score(metrics.get("image_contrast")) * 0.30
            + min(float(metrics.get("fog_density", 0.0) or 0.0) / 0.08, 1.0) * 0.10
        )
        topology_score = _score(metrics.get("topology_score", metrics.get("depth_score", 0.0)))
        technical_score = self._technical_score(metrics)
        performance_score = self._performance_score(metrics)

        semantic_score = _score(vlm_scores.get("semantic_score", vlm_scores.get("cave_likeness")), default=shape_score * 0.65 + detail_score * 0.35)
        composition_score = _score(vlm_scores.get("composition_score"), default=_clamp(_score(metrics.get("screenshot_count")) + topology_score * 0.55))

        penalties = self._penalties(metrics)
        vector: Dict[str, Any] = {
            "semantic_score": round(semantic_score, 3),
            "shape_score": round(shape_score, 3),
            "composition_score": round(composition_score, 3),
            "detail_score": round(detail_score, 3),
            "material_score": round(material_score, 3),
            "lighting_score": round(lighting_score, 3),
            "topology_score": round(topology_score, 3),
            "technical_score": round(technical_score, 3),
            "performance_score": round(performance_score, 3),
            "penalties": round(penalties, 3),
            "math_weight": 0.70,
            "vlm_weight": 0.30,
        }
        weighted = sum(vector[key] * float(weights.get(key, 0.0)) for key in self.DEFAULT_WEIGHTS)
        vector["overall"] = round(max(0.0, weighted - penalties) * 100.0, 2)
        return vector

    def _material_score(self, metrics: Mapping[str, Any], observation: Optional[Any]) -> float:
        material = getattr(observation, "materials", None) if observation is not None else None
        material_dict = material.to_dict() if hasattr(material, "to_dict") else {}
        source = {**material_dict, **dict(metrics)}
        default_count = int(source.get("default_material_actor_count", 0) or 0)
        return _clamp(
            (1.0 if default_count <= 0 else 0.25)
            * 0.35
            + _score(source.get("normal_map_coverage"), 0.35) * 0.25
            + _score(source.get("roughness_mean"), 0.75) * 0.15
            + min(float(source.get("wetness_coverage", 0.0) or 0.0) / 0.25, 1.0) * 0.15
            + min(float(source.get("moss_coverage", 0.0) or 0.0) / 0.12, 1.0) * 0.10
        )

    def _technical_score(self, metrics: Mapping[str, Any]) -> float:
        triangles = float(metrics.get("triangle_count", 0.0) or 0.0)
        if triangles <= 0:
            return 0.0
        min_score = min(triangles / 30000.0, 1.0)
        budget_penalty = max(0.0, (triangles - 350000.0) / 350000.0)
        return _clamp(min_score - budget_penalty * 0.25)

    def _performance_score(self, metrics: Mapping[str, Any]) -> float:
        fps = metrics.get("fps")
        memory_mb = metrics.get("memory_mb")
        if isinstance(fps, (int, float)):
            return _clamp(float(fps) / 60.0)
        if isinstance(memory_mb, (int, float)):
            return _clamp(1.0 - max(0.0, float(memory_mb) - 2048.0) / 4096.0)
        triangles = float(metrics.get("triangle_count", 0.0) or 0.0)
        return _clamp(0.82 - max(0.0, triangles - 160000.0) / 600000.0)

    def _penalties(self, metrics: Mapping[str, Any]) -> float:
        penalty = 0.0
        if not metrics.get("main_mesh_exists", True):
            penalty += 0.25
        if _score(metrics.get("flat_surface_ratio")) > 0.35:
            penalty += 0.08
        if int(metrics.get("floating_object_count", 0) or 0) > 0:
            penalty += 0.04
        if int(metrics.get("default_material_actor_count", 0) or 0) > 0:
            penalty += 0.04
        if _score(metrics.get("overexposed_pixel_ratio")) > 0.05:
            penalty += 0.03
        return _clamp(penalty, 0.0, 0.5)
