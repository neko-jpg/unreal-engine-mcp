"""PostProcessExpert - produces DirectCommandPatch entries for post-process look.

Consumes the post_process section of MoodProfile to apply bloom, exposure,
saturation, contrast, and other post-process settings.
"""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import DirectCommandPatch


class PostProcessExpert(BaseDomainExpert):
    domain = "post_process"

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        params = (profile.post_process if profile else {}) or {}
        if not params:
            return []

        patches: List[DirectCommandPatch] = []
        properties: dict[str, Any] = {}

        if "bloom_intensity" in params:
            properties["bloom_intensity"] = float(params["bloom_intensity"])
        if "saturation" in params:
            properties["saturation"] = float(params["saturation"])
        if "contrast" in params:
            properties["contrast"] = float(params["contrast"])
        if "exposure_compensation" in params:
            properties["exposure_compensation"] = float(params["exposure_compensation"])
        if "vignette_intensity" in params:
            properties["vignette_intensity"] = float(params["vignette_intensity"])
        if "white_balance_temperature" in params:
            properties["white_balance_temperature"] = float(params["white_balance_temperature"])
        if "auto_exposure_bias" in params:
            properties["auto_exposure_bias"] = float(params["auto_exposure_bias"])

        if properties:
            volume_name = "MCP_PostProcess_Primary"
            patches.append(
                DirectCommandPatch(
                    capability_id="postprocess.spawn",
                    command="spawn_post_process_volume",
                    params={
                        "name": volume_name,
                        "infinite_extent": True,
                    },
                    reason="Ensure a global post-process volume exists",
                )
            )
            patches.append(
                DirectCommandPatch(
                    capability_id="postprocess.apply",
                    command="set_post_process_volume",
                    params={"volume_name": volume_name, **properties},
                    reason=f"Apply post-process mood {intent.mood or 'default'}",
                )
            )

        return patches
