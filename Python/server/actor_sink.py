"""ActorSink abstraction for generator output routing.

Generators produce canonical ActorSpec objects. The sink determines the
target backend: direct Unreal, DB desired state, or dry-run.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from server.specs.actor_spec import ActorSpec, params_to_spec

logger = logging.getLogger("UnrealMCP_Advanced")


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
    def count(self) -> int:
        """Return the number of actors managed by this sink."""
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
        self._total_count: int = 0

    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        self._buffer.append(spec.to_db_dict(self.scene_id))
        self._total_count += 1
        return {"success": True, "buffered": True, "mcp_id": spec.mcp_id}

    def flush(self) -> Dict[str, Any]:
        if not self._buffer:
            return {"success": True, "target": "scene_db", "generated_count": 0, "upserted_count": 0, "error_count": 0, "total_spawned": self._total_count, "message": "nothing to flush"}

        from server.scene_client import call_scene_syncd

        payload: Dict[str, Any] = {
            "scene_id": self.scene_id,
            "objects": self._buffer,
        }
        if self.group_id is not None:
            payload["group_id"] = self.group_id

        raw = call_scene_syncd("/objects/bulk-upsert", payload)
        count = len(self._buffer)

        error_count = raw.get("error_count", 0)
        partial_success = raw.get("partial_success", False)
        success = raw.get("success", False)

        if success and error_count == 0:
            self._buffer.clear()
            return {"success": True, "target": "scene_db", "generated_count": count, "upserted_count": count, "error_count": 0, "total_spawned": self._total_count, "message": f"Flushed {count} objects to scene-syncd"}
        elif partial_success or (success and error_count > 0):
            return {"success": False, "target": "scene_db", "generated_count": count, "upserted_count": count - error_count, "error_count": error_count, "total_spawned": self._total_count, "message": f"scene-syncd bulk-upsert partially failed: {error_count} of {count} objects failed"}
        else:
            self._buffer.clear()
            return {"success": False, "target": "scene_db", "generated_count": count, "upserted_count": 0, "error_count": error_count, "total_spawned": self._total_count, "message": f"scene-syncd bulk-upsert failed after flushing {count} objects"}

    def count(self) -> int:
        return self._total_count

    def delete(self, mcp_id: str) -> Dict[str, Any]:
        from server.scene_client import call_scene_syncd
        return call_scene_syncd("/objects/delete", {"scene_id": self.scene_id, "mcp_id": mcp_id})


class UnrealActorSink(ActorSink):
    """Sink that spawns actors directly in Unreal via the MCP bridge."""

    def __init__(self) -> None:
        self._count = 0
        self._total_count = 0  # survives flush()

    def spawn(self, spec: ActorSpec) -> Dict[str, Any]:
        from helpers.actor_name_manager import safe_spawn_actor
        from server.core import get_unreal_connection

        unreal = get_unreal_connection()
        result = safe_spawn_actor(unreal, spec.to_unreal_dict())
        if result and result.get("success"):
            self._count += 1
            self._total_count += 1
        return result

    def flush(self) -> Dict[str, Any]:
        count = self._count
        self._count = 0
        return {"success": True, "target": "unreal", "generated_count": count, "upserted_count": None, "error_count": None, "total_spawned": self._total_count, "message": f"UnrealActorSink: {count} actors spawned (total: {self._total_count})"}

    def count(self) -> int:
        return self._total_count

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
            "target": "dry_run",
            "dry_run": True,
            "count": count,  # backward compat alias
            "generated_count": count,
            "upserted_count": None,
            "error_count": None,
            "total_spawned": count,
            "message": f"Dry run: {count} actors would be spawned",
        }

    def count(self) -> int:
        return len(self.specs)

    def delete(self, mcp_id: str) -> Dict[str, Any]:
        self.deletions.append(mcp_id)
        return {"success": True, "dry_run": True, "mcp_id": mcp_id}


def make_actor_sink(
    target: str = "scene_db",
    scene_id: str = "main",
    group_id: Optional[str] = None,
) -> ActorSink:
    """Factory for creating the appropriate ActorSink based on target."""
    if target == "dry_run":
        return DryRunActorSink()
    if target == "scene_db":
        return SceneDbActorSink(scene_id=scene_id, group_id=group_id)
    if target == "unreal":
        return UnrealActorSink()
    raise ValueError(f"Unknown target: {target}")


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


