"""CaveExpert - routes cave intents into the cave orchestration pipeline."""

from __future__ import annotations

from typing import Any, List, Optional

from server.experts.base_expert import BaseDomainExpert
from server.experts.mood_profiles import MoodProfile
from server.intent.intent_types import Intent
from server.intent.scene_context import SceneContextPack
from server.planning.design_patch import DirectCommandPatch


class CaveExpert(BaseDomainExpert):
    domain = "cave"
    keywords = (
        "cave",
        "cavern",
        "dungeon",
        "洞窟",
        "洞穴",
        "鍾乳洞",
        "ダンジョン",
    )

    def applies_to(self, intent: Intent) -> bool:
        if "cave" in intent.domains:
            return True
        text = intent.raw_text.lower()
        return any(keyword in text for keyword in self.keywords)

    def propose(
        self,
        intent: Intent,
        context: SceneContextPack,
        profile: Optional[MoodProfile],
    ) -> List[Any]:
        mood = intent.mood or intent.style_profile or "creepy"
        target = "cave"
        if intent.target_selector:
            target = intent.target_selector.get("text") or target

        return [
            DirectCommandPatch(
                capability_id="cave.audit",
                command="scene_cave_audit",
                params={"scene_id": intent.scene_id, "target": target},
                reason="Audit scene structure as cave geometry",
            ),
            DirectCommandPatch(
                capability_id="cave.generate_or_refine",
                command="scene_cave_generate_or_refine",
                params={
                    "scene_id": intent.scene_id,
                    "mood": mood,
                    "target": target,
                    "max_refine_iterations": 3,
                    "cave_score_threshold": 0.75,
                    "include_preview": False,
                },
                reason=f"Generate/refine cave with mood '{mood}'",
            ),
            DirectCommandPatch(
                capability_id="cave.validate",
                command="scene_validate_cave",
                params={"scene_id": intent.scene_id, "target": target},
                reason="Validate cave navigation and collision",
            ),
        ]
