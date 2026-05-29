"""Protocol definitions for scene-type-specific observation and quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SceneTypeProtocol:
    protocol_id: str
    scene_type: str
    anchors: Dict[str, str] = field(default_factory=dict)
    required_shots: List[str] = field(default_factory=list)
    required_metadata: List[str] = field(default_factory=list)
    quality_gates: Dict[str, Any] = field(default_factory=dict)
    metric_weights: Dict[str, float] = field(default_factory=dict)
    refinement_actions: Dict[str, Any] = field(default_factory=dict)
    semantic_parts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "scene_type": self.scene_type,
            "anchors": dict(self.anchors),
            "required_shots": list(self.required_shots),
            "required_metadata": list(self.required_metadata),
            "quality_gates": dict(self.quality_gates),
            "metric_weights": dict(self.metric_weights),
            "refinement_actions": dict(self.refinement_actions),
            "semantic_parts": list(self.semantic_parts),
        }
