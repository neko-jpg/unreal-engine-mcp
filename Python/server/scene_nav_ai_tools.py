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
)

@mcp.tool()
def scene_create_navmesh_volume(
    scene_id: str = "main",
    volume_name: str = "NavMeshVolume",
    location: Optional[Dict[str, float]] = None,
    extent: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Create a NavMeshBoundsVolume in Unreal and register it as a component in the scene database."""
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    loc = location or {"x": 0.0, "y": 0.0, "z": 0.0}
    ext = extent or {"x": 500.0, "y": 500.0, "z": 500.0}

    # Send command to Unreal
    try:
        conn = _stc.get_unreal_connection()
        unreal_result = conn.send_command("create_nav_mesh_volume", {
            "volume_name": volume_name,
            "location": [loc["x"], loc["y"], loc["z"]],
            "extent": [ext["x"], ext["y"], ext["z"]],
        })
    except Exception as e:
        return make_error_response(f"Failed to send NavMesh volume command to Unreal: {e}")

    # Check Unreal command result
    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    # Store as component in scene DB
    component_payload = {
        "scene_id": scene_id,
        "entity_id": volume_name,
        "component_type": "navmesh",
        "name": volume_name,
        "properties": {
            "location": loc,
            "extent": ext,
        },
    }
    db_result = _stc.call_scene_syncd("/components/upsert", component_payload)
    db_err = _scene_syncd_error_response(db_result, "scene_create_navmesh_volume/db")
    if not db_err.get("success", True):
        return db_err

    return {
        "success": True,
        "unreal_result": unreal_result,
        "db_result": db_result,
    }




@mcp.tool()
def scene_create_patrol_route(
    scene_id: str = "main",
    route_name: str = "PatrolRoute_001",
    points: Optional[List[Dict[str, float]]] = None,
    closed_loop: bool = False,
) -> Dict[str, Any]:
    """Create a patrol route (spline-based path) in Unreal and register it as an AI component in the scene database."""
    try:
        validate_string(scene_id, "scene_id")
        validate_string(route_name, "route_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if not points or len(points) < 2:
        return make_error_response("patrol route requires at least 2 points")

    # Send command to Unreal
    try:
        conn = _stc.get_unreal_connection()
        unreal_result = conn.send_command("create_patrol_route", {
            "patrol_route_name": route_name,
            "points": points,
            "closed_loop": closed_loop,
        })
    except Exception as e:
        return make_error_response(f"Failed to send patrol route command to Unreal: {e}")

    # Check Unreal command result
    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    # Store as component in scene DB
    component_payload = {
        "scene_id": scene_id,
        "entity_id": route_name,
        "component_type": "ai_patrol",
        "name": route_name,
        "properties": {
            "points": points,
            "closed_loop": closed_loop,
        },
    }
    db_result = _stc.call_scene_syncd("/components/upsert", component_payload)
    db_err = _scene_syncd_error_response(db_result, "scene_create_patrol_route/db")
    if not db_err.get("success", True):
        return db_err

    return {
        "success": True,
        "unreal_result": unreal_result,
        "db_result": db_result,
    }




@mcp.tool()
def scene_set_ai_behavior(
    scene_id: str = "main",
    entity_id: str = "",
    actor_name: Optional[str] = None,
    behavior_tree: Optional[str] = None,
    perception_radius: float = 1000.0,
) -> Dict[str, Any]:
    """Configure AI behavior for an actor in Unreal and store it as a component in the scene database."""
    try:
        validate_string(scene_id, "scene_id")
        validate_string(entity_id, "entity_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    target_name = actor_name or entity_id

    # Send command to Unreal
    try:
        conn = _stc.get_unreal_connection()
        params = {
            "actor_name": target_name,
            "perception_radius": perception_radius,
        }
        if behavior_tree:
            params["behavior_tree_path"] = behavior_tree
        unreal_result = conn.send_command("set_ai_behavior", params)
    except Exception as e:
        return make_error_response(f"Failed to send AI behavior command to Unreal: {e}")

    # Check Unreal command result
    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    # Store as component in scene DB
    component_payload = {
        "scene_id": scene_id,
        "entity_id": entity_id,
        "component_type": "ai_behavior",
        "name": f"ai_{entity_id}",
        "properties": {
            "behavior_tree": behavior_tree,
            "perception_radius": perception_radius,
        },
    }
    db_result = _stc.call_scene_syncd("/components/upsert", component_payload)
    db_err = _scene_syncd_error_response(db_result, "scene_set_ai_behavior/db")
    if not db_err.get("success", True):
        return db_err

    return {
        "success": True,
        "unreal_result": unreal_result,
        "db_result": db_result,
    }




@mcp.tool()
def scene_spawn_blueprint(
    scene_id: str = "main",
    entity_id: str = "",
    blueprint_path: str = "",
    actor_name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Spawn an actor from a Blueprint in Unreal and register a realization record in the scene database."""
    try:
        validate_string(scene_id, "scene_id")
        validate_string(entity_id, "entity_id")
        validate_string(blueprint_path, "blueprint_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    name = actor_name or entity_id
    loc = location or {"x": 0.0, "y": 0.0, "z": 0.0}
    rot = rotation or {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    scl = scale or {"x": 1.0, "y": 1.0, "z": 1.0}

    # Send command to Unreal
    try:
        conn = _stc.get_unreal_connection()
        unreal_result = conn.send_command("spawn_blueprint_actor", {
            "blueprint_name": blueprint_path,
            "actor_name": name,
            "location": [loc["x"], loc["y"], loc["z"]],
            "rotation": [rot["pitch"], rot["yaw"], rot["roll"]],
            "scale": [scl["x"], scl["y"], scl["z"]],
        })
    except Exception as e:
        return make_error_response(f"Failed to spawn blueprint actor in Unreal: {e}")

    # Check Unreal command result
    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    # Store as realization in scene DB
    realization_payload = {
        "scene_id": scene_id,
        "entity_id": entity_id,
        "policy": "blueprint",
        "status": "realized",
        "unreal_actor_name": name,
        "metadata": {
            "blueprint_path": blueprint_path,
            "location": loc,
            "rotation": rot,
            "scale": scl,
        },
    }
    db_result = _stc.call_scene_syncd("/realizations/upsert", realization_payload)
    db_err = _scene_syncd_error_response(db_result, "scene_spawn_blueprint/db")
    if not db_err.get("success", True):
        return db_err

    return {
        "success": True,
        "unreal_result": unreal_result,
        "db_result": db_result,
    }




@mcp.tool()
def scene_component_upsert(
    scene_id: str = "main",
    entity_id: str = "",
    component_type: str = "",
    name: str = "",
    properties: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or update a component (collision, navmesh, AI, etc.) for an entity in the scene database. Does NOT touch Unreal directly."""
    try:
        validate_string(scene_id, "scene_id")
        validate_string(entity_id, "entity_id")
        validate_string(component_type, "component_type")
        validate_string(name, "name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "entity_id": entity_id,
        "component_type": component_type,
        "name": name,
    }
    if properties is not None:
        payload["properties"] = properties
    if metadata is not None:
        payload["metadata"] = metadata

    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/components/upsert", payload), "scene_component_upsert"
    )




