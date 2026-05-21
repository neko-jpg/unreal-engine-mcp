"""AI and Navigation tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def create_behavior_tree(
    asset_name: str,
    package_path: str = "/Game/AI/",
) -> Dict[str, Any]:
    """Create a new BehaviorTree asset.

    asset_name: Name for the new BehaviorTree asset
    package_path: Package path (default /Game/AI/)
    """
    try:
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command(
            "create_behavior_tree",
            {"asset_name": asset_name, "package_path": package_path},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_behavior_tree error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_blackboard(
    asset_name: str,
    package_path: str = "/Game/AI/",
) -> Dict[str, Any]:
    """Create a new BlackboardData asset.

    asset_name: Name for the new Blackboard asset
    package_path: Package path (default /Game/AI/)
    """
    try:
        validate_string(asset_name, "asset_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command(
            "create_blackboard",
            {"asset_name": asset_name, "package_path": package_path},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_blackboard error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_nav_modifier_volume(
    name: str = "NavModifierVolume",
    location: Optional[List[float]] = None,
    extent: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Create a NavModifierVolume in the level.

    name: Actor name
    location: [x, y, z] location
    extent: [x, y, z] box extent in cm
    """
    try:
        validate_string(name, "name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = {"value": location}
    if extent is not None:
        params["extent"] = {"value": extent}

    try:
        response = unreal.send_command("create_nav_modifier_volume", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_nav_modifier_volume error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_nav_link_proxy(
    name: str = "NavLinkProxy",
    location: Optional[List[float]] = None,
    left: Optional[List[float]] = None,
    right: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Create a NavLinkProxy in the level.

    name: Actor name
    location: [x, y, z] location
    left: [x, y, z] left connection point relative to location
    right: [x, y, z] right connection point relative to location
    """
    try:
        validate_string(name, "name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = {"value": location}
    if left is not None:
        params["left"] = {"value": left}
    if right is not None:
        params["right"] = {"value": right}

    try:
        response = unreal.send_command("create_nav_link_proxy", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_nav_link_proxy error: {e}")
        return make_error_response(str(e))

# W1-D AI / Behavior Tree expansion (UE 5.7)

_BLACKBOARD_KEY_TYPES = {
    "Bool", "Int", "Integer", "Float", "String", "Name",
    "Vector", "Rotator", "Object", "Class",
}


@mcp.tool()
def add_blackboard_key(
    blackboard_path: str,
    key_name: str,
    key_type: str,
    instance_synced: bool = False,
) -> Dict[str, Any]:
    """Append a typed key to a UBlackboardData asset.

    blackboard_path: /Game path to the existing UBlackboardData asset
    key_name: New key identifier
    key_type: Bool | Int | Integer | Float | String | Name | Vector | Rotator | Object | Class
    instance_synced: If True, sync the key across all blackboard instances
    """
    try:
        validate_string(blackboard_path, "blackboard_path")
        validate_string(key_name, "key_name")
        validate_string(key_type, "key_type")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if key_type not in _BLACKBOARD_KEY_TYPES:
        return make_error_response(
            f"key_type must be one of {sorted(_BLACKBOARD_KEY_TYPES)}"
        )
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "add_blackboard_key",
            {
                "blackboard_path": blackboard_path,
                "key_name": key_name,
                "key_type": key_type,
                "instance_synced": instance_synced,
            },
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"add_blackboard_key error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def remove_blackboard_key(blackboard_path: str, key_name: str) -> Dict[str, Any]:
    """Remove all entries with the given name from a UBlackboardData asset.

    blackboard_path: /Game path to the existing UBlackboardData asset
    key_name: Key identifier to remove
    """
    try:
        validate_string(blackboard_path, "blackboard_path")
        validate_string(key_name, "key_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "remove_blackboard_key",
            {"blackboard_path": blackboard_path, "key_name": key_name},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"remove_blackboard_key error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def add_ai_perception(actor_name: str) -> Dict[str, Any]:
    """Attach a UAIPerceptionComponent to an actor.

    actor_name: Editor-world actor name or label (typically an AIController).
                If the component already exists, returns success with
                `already_existed: true`.
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("add_ai_perception", {"actor_name": actor_name})
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"add_ai_perception error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def configure_ai_sense_sight(
    actor_name: str,
    sight_radius: Optional[float] = None,
    lose_sight_radius: Optional[float] = None,
    peripheral_vision_angle_degrees: Optional[float] = None,
    auto_success_range_from_last_seen: Optional[float] = None,
    detect_neutrals: Optional[bool] = None,
    detect_friendlies: Optional[bool] = None,
    detect_enemies: Optional[bool] = None,
) -> Dict[str, Any]:
    """Configure UAISenseConfig_Sight on an actor's UAIPerceptionComponent.

    actor_name: Editor-world actor with an UAIPerceptionComponent
                (call add_ai_perception first if missing).
    sight_radius / lose_sight_radius: cm.
    peripheral_vision_angle_degrees: degrees from forward.
    auto_success_range_from_last_seen: cm.
    detect_neutrals / friendlies / enemies: affiliation filter flags.

    Sets Sight as the dominant sense if none was set.
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    for name, value in [
        ("sight_radius", sight_radius),
        ("lose_sight_radius", lose_sight_radius),
        ("peripheral_vision_angle_degrees", peripheral_vision_angle_degrees),
        ("auto_success_range_from_last_seen", auto_success_range_from_last_seen),
    ]:
        if value is not None and value < 0:
            return make_error_response(f"{name} must be >= 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"actor_name": actor_name}
    for k, v in [
        ("sight_radius", sight_radius),
        ("lose_sight_radius", lose_sight_radius),
        ("peripheral_vision_angle_degrees", peripheral_vision_angle_degrees),
        ("auto_success_range_from_last_seen", auto_success_range_from_last_seen),
        ("detect_neutrals", detect_neutrals),
        ("detect_friendlies", detect_friendlies),
        ("detect_enemies", detect_enemies),
    ]:
        if v is not None:
            payload[k] = v
    try:
        response = unreal.send_command("configure_ai_sense_sight", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"configure_ai_sense_sight error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def set_recast_navmesh_agent(
    agent_radius: Optional[float] = None,
    agent_height: Optional[float] = None,
    agent_max_step_height: Optional[float] = None,
    tile_size_uu: Optional[float] = None,
    max_simplification_error: Optional[float] = None,
) -> Dict[str, Any]:
    """Tune the active ARecastNavMesh actor agent/build parameters.

    Per-instance change; requires a NavMesh build to apply to existing tiles.
    Requires at least one numeric field. Values must be positive
    (or >= 0 for max_simplification_error).
    """
    fields = {
        "agent_radius": agent_radius,
        "agent_height": agent_height,
        "agent_max_step_height": agent_max_step_height,
        "tile_size_uu": tile_size_uu,
        "max_simplification_error": max_simplification_error,
    }
    payload = {k: v for k, v in fields.items() if v is not None}
    if not payload:
        return make_error_response("Provide at least one navmesh agent field to update")
    for name, value in fields.items():
        if value is None:
            continue
        if name == "max_simplification_error":
            if value < 0:
                return make_error_response(f"{name} must be >= 0")
        else:
            if value <= 0:
                return make_error_response(f"{name} must be > 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("set_recast_navmesh_agent", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_recast_navmesh_agent error: {exc}")
        return make_error_response(str(exc))

# W1-G EQS + Crowd Following (UE 5.7)


@mcp.tool()
def create_eqs_query(
    asset_path: str,
    query_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an empty UEnvQuery (EQS Query) DataAsset.

    asset_path: /Game path for the new UEnvQuery asset
    query_name: Optional UEnvQuery::QueryName (defaults to asset_name)
    """
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"asset_path": asset_path}
    if query_name:
        payload["query_name"] = query_name
    try:
        response = unreal.send_command("create_eqs_query", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"create_eqs_query error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def set_crowd_following_enable(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """Attach or remove a UCrowdFollowingComponent on an AAIController.

    actor_name: Editor-world AAIController actor name or label
    enable: True (default) adds the component, False removes it
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command(
            "set_crowd_following_enable",
            {"actor_name": actor_name, "enable": enable},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_crowd_following_enable error: {exc}")
        return make_error_response(str(exc))
