"""Scene database tools for the Unreal MCP server.

These tools call the Rust scene-syncd service over HTTP and are additive
to the existing direct Unreal tools. They do NOT replace them.
"""

import logging
from typing import Any, Dict, List, Optional

from server.core import mcp
from server.scene_client import call_scene_syncd, call_scene_syncd_get
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


def _scene_syncd_error_response(result: Dict[str, Any], operation: str) -> Dict[str, Any]:
    """Convert a scene-syncd error response to a consistent error format."""
    if result.get("success") is False and result.get("error"):
        err = result["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return make_error_response(f"scene-syncd {operation} failed: {msg}")
    return result


@mcp.tool()
def scene_create(
    scene_id: str = "main",
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a scene in the scene database."""
    payload = {"scene_id": scene_id}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    return _scene_syncd_error_response(
        call_scene_syncd("/scenes/create", payload), "scene_create"
    )


@mcp.tool()
def scene_upsert_actor(
    scene_id: str = "main",
    mcp_id: str = "",
    desired_name: Optional[str] = None,
    actor_type: str = "StaticMeshActor",
    asset_ref: Optional[Dict[str, Any]] = None,
    transform: Optional[Dict[str, Any]] = None,
    visual: Optional[Dict[str, Any]] = None,
    physics: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    group_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write desired actor state to the scene database. Does NOT touch Unreal."""
    try:
        mcp_id = sanitize_mcp_id(mcp_id)
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "mcp_id": mcp_id,
        "actor_type": actor_type,
    }
    if desired_name is not None:
        payload["desired_name"] = desired_name
    if asset_ref is not None:
        payload["asset_ref"] = asset_ref
    if transform is not None:
        payload["transform"] = transform
    if visual is not None:
        payload["visual"] = visual
    if physics is not None:
        payload["physics"] = physics
    if tags is not None:
        payload["tags"] = tags
    if group_id is not None:
        payload["group_id"] = group_id

    return _scene_syncd_error_response(
        call_scene_syncd("/objects/upsert", payload), "scene_upsert_actor"
    )


@mcp.tool()
def scene_upsert_actors(
    scene_id: str = "main",
    group_id: Optional[str] = None,
    objects: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Bulk upsert multiple actors to the scene database. Does NOT touch Unreal."""
    if not objects:
        return make_error_response("objects list must not be empty")

    try:
        scene_id = normalize_scene_id(scene_id)
        for i, obj in enumerate(objects):
            if "mcp_id" in obj:
                obj["mcp_id"] = sanitize_mcp_id(obj["mcp_id"])
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "objects": objects,
    }
    if group_id is not None:
        payload["group_id"] = group_id

    return _scene_syncd_error_response(
        call_scene_syncd("/objects/bulk-upsert", payload), "scene_upsert_actors"
    )


@mcp.tool()
def scene_delete_actor(
    scene_id: str = "main",
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Tombstone an actor in the scene database. Does NOT delete from Unreal until scene_sync."""
    try:
        validate_string(mcp_id, "mcp_id")
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload = {"scene_id": scene_id, "mcp_id": mcp_id}
    return _scene_syncd_error_response(
        call_scene_syncd("/objects/delete", payload), "scene_delete_actor"
    )


@mcp.tool()
def scene_snapshot_create(
    scene_id: str = "main",
    name: str = "",
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Snapshot the current desired scene state in the database. Does NOT touch Unreal."""
    try:
        validate_string(scene_id, "scene_id")
        validate_string(name, "name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {"scene_id": scene_id, "name": name}
    if description is not None:
        payload["description"] = description

    return _scene_syncd_error_response(
        call_scene_syncd("/snapshots/create", payload), "scene_snapshot_create"
    )


@mcp.tool()
def scene_snapshot_restore(
    snapshot_id: str = "",
    restore_mode: str = "replace_desired",
) -> Dict[str, Any]:
    """Restore snapshot contents to desired state in the database. Run scene_sync separately."""
    try:
        validate_string(snapshot_id, "snapshot_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload = {"snapshot_id": snapshot_id, "restore_mode": restore_mode}
    return _scene_syncd_error_response(
        call_scene_syncd("/snapshots/restore", payload), "scene_snapshot_restore"
    )


@mcp.tool()
def scene_list_objects(
    scene_id: str = "main",
    include_deleted: bool = False,
) -> Dict[str, Any]:
    """List desired objects in the scene database."""
    payload = {"scene_id": scene_id, "include_deleted": include_deleted}
    return _scene_syncd_error_response(
        call_scene_syncd("/objects/list", payload), "scene_list_objects"
    )


@mcp.tool()
def scene_create_wall(
    scene_id: str = "main",
    group_id: str = "wall_001",
    start: Optional[Dict[str, float]] = None,
    length: float = 1000.0,
    height: float = 300.0,
    thickness: float = 50.0,
    segments: int = 10,
    axis: str = "x",
) -> Dict[str, Any]:
    """Write wall segment desired actors to the scene database. Does NOT touch Unreal."""
    if segments < 1:
        return make_error_response("segments must be at least 1")
    if axis not in ("x", "y"):
        return make_error_response("axis must be 'x' or 'y'")

    origin = start or {"x": 0.0, "y": 0.0, "z": 0.0}
    segment_length = length / segments
    sink = SceneDbActorSink(scene_id=scene_id, group_id=group_id)
    for index in range(segments):
        x = float(origin.get("x", 0.0))
        y = float(origin.get("y", 0.0))
        if axis == "x":
            x += index * segment_length
        else:
            y += index * segment_length
        sink.spawn(ActorSpec(
            mcp_id=f"{group_id}_segment_{index:03d}",
            desired_name=f"{group_id}_segment_{index:03d}",
            actor_type="StaticMeshActor",
            asset_ref={"path": "/Engine/BasicShapes/Cube.Cube"},
            transform={
                "location": {"x": x, "y": y, "z": float(origin.get("z", 0.0)) + height / 2.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {
                    "x": segment_length / 100.0 if axis == "x" else thickness / 100.0,
                    "y": thickness / 100.0 if axis == "x" else segment_length / 100.0,
                    "z": height / 100.0,
                },
            },
            tags=["scene_wall", group_id],
            group_id=group_id,
        ))

    return _scene_syncd_error_response(sink.flush(), "scene_create_wall")


@mcp.tool()
def scene_create_pyramid(
    scene_id: str = "main",
    group_id: str = "pyramid_001",
    base_location: Optional[Dict[str, float]] = None,
    levels: int = 5,
    block_size: float = 100.0,
) -> Dict[str, Any]:
    """Write pyramid block desired actors to the scene database. Does NOT touch Unreal."""
    if levels < 1:
        return make_error_response("levels must be at least 1")
    if block_size <= 0:
        return make_error_response("block_size must be greater than 0")

    origin = base_location or {"x": 0.0, "y": 0.0, "z": 0.0}
    sink = SceneDbActorSink(scene_id=scene_id, group_id=group_id)
    index = 0
    for level in range(levels):
        width = levels - level
        offset = (width - 1) * block_size / 2.0
        for row in range(width):
            for col in range(width):
                sink.spawn(ActorSpec(
                    mcp_id=f"{group_id}_block_{index:03d}",
                    desired_name=f"{group_id}_block_{index:03d}",
                    actor_type="StaticMeshActor",
                    asset_ref={"path": "/Engine/BasicShapes/Cube.Cube"},
                    transform={
                        "location": {
                            "x": float(origin.get("x", 0.0)) + col * block_size - offset,
                            "y": float(origin.get("y", 0.0)) + row * block_size - offset,
                            "z": float(origin.get("z", 0.0)) + level * block_size + block_size / 2.0,
                        },
                        "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                        "scale": {"x": block_size / 100.0, "y": block_size / 100.0, "z": block_size / 100.0},
                    },
                    tags=["scene_pyramid", group_id],
                    group_id=group_id,
                ))
                index += 1

    return _scene_syncd_error_response(sink.flush(), "scene_create_pyramid")


@mcp.tool()
def scene_health() -> Dict[str, Any]:
    """Check the health of the scene-syncd service."""
    return call_scene_syncd_get("/health")


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
        call_scene_syncd("/sync/plan", payload), "scene_plan_sync"
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
        call_scene_syncd("/sync/apply", payload), "scene_sync"
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
        from server.core import get_unreal_connection
        conn = get_unreal_connection()
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
    db_result = call_scene_syncd("/components/upsert", component_payload)
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
        from server.core import get_unreal_connection
        conn = get_unreal_connection()
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
    db_result = call_scene_syncd("/components/upsert", component_payload)
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
        from server.core import get_unreal_connection
        conn = get_unreal_connection()
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
    db_result = call_scene_syncd("/components/upsert", component_payload)
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
        from server.core import get_unreal_connection
        conn = get_unreal_connection()
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
    db_result = call_scene_syncd("/realizations/upsert", realization_payload)
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
        call_scene_syncd("/components/upsert", payload), "scene_component_upsert"
    )
