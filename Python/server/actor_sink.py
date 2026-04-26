"""ActorSink abstraction for generator output routing.

Generators produce canonical ActorSpec objects. The sink determines the
target backend: direct Unreal, DB desired state, or dry-run.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("UnrealMCP_Advanced")


@dataclass
class ActorSpec:
    """Canonical actor description that generators produce.

    All sinks accept this format. Conversion to backend-specific wire
    formats happens inside each sink, not in generators.
    """

    mcp_id: str
    desired_name: str
    actor_type: str = "StaticMeshActor"
    asset_ref: Dict[str, Any] = field(default_factory=lambda: {"path": "/Engine/BasicShapes/Cube.Cube"})
    transform: Dict[str, Any] = field(default_factory=lambda: {
        "location": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
        "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
    })
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
            "location": [loc.get("x", 0.0), loc.get("y", 0.0), loc.get("z", 0.0)],
            "rotation": [rot.get("pitch", 0.0), rot.get("yaw", 0.0), rot.get("roll", 0.0)],
            "scale": [scl.get("x", 1.0), scl.get("y", 1.0), scl.get("z", 1.0)],
            "static_mesh": self.asset_ref.get("path", ""),
            "tags": self.tags,
        }


class ActorSink(ABC):
    """Abstract base for actor output routing."""

    @abstractmethod
    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        """Emit a single actor. Return result dict."""
        ...

    @abstractmethod
    def flush(self) -> Dict[str, Any]:
        """Flush any buffered actors. Return summary."""
        ...

    @abstractmethod
    def delete(self, mcp_id: str) -> Dict[str, Any]:
        """Mark actor for deletion."""
        ...


class SceneDbActorSink(ActorSink):
    """Sink that writes desired actor state to the scene-syncd database."""

    def __init__(self, scene_id: str = "main", group_id: Optional[str] = None):
        self.scene_id = scene_id
        self.group_id = group_id
        self._buffer: List[Dict[str, Any]] = []

    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        self._buffer.append(spec.to_db_dict(self.scene_id))
        return {"success": True, "buffered": True, "mcp_id": spec.mcp_id}

    def flush(self) -> Dict[str, Any]:
        if not self._buffer:
            return {"success": True, "upserted_count": 0, "message": "nothing to flush"}

        from server.scene_client import call_scene_syncd

        payload: Dict[str, Any] = {
            "scene_id": self.scene_id,
            "objects": self._buffer,
        }
        if self.group_id is not None:
            payload["group_id"] = self.group_id

        result = call_scene_syncd("/objects/bulk-upsert", payload)
        count = len(self._buffer)
        self._buffer.clear()
        if result.get("success") is False:
            result["message"] = f"scene-syncd bulk-upsert failed after flushing {count} objects"
        else:
            result["message"] = f"Flushed {count} objects to scene-syncd"
        return result

    def delete(self, mcp_id: str) -> Dict[str, Any]:
        from server.scene_client import call_scene_syncd
        return call_scene_syncd("/objects/delete", {"scene_id": self.scene_id, "mcp_id": mcp_id})


class UnrealActorSink(ActorSink):
    """Sink that spawns actors directly in Unreal via the MCP bridge."""

    def __init__(self) -> None:
        self._count = 0

    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        from helpers.actor_name_manager import safe_spawn_actor
        from server.core import get_unreal_connection

        unreal = get_unreal_connection()
        result = safe_spawn_actor(unreal, spec.to_unreal_dict())
        if result and result.get("success"):
            self._count += 1
        return result

    def flush(self) -> Dict[str, Any]:
        count = self._count
        self._count = 0
        return {"success": True, "count": count, "message": f"UnrealActorSink: {count} actors spawned"}

    def delete(self, mcp_id: str) -> Dict[str, Any]:
        from helpers.actor_name_manager import safe_delete_actor_by_mcp_id
        from server.core import get_unreal_connection

        unreal = get_unreal_connection()
        return safe_delete_actor_by_mcp_id(unreal, mcp_id)


class DryRunActorSink(ActorSink):
    """Sink that records specs without any side effects. Useful for testing and previews."""

    def __init__(self) -> None:
        self.specs: List[ActorSpec] = []
        self.deletions: List[str] = []

    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        self.specs.append(spec)
        return {"success": True, "dry_run": True, "mcp_id": spec.mcp_id}

    def flush(self) -> Dict[str, Any]:
        count = len(self.specs)
        return {
            "success": True,
            "dry_run": True,
            "count": count,
            "specs": self.specs,
            "message": f"Dry run: {count} actors would be spawned",
        }

    def delete(self, mcp_id: str) -> Dict[str, Any]:
        self.deletions.append(mcp_id)
        return {"success": True, "dry_run": True, "mcp_id": mcp_id}


def _coerce_vec3(value: Any, default: List[float]) -> List[float]:
    """Coerce a value to a 3-element float list, accepting both list and dict forms."""
    if isinstance(value, dict):
        return [float(value.get("x", default[0])), float(value.get("y", default[1])), float(value.get("z", default[2]))]
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    if isinstance(value, (list, tuple)):
        return default
    return default


def _spawn_actor_via_sink_or_direct(
    sink, unreal, params: Dict[str, Any], tags: Optional[List[str]] = None
) -> bool:
    """Unified spawn helper for all helper modules.

    When sink is provided, converts params to ActorSpec and sends to sink.
    When sink is None, uses safe_spawn_actor via the unreal connection.

    Returns True on success, False on failure.
    """
    if sink is not None:
        sink.spawn(params_to_spec(params, tags=tags))
        return True

    from helpers.actor_name_manager import safe_spawn_actor
    from utils.responses import is_success_response

    resp = safe_spawn_actor(unreal, params)
    return resp is not None and is_success_response(resp)


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
    mcp_id = params.get("mcp_id") or params.get("name", "")
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