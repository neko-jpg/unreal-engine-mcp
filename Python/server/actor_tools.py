"""Actor management tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_vector3, validate_string, validate_unreal_path,
    ValidationError, make_validation_error_response_from_exception,
)
from helpers.actor_name_manager import safe_spawn_actor, safe_delete_actor

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def get_actors_in_level(random_string: str = "") -> Dict[str, Any]:
    """Get a list of all actors in the current level."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        response = unreal.send_command("get_actors_in_level", {})
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"get_actors_in_level error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def find_actors_by_name(pattern: str) -> Dict[str, Any]:
    """Find actors by name pattern."""
    try:
        validate_string(pattern, "pattern")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        response = unreal.send_command("find_actors_by_name", {"pattern": pattern})
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"find_actors_by_name error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def delete_actor(name: str) -> Dict[str, Any]:
    """Delete an actor by name."""
    try:
        validate_string(name, "name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        response = safe_delete_actor(unreal, name)
        return response
    except Exception as e:
        logger.error(f"delete_actor error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def spawn_actor(
    type: str,
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
    static_mesh: Optional[str] = None
) -> Dict[str, Any]:
    """Spawn an actor by type and name."""
    try:
        validate_string(type, "type")
        validate_string(name, "name")
        validate_vector3(location, "location", allow_none=True)
        validate_vector3(rotation, "rotation", allow_none=True)
        validate_vector3(scale, "scale", allow_none=True)
        if static_mesh is not None:
            validate_unreal_path(static_mesh, "static_mesh")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {
            "type": type,
            "name": name
        }
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        if static_mesh is not None:
            params["static_mesh"] = static_mesh

        return safe_spawn_actor(unreal, params, auto_unique_name=False)
    except Exception as e:
        logger.error(f"spawn_actor error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def set_actor_transform(
    name: str,
    location: List[float] = None,
    rotation: List[float] = None,
    scale: List[float] = None
) -> Dict[str, Any]:
    """Set the transform of an actor."""
    try:
        validate_string(name, "name")
        validate_vector3(location, "location", allow_none=True)
        validate_vector3(rotation, "rotation", allow_none=True)
        validate_vector3(scale, "scale", allow_none=True)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale

        response = unreal.send_command("set_actor_transform", params)
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"set_actor_transform error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def batch_spawn_actors(
    actors: List[Dict[str, Any]],
    dry_run: bool = False
) -> Dict[str, Any]:
    """Spawn multiple actors in a single call. Each actor dict should have 'name', 'type', and optionally 'location', 'rotation', 'scale', 'static_mesh'.

    Example:
        actors = [
            {"name": "Wall_001", "type": "StaticMeshActor", "location": [0,0,0], "static_mesh": "/Engine/BasicShapes/Cube.Cube"},
            {"name": "Wall_002", "type": "StaticMeshActor", "location": [100,0,0]}
        ]
    """
    from server.validation import validate_positive_int
    if not isinstance(actors, list):
        return {"success": False, "message": "actors must be a list of actor dictionaries"}
    if len(actors) == 0:
        return {"success": False, "message": "actors list must not be empty"}
    if len(actors) > MAX_ACTORS_PER_BATCH:
        return {
            "success": False,
            "message": f"Requested {len(actors)} actors exceeds batch limit of {MAX_ACTORS_PER_BATCH}",
            "requested": len(actors),
            "max_actors": MAX_ACTORS_PER_BATCH,
        }

    validated = []
    for i, actor_def in enumerate(actors):
        if not isinstance(actor_def, dict):
            return {"success": False, "message": f"actors[{i}] must be a dictionary, got {type(actor_def).__name__}"}
        try:
            name = validate_string(actor_def.get("name"), f"actors[{i}].name")
            actor_type = validate_string(actor_def.get("type"), f"actors[{i}].type")
            loc = validate_vector3(actor_def.get("location"), f"actors[{i}].location", allow_none=True)
            rot = validate_vector3(actor_def.get("rotation"), f"actors[{i}].rotation", allow_none=True)
            scl = validate_vector3(actor_def.get("scale"), f"actors[{i}].scale", allow_none=True)
            mesh = actor_def.get("static_mesh")
            if mesh is not None:
                mesh = validate_unreal_path(mesh, f"actors[{i}].static_mesh")
        except ValidationError as e:
            return make_validation_error_response_from_exception(e)
        validated.append({
            "name": name,
            "type": actor_type,
            "location": loc,
            "rotation": rot,
            "scale": scl,
            "static_mesh": mesh,
        })

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "actor_count": len(validated),
            "actors": validated,
            "message": f"Would spawn {len(validated)} actors. Set dry_run=False to execute.",
        }

    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    spawned = []
    failed = []
    for actor_def in validated:
        params = {"name": actor_def["name"], "type": actor_def["type"]}
        if actor_def["location"] is not None:
            params["location"] = actor_def["location"]
        if actor_def["rotation"] is not None:
            params["rotation"] = actor_def["rotation"]
        if actor_def["scale"] is not None:
            params["scale"] = actor_def["scale"]
        if actor_def["static_mesh"] is not None:
            params["static_mesh"] = actor_def["static_mesh"]
        try:
            resp = safe_spawn_actor(unreal, params)
            if resp and resp.get("status") == "success":
                spawned.append(resp)
            else:
                failed.append({"name": actor_def["name"], "reason": str(resp)})
        except Exception as e:
            failed.append({"name": actor_def["name"], "reason": str(e)})

    result = {
        "success": len(failed) == 0,
        "spawned_count": len(spawned),
        "failed_count": len(failed),
        "actors": spawned,
    }
    if failed:
        result["failed"] = failed
        result["message"] = f"Spawned {len(spawned)}/{len(validated)} actors. {len(failed)} failed."
    else:
        result["message"] = f"Successfully spawned all {len(spawned)} actors."
    return result
