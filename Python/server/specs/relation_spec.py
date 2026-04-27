from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RelationSpec:
    """Relationship between two entities.

    relation_type values: contains, attached_to, spawned_by, adjacent_to
    """

    relation_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
