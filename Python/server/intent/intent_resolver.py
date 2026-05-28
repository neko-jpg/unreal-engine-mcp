"""IntentResolver - rule-first, optional LLM slot filling.

Turns a free-text intent like "make this cave creepy" into a structured Intent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from server.intent.intent_types import Intent


# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

# Action verbs => Intent.action
_ACTION_KEYWORDS = [
    ("restore",  ["restore", "revert", "rollback", "roll back", "undo"]),
    ("describe", ["describe", "explain", "summarize", "what is", "show"]),
    ("compare",  ["compare", "diff"]),
    ("refine",   ["refine", "improve", "tweak"]),
    ("create",   ["create", "make new", "spawn", "build"]),
    ("modify",   ["make", "change", "set", "modify", "adjust", "tune", "add", "more", "less", "dim", "brighter", "darker", "denser", "increase", "decrease"]),
]

# Domain hints
_DOMAIN_KEYWORDS = {
    "lighting": ["light", "torch", "lamp", "bright", "dark", "shadow", "明る", "暗", "灯", "光"],
    "material": ["material", "stone", "metal", "wood", "wet", "rough", "shiny", "color"],
    "atmosphere": ["fog", "mist", "haze", "sky", "atmosphere", "weather", "clouds"],
    "audio": ["sound", "audio", "drip", "wind", "music", "ambient"],
    "vfx": ["dust", "smoke", "embers", "particle", "vfx", "niagara"],
    "post_process": ["bloom", "exposure", "tonemap", "saturation", "post"],
    "camera": ["camera", "view", "framing"],
    "cave": ["cave", "cavern", "洞窟", "洞穴", "鍾乳洞", "ダンジョン", "dungeon"],
    "architecture": ["house", "building", "castle", "mansion", "tower", "bridge", "arch", "wall", "pyramid", "maze", "town", "aqueduct", "家", "建物", "城", "塔"],
    "procedural": ["procedural", "sdf", "wfc", "generate terrain", "生成"],
    "mesh_editing": ["remesh", "collision", "nanite", "uv unwrap", "voxel"],
    "navigation": ["navmesh", "walkable", "pathfinding", "歩ける"],
    "validation": ["validate", "check", "audit", "検証"],
}

# Mood markers (used to fill Intent.mood)
_MOOD_KEYWORDS = {
    "creepy":   ["creepy", "creepier", "scary", "haunted", "eerie", "spooky", "horror", "不気味", "怖い", "怖く", "ホラー", "薄気味悪い", "怪しい"],
    "heroic":   ["heroic", "epic", "majestic", "triumphant"],
    "moonlit":  ["moonlit", "moonlight", "lunar", "night"],
    "cinematic_warm": ["cinematic", "warm cinematic", "filmic", "golden hour"],
    "osaka_castle": ["osaka", "japanese castle", "samurai"],
    "calm": ["calm", "serene", "peaceful"],
    "intense": ["intense", "dramatic", "battle"],
}

# Restore detection
_RESTORE_PATTERN = re.compile(r"\b(?:restore|revert|rollback|undo)\b\s+(?:to\s+)?(?:snapshot\s+)?[\"']?([\w\-]+)?", re.IGNORECASE)

# Risk hint guesses (used as a soft signal; SafetyChecker re-evaluates)
_DESTRUCTIVE = ["delete", "remove", "wipe", "clear all"]


@dataclass
class IntentResolution:
    intent: Intent
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


def _infer_action(text_lower: str) -> str:
    # special case: "add an actor"/"add a ..." => create
    if re.search(r"\badd\s+(?:an|a|new)\s+", text_lower):
        return "create"
    for action, keys in _ACTION_KEYWORDS:
        for k in keys:
            if k in text_lower:
                return action
    return "modify"


def _infer_domains(text_lower: str) -> List[str]:
    domains: List[str] = []
    for domain, keys in _DOMAIN_KEYWORDS.items():
        if any(k in text_lower for k in keys):
            domains.append(domain)
    return domains


def _append_missing(domains: List[str], additions: List[str]) -> None:
    for domain in additions:
        if domain not in domains:
            domains.append(domain)


def _infer_mood(text_lower: str) -> Optional[str]:
    for mood, keys in _MOOD_KEYWORDS.items():
        if any(k in text_lower for k in keys):
            return mood
    return None


def _infer_risk(text_lower: str) -> Optional[str]:
    if any(k in text_lower for k in _DESTRUCTIVE):
        return "destructive"
    return None


class IntentResolver:
    """Rule-based + optional LLM slot filling."""

    def __init__(self, llm=None) -> None:
        # The LLM callable is optional; not used in MVP rule-only mode.
        self._llm = llm

    def resolve(
        self,
        raw_text: str,
        *,
        scene_id: str = "main",
        target: Optional[str] = None,
        style_profile: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> IntentResolution:
        text_lower = raw_text.lower().strip()
        warnings: List[str] = []

        action = _infer_action(text_lower)
        domains = _infer_domains(text_lower)
        mood = _infer_mood(text_lower)
        risk_hint = _infer_risk(text_lower)

        if action == "restore":
            domains = []  # restore is structural
            mood = None

        # If a style profile is explicitly passed, it wins.
        effective_mood = style_profile or mood

        # If we found no domain at all but action is modify, default to a wide set.
        if action == "modify" and not domains and effective_mood:
            domains = ["lighting", "material", "atmosphere", "audio", "vfx"]
            warnings.append("domains inferred from mood")

        # Cave mood edits need both orchestration and the existing mood passes.
        if action in {"modify", "refine", "create"} and "cave" in domains:
            _append_missing(
                domains,
                [
                    "lighting",
                    "material",
                    "atmosphere",
                    "audio",
                    "vfx",
                    "post_process",
                ],
            )

        target_selector: Optional[Dict[str, Any]] = None
        if target:
            target_selector = {"text": target}
        elif "this" in text_lower or "it" in text_lower.split():
            target_selector = {"text": "<recent>"}

        intent = Intent(
            raw_text=raw_text,
            scene_id=scene_id,
            action=action,
            domains=domains,
            target_selector=target_selector,
            mood=effective_mood,
            style_profile=style_profile,
            constraints=dict(constraints or {}),
            risk_hint=risk_hint,
        )

        confidence = 0.9 if (domains or mood or action != "modify") else 0.5
        return IntentResolution(intent=intent, confidence=confidence, warnings=warnings)


def resolve_intent(
    raw_text: str,
    *,
    scene_id: str = "main",
    target: Optional[str] = None,
    style_profile: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> IntentResolution:
    return IntentResolver().resolve(
        raw_text,
        scene_id=scene_id,
        target=target,
        style_profile=style_profile,
        constraints=constraints,
    )
