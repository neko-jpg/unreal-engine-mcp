import logging
from typing import Any, Dict, List, Optional

from server.core import mcp
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")

import server.scene_tools_common as _stc

from server.scene_tools_common import (
    _scene_syncd_error_response,
    _scene_syncd_data,
    _unreal_envelope,
)

@mcp.tool()
def scene_plan_sync(
    scene_id: str = "main",
    mode: str = "plan_only",
    orphan_policy: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare desired state in the database with actual state in Unreal and return a plan of create/update/delete/noop/conflict operations. Does NOT modify Unreal."""
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "mode": mode,
    }
    if orphan_policy is not None:
        payload["orphan_policy"] = orphan_policy

    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/sync/plan", payload), "scene_plan_sync"
    )




@mcp.tool()
def scene_sync(
    scene_id: str = "main",
    mode: str = "apply_safe",
    allow_delete: bool = False,
    max_operations: int = 500,
) -> Dict[str, Any]:
    """Apply a sync to create/update/delete actors in Unreal based on desired state in the database. Use scene_plan_sync first to preview changes."""
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "mode": mode,
        "allow_delete": allow_delete,
        "max_operations": max_operations,
    }

    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/sync/apply", payload), "scene_sync"
    )


@mcp.tool()
def scene_compile_apply_streaming(
    scene_id: str = "main",
    mode: str = "apply_safe",
    allow_delete: bool = False,
    batch_size: int = 500,
    max_operations: int = 50000,
) -> Dict[str, Any]:
    """Apply a sync in streaming mode for large scenes (中長期-3).

    Hits the scene-syncd `/sync/apply-stream` NDJSON endpoint, collects all
    progress events, and returns the aggregate result.

    Args:
        scene_id: Scene identifier.
        mode: `apply_safe` (default, no deletes) or `apply_all`.
        allow_delete: Allow actor removal regardless of mode.
        batch_size: Number of operations per progress checkpoint (default 500).
        max_operations: Hard cap; rejects plans larger than this (default 50000).

    Returns:
        Aggregate dict with `success`, `events` (list of all NDJSON events),
        `progress_events` count, `warnings`, and `result` (final apply result)
        when the stream completes successfully.
    """
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    from server.scene_client import call_scene_syncd_stream

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "mode": mode,
        "allow_delete": allow_delete,
        "batch_size": batch_size,
        "max_operations": max_operations,
    }

    events: List[Dict[str, Any]] = []
    progress_count = 0
    final_result: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    error_message: Optional[str] = None

    for event in call_scene_syncd_stream("/sync/apply-stream", payload):
        events.append(event)
        kind = event.get("event")
        if kind == "progress":
            progress_count += 1
        elif kind == "warning":
            warnings.append(str(event.get("message", "")))
        elif kind == "complete":
            final_result = event.get("result")
        elif kind == "error":
            error_message = str(event.get("message", ""))
            break

    if error_message is not None:
        return make_error_response(
            f"scene_compile_apply_streaming failed: {error_message}"
        )

    return {
        "success": True,
        "scene_id": scene_id,
        "events": events,
        "progress_events": progress_count,
        "warnings": warnings,
        "result": final_result,
    }




@mcp.tool()
def scene_get_instance_sets(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Get instance set grouping preview for a scene. Returns which objects would be grouped into ISM/HISM instance sets by the density planner, along with their mesh, material, and instance count. Useful for debugging render planning and instance set sync."""
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    result = _stc.call_scene_syncd("/sync/plan", {"scene_id": scene_id, "mode": "plan_only"})
    data = _scene_syncd_data(result)
    if result.get("success") is False:
        return _scene_syncd_error_response(result, "scene_get_instance_sets")

    instance_sets = data.get("instance_sets", [])
    summary = data.get("summary", {})

    return {
        "success": True,
        "scene_id": scene_id,
        "instance_sets": instance_sets,
        "summary": {
            "total_instance_sets": summary.get("instance_sets", 0),
            "instance_set_creates": summary.get("instance_set_creates", 0),
            "individual_creates": summary.get("create", 0),
            "individual_updates": summary.get("update_transform", 0),
            "individual_deletes": summary.get("delete", 0),
        },
    }




@mcp.tool()
def scene_spawn_instance_set(
    set_id: str = "",
    mesh_path: str = "",
    material_path: Optional[str] = None,
    transforms: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Spawn an instance set (HISM/ISM) in Unreal. Creates an actor with a HierarchicalInstancedStaticMeshComponent containing all instances at once. Use for efficiently rendering many identical meshes (crenellations, bricks, tiles)."""
    try:
        validate_string(set_id, "set_id")
        validate_string(mesh_path, "mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    params: Dict[str, Any] = {
        "set_id": set_id,
        "mesh_path": mesh_path,
        "transforms": transforms or [],
    }
    if material_path:
        params["material_path"] = material_path

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("spawn_instance_set", params)
    except Exception as e:
        return make_error_response(f"Failed to spawn instance set in Unreal: {e}")

    if not result.get("success", False):
        return make_error_response(f"Unreal command failed: {result.get('error', 'unknown error')}")

    return {"success": True, "unreal_result": result}




@mcp.tool()
def scene_update_instance_set(
    set_id: str = "",
    transforms: Optional[List[Dict[str, Any]]] = None,
    material_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing instance set in Unreal. Replaces all instances with the provided transforms. Optionally updates the material."""
    try:
        validate_string(set_id, "set_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    params: Dict[str, Any] = {
        "set_id": set_id,
        "transforms": transforms or [],
    }
    if material_path:
        params["material_path"] = material_path

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("update_instance_set", params)
    except Exception as e:
        return make_error_response(f"Failed to update instance set in Unreal: {e}")

    if not result.get("success", False):
        return make_error_response(f"Unreal command failed: {result.get('error', 'unknown error')}")

    return {"success": True, "unreal_result": result}




@mcp.tool()
def scene_delete_instance_set(
    set_id: str = "",
) -> Dict[str, Any]:
    """Delete an instance set from Unreal by set_id. Removes the actor and its ISM/HISM component."""
    try:
        validate_string(set_id, "set_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("delete_instance_set", {"set_id": set_id})
    except Exception as e:
        return make_error_response(f"Failed to delete instance set in Unreal: {e}")

    if not result.get("success", False):
        return make_error_response(f"Unreal command failed: {result.get('error', 'unknown error')}")

    return {"success": True, "unreal_result": result}




@mcp.tool()
def scene_get_instance_set_state(
    set_id: str = "",
) -> Dict[str, Any]:
    """Query the state of an instance set in Unreal. Returns instance count, mesh path, material path, and whether it uses HISM."""
    try:
        validate_string(set_id, "set_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("get_instance_set_state", {"set_id": set_id})
    except Exception as e:
        return make_error_response(f"Failed to get instance set state from Unreal: {e}")

    return _unreal_envelope("get_instance_set_state", result)




@mcp.tool()
def scene_list_instance_sets() -> Dict[str, Any]:
    """List all instance sets currently in Unreal. Returns set_id, mesh, material, instance_count, and use_hism for each set."""
    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("list_instance_sets", {})
    except Exception as e:
        return make_error_response(f"Failed to list instance sets from Unreal: {e}")

    return _unreal_envelope("list_instance_sets", result)




