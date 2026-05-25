"""AtmosphereExpert - emits ComponentPatch(atmosphere) entries.

Python PatchExecutor path: fog / sky / volumetric.
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import ComponentPatch


class AtmosphereExpert(BaseDomainExpert):
    domain = "atmosphere"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.atmosphere if profile else {}) or {}
        if not params:
            return []

        # The atmosphere is global per scene; we model it as a single component
        # on a singleton "atmosphere:scene" entity.
        fog_density_scale = params.get("fog_density_scale")
        fog_color = params.get("fog_color")
        volumetric_fog = params.get("volumetric_fog")
        sky_brightness = params.get("sky_brightness")
        fog_actor_name = "Cave_Fog"
        for kind, items in context.objects_by_kind.items():
            if kind.lower() in {"fog", "atmosphere"} and items:
                fog_actor_name = items[0].name or items[0].mcp_id
                break

        properties = {
            "actor_name": fog_actor_name,
            **({"fog_density": max(0.0, min(0.15, 0.04 * float(fog_density_scale)))} if fog_density_scale is not None else {}),
            **({"light_inscattering_color": list(fog_color)} if fog_color is not None else {}),
            **({"volumetric_fog_enabled": bool(volumetric_fog)} if volumetric_fog is not None else {}),
            **({"sky_brightness": float(sky_brightness)} if sky_brightness is not None else {}),
        }
        if not properties:
            return []
        return [
            ComponentPatch(
                scene_id=intent.scene_id,
                entity_id="atmosphere:scene",
                component_type="atmosphere",
                name="primary",
                properties=properties,
                capability_id="atmosphere.set_height_fog",
                reason=f"Atmosphere preset for mood {intent.mood or 'default'}",
            )
        ]
