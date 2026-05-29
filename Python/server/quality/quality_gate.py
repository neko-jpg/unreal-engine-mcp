"""Quality gates for cave scene acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


CAVE_QUALITY_GATES: Dict[str, Any] = {
    "main_mesh_exists": True,
    "triangle_count_min": 30000,
    "flat_surface_ratio_max": 0.35,
    "curvature_entropy_min": 0.45,
    "arch_score_min": 0.55,
    "detail_density_per_m2_min": 1.5,
    "default_material_actor_count_max": 0,
    "stalactite_count_min": 12,
    "rock_debris_count_min": 25,
    "image_contrast_min": 0.45,
    "composition_score_min": 0.60,
    "vlm_cave_likeness_min": 0.65,
}

ROOM_QUALITY_GATES: Dict[str, Any] = {
    "main_mesh_exists": True,
    "triangle_count_min": 10000,
    "walkable_area_ratio_min": 0.40,
    "light_count_min": 2,
    "default_material_actor_count_max": 0,
    "image_contrast_min": 0.30,
    "composition_score_min": 0.55,
}

FOREST_QUALITY_GATES: Dict[str, Any] = {
    "tree_count_min": 15,
    "canopy_coverage_min": 0.30,
    "ground_cover_density_min": 0.50,
    "path_walkable_min": True,
    "default_material_actor_count_max": 0,
    "image_contrast_min": 0.35,
    "composition_score_min": 0.50,
}

CITY_QUALITY_GATES: Dict[str, Any] = {
    "building_count_min": 5,
    "road_connectivity_min": 0.60,
    "sidewalk_coverage_min": 0.25,
    "default_material_actor_count_max": 0,
    "image_contrast_min": 0.30,
    "composition_score_min": 0.50,
}


@dataclass
class GateResult:
    passed: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    values: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "values": dict(self.values),
        }


class QualityGate:
    """Check quality vectors and observation metrics against hard gates."""

    def __init__(self, gates: Optional[Mapping[str, Any]] = None) -> None:
        self.gates = dict(gates or CAVE_QUALITY_GATES)

    # Soft gates (warnings only, never block)
    _SOFT_GATES = frozenset({
        "image_contrast_min", "composition_score_min", "vlm_cave_likeness_min",
    })

    def check(self, quality_vector: Mapping[str, Any], observation_or_metrics: Any) -> GateResult:
        metrics = self._metrics(observation_or_metrics)
        actor_counts = self._actor_counts(observation_or_metrics)
        # Merge actor counts into metrics for uniform lookup
        for k, v in actor_counts.items():
            metrics.setdefault(k, v)
        # Also merge quality_vector scores for *_score_min gates
        for k, v in quality_vector.items():
            if k.endswith("_score"):
                metrics.setdefault(k, v)
        # Merge semantic_score as vlm_cave_likeness alias
        metrics.setdefault("vlm_cave_likeness", quality_vector.get("semantic_score", 0.0))

        values: Dict[str, Any] = {}
        blockers: list[str] = []
        warnings: list[str] = []

        for gate_name, threshold in self.gates.items():
            # Determine the metric key: strip _min/_max suffix
            if gate_name.endswith("_min"):
                metric_key = gate_name[:-4]
                is_min_gate = True
            elif gate_name.endswith("_max"):
                metric_key = gate_name[:-4]
                is_min_gate = False
            elif gate_name == "main_mesh_exists":
                metric_key = "main_mesh_exists"
                is_min_gate = None  # boolean check
            else:
                continue

            value = metrics.get(metric_key, 0)
            hard = gate_name not in self._SOFT_GATES

            if is_min_gate is None:
                # Boolean equality check
                ok = bool(value) is bool(threshold)
            elif is_min_gate:
                ok = float(value or 0) >= float(threshold)
            else:
                ok = float(value or 0) <= float(threshold)

            values[metric_key] = value
            if not ok:
                (blockers if hard else warnings).append(metric_key)

        return GateResult(passed=not blockers, blockers=blockers, warnings=warnings, values=values)

    def _metrics(self, observation_or_metrics: Any) -> Dict[str, Any]:
        if hasattr(observation_or_metrics, "metrics"):
            metrics = dict(getattr(observation_or_metrics, "metrics", {}) or {})
            meshes = getattr(observation_or_metrics, "meshes", {}) or {}
            if isinstance(meshes, Mapping):
                for value in meshes.values():
                    if hasattr(value, "to_dict"):
                        metrics.update(value.to_dict())
                    elif isinstance(value, Mapping):
                        metrics.update(value)
                    break
            for attr in ("materials", "lights", "pcg"):
                value = getattr(observation_or_metrics, attr, None)
                if hasattr(value, "to_dict"):
                    metrics.update(value.to_dict())
                elif isinstance(value, Mapping):
                    metrics.update(value)
            return metrics
        return dict(observation_or_metrics or {})

    def _actor_counts(self, observation_or_metrics: Any) -> Dict[str, Any]:
        if hasattr(observation_or_metrics, "actors"):
            actors = getattr(observation_or_metrics, "actors", {}) or {}
            if isinstance(actors, Mapping):
                counts = actors.get("actor_count_by_tag", {})
                return dict(counts) if isinstance(counts, Mapping) else {}
        if isinstance(observation_or_metrics, Mapping):
            counts = observation_or_metrics.get("actor_count_by_tag", {})
            return dict(counts) if isinstance(counts, Mapping) else {}
        return {}
