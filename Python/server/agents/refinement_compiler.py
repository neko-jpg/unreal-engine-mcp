"""Compile critique evidence into parameter updates and agent actions."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


CRITIQUE_TO_PARAM_MAP: Dict[str, Dict[str, Any]] = {
    "walls_too_smooth": {
        "evidence": {"flat_surface_ratio": "> 0.35", "curvature_entropy": "< 0.45"},
        "parameter_updates": {
            "sdf_warp_strength": "+0.25",
            "noise_octaves": "+2",
            "normal_strength": "+0.8",
            "detail_density_wall": "+0.4",
        },
    },
    "ceiling_too_flat": {
        "evidence": {"arch_score": "< 0.55", "stalactite_count": "< 12"},
        "parameter_updates": {
            "ceiling_warp_strength": "+0.25",
            "ceiling_noise_octaves": "+2",
            "stalactite_density": "+0.45",
            "stalactite_min_length": 120,
            "stalactite_max_length": 420,
        },
    },
    "too_bright": {
        "evidence": {"image_contrast": "< 0.45", "underexposed_pixel_ratio": "< 0.15"},
        "parameter_updates": {
            "main_light_intensity": "-0.30",
            "fog_density": "+0.02",
            "postprocess_exposure": "-0.5",
        },
    },
    "detail_too_sparse": {
        "evidence": {"detail_density_per_m2": "< 1.5"},
        "parameter_updates": {
            "detail_density_multiplier": "+0.5",
            "stalactite_density": "+0.3",
            "rock_debris_density": "+0.4",
        },
    },
}


class RefinementCompiler:
    """Build evidence-backed refinement plans."""

    def compile(
        self,
        quality_vector: Mapping[str, Any],
        observation: Any,
        gate_result: Optional[Any] = None,
        critique: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        metrics = dict(getattr(observation, "metrics", {}) or {})
        actors = getattr(observation, "actors", {}) or {}
        counts = actors.get("actor_count_by_tag", {}) if isinstance(actors, Mapping) else {}
        metrics.setdefault("stalactite_count", counts.get("stalactite", 0))
        metrics.setdefault("rock_debris_count", counts.get("rock_debris", 0))
        blockers = set(getattr(gate_result, "blockers", []) or [])
        if isinstance(gate_result, Mapping):
            blockers = set(gate_result.get("blockers", []) or [])
        plans: List[Dict[str, Any]] = []

        if metrics.get("flat_surface_ratio", 0.0) > 0.35 or metrics.get("curvature_entropy", 1.0) < 0.45 or "flat_surface_ratio" in blockers:
            plans.append(self._plan("walls_too_smooth", "walls are too smooth or box-like", metrics, [
                {
                    "agent": "cave_domain",
                    "operation": "increase_sdf_wall_warp",
                    "params": CRITIQUE_TO_PARAM_MAP["walls_too_smooth"]["parameter_updates"],
                }
            ]))
        if metrics.get("arch_score", 1.0) < 0.55 or metrics.get("stalactite_count", 0) < 12 or "arch_score" in blockers:
            plans.append(self._plan("ceiling_too_flat", "ceiling is too flat and has insufficient stalactites", metrics, [
                {
                    "agent": "cave_domain",
                    "operation": "increase_sdf_ceiling_warp",
                    "params": {
                        "ceiling_warp_strength": "+0.25",
                        "ceiling_noise_octaves": "+2",
                    },
                },
                {
                    "agent": "pcg_domain",
                    "operation": "spawn_ceiling_stalactites",
                    "params": {
                        "density": "+0.45",
                        "min_length": 120,
                        "max_length": 420,
                    },
                },
            ]))
        if metrics.get("image_contrast", 1.0) < 0.45 or metrics.get("underexposed_pixel_ratio", 0.2) < 0.15:
            plans.append(self._plan("too_bright", "lighting lacks dramatic cave contrast", metrics, [
                {
                    "agent": "lighting_domain",
                    "operation": "increase_volumetric_contrast",
                    "params": CRITIQUE_TO_PARAM_MAP["too_bright"]["parameter_updates"],
                }
            ]))
        if quality_vector.get("material_score", 1.0) < 0.62 or metrics.get("default_material_actor_count", 0) > 0:
            plans.append(
                {
                    "issue": "materials are too default or lack wet stone layering",
                    "evidence": {
                        "material_score": quality_vector.get("material_score"),
                        "default_material_actor_count": metrics.get("default_material_actor_count"),
                    },
                    "actions": [
                        {
                            "agent": "material_domain",
                            "operation": "apply_wet_fbm_stone_material",
                            "params": {
                                "roughness": 0.86,
                                "normal_strength": "+1.0",
                                "wetness_coverage": "+0.18",
                                "moss_coverage": "+0.10",
                            },
                        }
                    ],
                }
            )
        if metrics.get("detail_density_per_m2", 0.0) < 1.5:
            plans.append(self._plan("detail_too_sparse", "detail objects are too sparse", metrics, [
                {
                    "agent": "pcg_domain",
                    "operation": "increase_detail_density",
                    "params": CRITIQUE_TO_PARAM_MAP["detail_too_sparse"]["parameter_updates"],
                }
            ]))
        if critique and critique.get("suggestions"):
            for suggestion in critique.get("suggestions", []):
                if isinstance(suggestion, Mapping):
                    actions = _vlm_suggestion_to_actions(suggestion)
                    plans.append({"issue": "vlm_or_math_suggestion", "evidence": dict(suggestion), "actions": actions})
        return plans

    def _plan(self, issue_id: str, issue: str, metrics: Mapping[str, Any], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        spec = CRITIQUE_TO_PARAM_MAP[issue_id]
        evidence = {}
        for metric in spec["evidence"]:
            if metric in metrics:
                evidence[metric] = metrics.get(metric)
        return {
            "issue": issue,
            "evidence": evidence,
            "actions": actions,
        }


def _vlm_suggestion_to_actions(suggestion: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Map a VLM/math suggestion to actionable agent operations."""
    s_type = suggestion.get("type", "")
    if s_type == "param":
        param = suggestion.get("parameter", "")
        delta = suggestion.get("delta", "")
        if "warp" in param or "noise" in param or "roughness" in param:
            return [{"agent": "cave_domain", "operation": "adjust_sdf_params", "params": {param: delta}}]
        if "light" in param or "fog" in param or "exposure" in param:
            return [{"agent": "lighting_domain", "operation": "adjust_lighting_params", "params": {param: delta}}]
        if "density" in param or "stalactite" in param or "debris" in param:
            return [{"agent": "pcg_domain", "operation": "adjust_pcg_params", "params": {param: delta}}]
        if "material" in param or "roughness" in param or "wetness" in param or "moss" in param:
            return [{"agent": "material_domain", "operation": "adjust_material_params", "params": {param: delta}}]
        return [{"agent": "cave_domain", "operation": "adjust_params", "params": {param: delta}}]
    if s_type == "agent":
        agent = suggestion.get("agent", "cave_domain")
        intent = suggestion.get("intent", "")
        return [{"agent": agent, "operation": "execute_intent", "params": {"intent": intent}}]
    return []
