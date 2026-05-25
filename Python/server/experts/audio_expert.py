"""AudioExpert - ambient sounds and audio components.

Python PatchExecutor path.
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import ComponentPatch


class AudioExpert(BaseDomainExpert):
    domain = "audio"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.audio if profile else {}) or {}
        ambient = params.get("ambient_sounds") or []
        if not ambient:
            return []
        volume = float(params.get("volume", 0.5))
        attenuation = float(params.get("attenuation_radius", 500.0))

        patches: List[ComponentPatch] = []
        for name in ambient:
            properties = {
                "sound_name": name,
                "volume": volume,
                "attenuation_radius": attenuation,
            }
            patches.append(
                ComponentPatch(
                    scene_id=intent.scene_id,
                    entity_id="audio:scene",
                    component_type="audio",
                    name=f"ambient_{name}",
                    properties=properties,
                    capability_id="audio.spawn_ambient",
                    reason=f"Ambient {name} for mood {intent.mood or 'default'}",
                )
            )
        return patches
