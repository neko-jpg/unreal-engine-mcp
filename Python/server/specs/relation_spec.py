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
    def to_layout_edge(self) -> Dict[str, Any]:
        """Convert to Rust scene_relation bulk-upsert format."""
        result: Dict[str, Any] = {
            "relation_id": self.relation_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type,
        }
        if self.properties:
            result["properties"] = self.properties
        if self.metadata:
            result["metadata"] = self.metadata
        return result
