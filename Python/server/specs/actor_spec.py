from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _sanitize_mcp_id(value: str) -> str:
    """Lightweight inline sanitizer to avoid circular imports."""
    import re

    pattern = re.compile(r"^[A-Za-z0-9_.:-]+$")
    value = value.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    if not value or not pattern.match(value):
        raise ValueError(f"invalid mcp_id after sanitization: '{value}'")
    return value


def _coerce_vec3(value, default=(0.0, 0.0, 0.0)):
    """Coerce a value to a 3-element float list, accepting both list and dict forms."""
    if isinstance(value, dict):
        return [
            float(value.get("x", default[0])),
            float(value.get("y", default[1])),
            float(value.get("z", default[2])),
        ]
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    if isinstance(value, (list, tuple)):
        return list(default)
    return list(default)


@dataclass
class ActorSpec:
    """Canonical actor description that generators produce.

    All sinks accept this format. Conversion to backend-specific wire
    formats happens inside each sink, not in generators.
    """

    mcp_id: str
    desired_name: str
    actor_type: str = "StaticMeshActor"
    asset_ref: Dict[str, Any] = field(
        default_factory=lambda: {"path": "/Engine/BasicShapes/Cube.Cube"}
    )
    transform: Dict[str, Any] = field(
        default_factory=lambda: {
            "location": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
        }
    )
    tags: List[str] = field(default_factory=list)
    group_id: Optional[str] = None
    visual: Dict[str, Any] = field(default_factory=dict)
    physics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self, scene_id: str = "main") -> Dict[str, Any]:
        """Convert to the dict format expected by the scene-syncd bulk-upsert API."""
        d: Dict[str, Any] = {
            "scene_id": scene_id,
            "mcp_id": self.mcp_id,
            "desired_name": self.desired_name,
            "actor_type": self.actor_type,
            "asset_ref": self.asset_ref,
            "transform": self.transform,
            "tags": self.tags,
        }
        if self.group_id is not None:
            d["group_id"] = self.group_id
        if self.visual:
            d["visual"] = self.visual
        if self.physics:
            d["physics"] = self.physics
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_unreal_dict(self) -> Dict[str, Any]:
        """Convert to the Unreal bridge wire format (arrays for location/rotation/scale)."""
        loc = self.transform.get("location", {})
        rot = self.transform.get("rotation", {})
        scl = self.transform.get("scale", {})
        return {
            "name": self.desired_name,
            "mcp_id": self.mcp_id,
            "type": self.actor_type,
            "location": [
                loc.get("x", 0.0),
                loc.get("y", 0.0),
                loc.get("z", 0.0),
            ],
            "rotation": [
                rot.get("pitch", 0.0),
                rot.get("yaw", 0.0),
                rot.get("roll", 0.0),
            ],
            "scale": [
                scl.get("x", 1.0),
                scl.get("y", 1.0),
                scl.get("z", 1.0),
            ],
            "static_mesh": self.asset_ref.get("path", ""),
            "tags": self.tags,
        }


def params_to_spec(
    params: Dict[str, Any],
    tags: Optional[List[str]] = None,
    group_id: Optional[str] = None,
) -> ActorSpec:
    """Convert an Unreal wire-format params dict to an ActorSpec.

    This is the inverse of ActorSpec.to_unreal_dict() and is used when
    migrating helper modules that construct params dicts for safe_spawn_actor.
    """
    loc = _coerce_vec3(params.get("location"), [0.0, 0.0, 0.0])
    rot = _coerce_vec3(params.get("rotation"), [0.0, 0.0, 0.0])
    scl = _coerce_vec3(params.get("scale"), [1.0, 1.0, 1.0])
    mcp_id_raw = params.get("mcp_id") or params.get("name", "")
    mcp_id = _sanitize_mcp_id(mcp_id_raw)
    return ActorSpec(
        mcp_id=mcp_id,
        desired_name=params.get("name", ""),
        actor_type=params.get("type", "StaticMeshActor"),
        asset_ref={"path": params.get("static_mesh", "/Engine/BasicShapes/Cube.Cube")},
        transform={
            "location": {"x": loc[0], "y": loc[1], "z": loc[2]},
            "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]},
            "scale": {"x": scl[0], "y": scl[1], "z": scl[2]},
        },
        tags=tags or [],
        group_id=group_id,
    )
