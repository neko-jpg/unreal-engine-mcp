"""ExpertRouter - picks which experts apply for a given intent."""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.atmosphere_expert import AtmosphereExpert
from server.experts.audio_expert import AudioExpert
from server.experts.base_expert import BaseDomainExpert
from server.experts.cave_expert import CaveExpert
from server.experts.lighting_expert import LightingExpert
from server.experts.material_expert import MaterialExpert
from server.experts.mood_profiles import MoodProfile, load_profile
from server.experts.postprocess_expert import PostProcessExpert
from server.experts.vfx_expert import VFXExpert
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack


class ExpertRouter:
    def __init__(self, experts: Optional[List[BaseDomainExpert]] = None) -> None:
        self.experts: List[BaseDomainExpert] = experts or [
            CaveExpert(),       # Highest priority: cave geometry orchestration
            LightingExpert(),
            MaterialExpert(),
            AtmosphereExpert(),
            AudioExpert(),
            VFXExpert(),
            PostProcessExpert(),
        ]

    def propose_all(
        self,
        intent: Intent,
        context: SceneContextPack,
    ) -> List[Any]:
        profile: Optional[MoodProfile] = None
        profile_name = intent.style_profile or intent.mood
        if profile_name:
            profile = load_profile(profile_name)
        out: List[Any] = []
        for expert in self.experts:
            if expert.applies_to(intent):
                out.extend(expert.propose(intent, context, profile))
        return out


def default_router() -> ExpertRouter:
    return ExpertRouter()
