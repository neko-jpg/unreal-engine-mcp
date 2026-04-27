from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EntitySpec:
    """Semantic world object: a castle, room, road, or enemy.

    Entities are abstract design concepts that may be realized into
    one or more ActorSpecs depending on the RealizationPolicy.
    """

    entity_id: str
    kind: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    mcp_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
