"""LightingExpert - produces ComponentPatch entries for the 'light' domain.

Hybrid path: lights are component_apply (Rust component_applier handles them).
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack, SceneObjectBrief
from server.planning.design_patch import ComponentPatch


class LightingExpert(BaseDomainExpert):
    domain = "lighting"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.lighting if profile else {}) or {}
        patches: List[ComponentPatch] = []

        # Target the union of all "light" kind objects and any existing
        # scene_component:light entries.
        light_objects: List[SceneObjectBrief] = []
        for kind, items in context.objects_by_kind.items():
            if kind.lower() in {"light", "pointlight", "spotlight", "rectlight", "directionallight"}:
                light_objects.extend(items)

        if not light_objects:
            # If no lights present yet, emit a single creepy ambient marker
            # so the planner has something to apply downstream.
            return []

        intensity_mult = float(params.get("intensity_multiplier", 1.0))
        color_bias = params.get("color_bias")
        temperature = params.get("temperature_kelvin")
        shadow_enabled = params.get("shadow_enabled")
        vol_scattering = params.get("volumetric_scattering")

        for obj in light_objects:
            actor_name = obj.name or obj.mcp_id
            properties = {
                "actor_mcp_id": obj.mcp_id,
                "actor_name": actor_name,
                "intensity_multiplier": intensity_mult,
                "intensity": max(150.0, 5000.0 * intensity_mult),
            }
            if color_bias:
                properties["color"] = list(color_bias)
            if temperature is not None:
                properties["temperature_kelvin"] = float(temperature)
            if shadow_enabled is not None:
                properties["shadow_enabled"] = bool(shadow_enabled)
            if vol_scattering is not None:
                properties["volumetric_scattering"] = float(vol_scattering)

            patches.append(
                ComponentPatch(
                    scene_id=intent.scene_id,
                    entity_id=f"actor:{obj.mcp_id}",
                    component_type="light",
                    name="primary",
                    properties=properties,
                    capability_id="light.set_intensity",
                    reason=f"Apply mood {intent.mood or 'default'} to {obj.mcp_id}",
                )
            )
        return patches
