"""VFXExpert - dust/embers Niagara components.

Python PatchExecutor path.
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import ComponentPatch


_EFFECT_TO_LEVEL = {"none": 0.0, "low": 0.3, "medium": 0.7, "high": 1.0}


class VFXExpert(BaseDomainExpert):
    domain = "vfx"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.vfx if profile else {}) or {}
        if not params:
            return []
        density_mult = float(params.get("density_multiplier", 1.0))
        patches: List[ComponentPatch] = []
        if params.get("dust"):
            patches.append(
                ComponentPatch(
                    scene_id=intent.scene_id,
                    entity_id="vfx:scene",
                    component_type="vfx",
                    name="dust",
                    properties={
                        "system_path": "/Game/MCP/VFX/NS_Dust",
                        "density": density_mult,
                    },
                    capability_id="vfx.add_niagara_component",
                    reason="Dust particles for mood",
                )
            )
        embers = params.get("embers")
        if embers and embers != "none":
            level = _EFFECT_TO_LEVEL.get(str(embers).lower(), 0.3)
            patches.append(
                ComponentPatch(
                    scene_id=intent.scene_id,
                    entity_id="vfx:scene",
                    component_type="vfx",
                    name="embers",
                    properties={
                        "system_path": "/Game/MCP/VFX/NS_Embers",
                        "level": level,
                    },
                    capability_id="vfx.add_niagara_component",
                    reason=f"Embers level={embers} for mood",
                )
            )
        return patches
