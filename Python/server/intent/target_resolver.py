"""TargetResolver - resolves natural-language target phrases to scene selectors.

Priority order:
  1. tags          ("all wall torches" => tag match)
  2. entity kind/name fuzzy
  3. component_type
  4. spatial relation (near/inside) - placeholder
  5. recent_operations (when text references "it"/"this"/"<recent>")

If multiple plausible candidates exist or the phrase is too generic, mark the
result ambiguous so SafetyChecker can require user approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from server.intent.scene_context import (
    EntityBrief,
    OperationBrief,
    SceneContextPack,
    SceneObjectBrief,
)


@dataclass
class TargetResolution:
    selector: Dict[str, Any] = field(default_factory=dict)
    matched_mcp_ids: List[str] = field(default_factory=list)
    matched_entity_ids: List[str] = field(default_factory=list)
    ambiguous: bool = False
    reason: str = ""
    candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "matched_mcp_ids": self.matched_mcp_ids,
            "matched_entity_ids": self.matched_entity_ids,
            "ambiguous": self.ambiguous,
            "reason": self.reason,
            "candidates": self.candidates,
        }


_FILLER_WORDS = {"the", "a", "an", "of", "this", "that", "all", "every"}


def _tokenize(text: str) -> List[str]:
    return [w for w in re.split(r"\W+", text.lower()) if w and w not in _FILLER_WORDS]


def _iter_objects(pack: SceneContextPack) -> Iterable[SceneObjectBrief]:
    for items in pack.objects_by_kind.values():
        for obj in items:
            yield obj


def _iter_entities(pack: SceneContextPack) -> Iterable[EntityBrief]:
    for items in pack.entities_by_kind.values():
        for ent in items:
            yield ent


def _resolve_recent(pack: SceneContextPack) -> TargetResolution:
    matched: List[str] = []
    for op in reversed(pack.recent_operations):
        if op.mcp_id and op.mcp_id not in matched:
            matched.append(op.mcp_id)
        if len(matched) >= 3:
            break
    if not matched:
        return TargetResolution(
            selector={"kind": "recent"},
            ambiguous=True,
            reason="no recent operations available to resolve 'it'/'this'",
        )
    return TargetResolution(
        selector={"kind": "recent", "mcp_ids": matched},
        matched_mcp_ids=matched,
        reason="resolved via recent_operations",
    )


def _resolve_tag(tokens: List[str], pack: SceneContextPack) -> TargetResolution:
    matched_mcp: List[str] = []
    candidate_tags = set(tokens)
    for obj in _iter_objects(pack):
        if any(t.lower() in candidate_tags for t in obj.tags):
            matched_mcp.append(obj.mcp_id)
    if matched_mcp:
        return TargetResolution(
            selector={"kind": "tag", "tags": list(candidate_tags)},
            matched_mcp_ids=matched_mcp,
            reason="tag-based selection",
        )
    return TargetResolution(selector={}, ambiguous=True, reason="no tag match")


def _resolve_entity(tokens: List[str], pack: SceneContextPack) -> TargetResolution:
    matched: List[str] = []
    kind_candidates: List[str] = []
    for entity in _iter_entities(pack):
        if entity.kind and entity.kind.lower() in tokens:
            matched.append(entity.entity_id)
            kind_candidates.append(entity.kind)
            continue
        for token in tokens:
            if entity.name and token in entity.name.lower():
                matched.append(entity.entity_id)
                break
    if matched:
        return TargetResolution(
            selector={"kind": "entity", "tokens": tokens, "kinds": sorted(set(kind_candidates))},
            matched_entity_ids=matched,
            reason="entity kind/name fuzzy match",
        )
    return TargetResolution(selector={}, ambiguous=True, reason="no entity match")


def _resolve_component_type(tokens: List[str], pack: SceneContextPack) -> TargetResolution:
    matched: List[str] = []
    for ctype, comps in pack.components_by_type.items():
        if ctype.lower() in tokens:
            for c in comps:
                matched.append(c.entity_id)
    if matched:
        return TargetResolution(
            selector={"kind": "component_type", "tokens": tokens},
            matched_entity_ids=sorted(set(matched)),
            reason="component_type match",
        )
    return TargetResolution(selector={}, ambiguous=True, reason="no component_type match")


class TargetResolver:
    """Resolve a natural-language target phrase to a structured selector."""

    def __init__(self, pack: SceneContextPack) -> None:
        self.pack = pack

    def resolve(self, phrase: Optional[str]) -> TargetResolution:
        if not phrase:
            return TargetResolution(
                selector={"kind": "scene"},
                ambiguous=False,
                reason="no target phrase; default to whole-scene",
            )
        phrase_norm = phrase.strip().lower()
        if phrase_norm in {"<recent>", "this", "it", "that"}:
            return _resolve_recent(self.pack)

        tokens = _tokenize(phrase_norm)
        if not tokens:
            return TargetResolution(selector={}, ambiguous=True, reason="empty target after tokenisation")

        for resolver_fn in (_resolve_tag, _resolve_entity, _resolve_component_type):
            res = resolver_fn(tokens, self.pack)
            if not res.ambiguous and (res.matched_mcp_ids or res.matched_entity_ids):
                return res

        # Heuristic fallback: scene-wide modify with the phrase as a tag hint
        return TargetResolution(
            selector={"kind": "fallback", "tokens": tokens},
            ambiguous=True,
            reason="no specific match; fallback to scene with low confidence",
            candidates=tokens,
        )


def resolve_target(phrase: Optional[str], pack: SceneContextPack) -> TargetResolution:
    return TargetResolver(pack).resolve(phrase)
