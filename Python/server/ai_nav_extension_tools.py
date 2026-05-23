"""AI / Navigation extensions (Sub-batch L, issue #47) MCP tools (auto-generated scaffold).

Each tool wraps a single C++ handler. The C++ side returns a queued
envelope when the underlying plugin is missing; the wrappers surface that
to the caller via an actionable error envelope.
"""

from typing import Any, Dict

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_string,
    ValidationError,
    make_validation_error_response_from_exception,
)
from utils.responses import make_error_response


def _envelope(name: str, result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return make_error_response(f"Unexpected Unreal response for '{name}'")
    if not result.get("success", False):
        err = result.get("error", "unknown error")
        hint = result.get("hint")
        return make_error_response(f"{name}: {err}" + (f" (hint: {hint})" if hint else ""))
    return result


@mcp.tool()
def add_behavior_tree_node(bt_path: str, node_type: str, parent_node: str = "") -> Dict[str, Any]:
    """add_behavior_tree_node -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(bt_path, "bt_path")
        validate_string(node_type, "node_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_behavior_tree_node", {"bt_path": bt_path, "node_type": node_type, "parent_node": parent_node})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_behavior_tree_node': {e}")
    return _envelope("add_behavior_tree_node", r)


@mcp.tool()
def connect_behavior_tree_nodes(bt_path: str, from_node: str, to_node: str) -> Dict[str, Any]:
    """connect_behavior_tree_nodes -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(bt_path, "bt_path")
        validate_string(from_node, "from_node")
        validate_string(to_node, "to_node")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("connect_behavior_tree_nodes", {"bt_path": bt_path, "from_node": from_node, "to_node": to_node})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'connect_behavior_tree_nodes': {e}")
    return _envelope("connect_behavior_tree_nodes", r)


@mcp.tool()
def create_bt_task(asset_path: str = "/Game/AI", asset_name: str = "BTT_New", base_class: str = "BTTaskNode") -> Dict[str, Any]:
    """create_bt_task -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_bt_task", {"asset_path": asset_path, "asset_name": asset_name, "base_class": base_class})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_bt_task': {e}")
    return _envelope("create_bt_task", r)


@mcp.tool()
def create_bt_service(asset_path: str = "/Game/AI", asset_name: str = "BTS_New") -> Dict[str, Any]:
    """create_bt_service -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_bt_service", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_bt_service': {e}")
    return _envelope("create_bt_service", r)


@mcp.tool()
def create_bt_decorator(asset_path: str = "/Game/AI", asset_name: str = "BTD_New") -> Dict[str, Any]:
    """create_bt_decorator -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_bt_decorator", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_bt_decorator': {e}")
    return _envelope("create_bt_decorator", r)


@mcp.tool()
def set_blackboard_template(controller_actor: str, blackboard_path: str) -> Dict[str, Any]:
    """set_blackboard_template -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(controller_actor, "controller_actor")
        validate_string(blackboard_path, "blackboard_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_blackboard_template", {"controller_actor": controller_actor, "blackboard_path": blackboard_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_blackboard_template': {e}")
    return _envelope("set_blackboard_template", r)


@mcp.tool()
def set_ai_controller_behavior_tree(controller_actor: str, behavior_tree_path: str) -> Dict[str, Any]:
    """set_ai_controller_behavior_tree -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(controller_actor, "controller_actor")
        validate_string(behavior_tree_path, "behavior_tree_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_ai_controller_behavior_tree", {"controller_actor": controller_actor, "behavior_tree_path": behavior_tree_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_ai_controller_behavior_tree': {e}")
    return _envelope("set_ai_controller_behavior_tree", r)


@mcp.tool()
def spawn_run_behavior_tree_node(bt_path: str, target_bt_path: str) -> Dict[str, Any]:
    """spawn_run_behavior_tree_node -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(bt_path, "bt_path")
        validate_string(target_bt_path, "target_bt_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_run_behavior_tree_node", {"bt_path": bt_path, "target_bt_path": target_bt_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_run_behavior_tree_node': {e}")
    return _envelope("spawn_run_behavior_tree_node", r)


@mcp.tool()
def configure_ai_sense_hearing(perception_actor: str, range: float = 1500.0) -> Dict[str, Any]:
    """configure_ai_sense_hearing -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(perception_actor, "perception_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ai_sense_hearing", {"perception_actor": perception_actor, "range": float(range)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ai_sense_hearing': {e}")
    return _envelope("configure_ai_sense_hearing", r)


@mcp.tool()
def configure_ai_sense_damage(perception_actor: str, max_age: float = 5.0) -> Dict[str, Any]:
    """configure_ai_sense_damage -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(perception_actor, "perception_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ai_sense_damage", {"perception_actor": perception_actor, "max_age": float(max_age)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ai_sense_damage': {e}")
    return _envelope("configure_ai_sense_damage", r)


@mcp.tool()
def configure_ai_sense_team(perception_actor: str, detect_friendlies: bool = False, detect_enemies: bool = True) -> Dict[str, Any]:
    """configure_ai_sense_team -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(perception_actor, "perception_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ai_sense_team", {"perception_actor": perception_actor, "detect_friendlies": bool(detect_friendlies), "detect_enemies": bool(detect_enemies)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ai_sense_team': {e}")
    return _envelope("configure_ai_sense_team", r)


@mcp.tool()
def configure_eqs_generator(eqs_path: str, generator_type: str = "SimpleGrid") -> Dict[str, Any]:
    """configure_eqs_generator -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(eqs_path, "eqs_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_eqs_generator", {"eqs_path": eqs_path, "generator_type": generator_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_eqs_generator': {e}")
    return _envelope("configure_eqs_generator", r)


@mcp.tool()
def configure_eqs_test(eqs_path: str, test_type: str = "Distance") -> Dict[str, Any]:
    """configure_eqs_test -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(eqs_path, "eqs_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_eqs_test", {"eqs_path": eqs_path, "test_type": test_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_eqs_test': {e}")
    return _envelope("configure_eqs_test", r)


@mcp.tool()
def set_eqs_debug(enable: bool = True) -> Dict[str, Any]:
    """set_eqs_debug -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_eqs_debug", {"enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_eqs_debug': {e}")
    return _envelope("set_eqs_debug", r)


@mcp.tool()
def set_smart_nav_link(actor_name: str, start_xy: list, end_xy: list) -> Dict[str, Any]:
    """set_smart_nav_link -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_smart_nav_link", {"actor_name": actor_name, "start_xy": start_xy, "end_xy": end_xy})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_smart_nav_link': {e}")
    return _envelope("set_smart_nav_link", r)


@mcp.tool()
def create_nav_area_class(asset_path: str = "/Game/AI", asset_name: str = "NA_Custom") -> Dict[str, Any]:
    """create_nav_area_class -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_nav_area_class", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_nav_area_class': {e}")
    return _envelope("create_nav_area_class", r)


@mcp.tool()
def set_recast_navmesh_details(actor_name: str = "RecastNavMesh-Default", cell_size: float = 19.0, agent_radius: float = 34.0) -> Dict[str, Any]:
    """set_recast_navmesh_details -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_recast_navmesh_details", {"actor_name": actor_name, "cell_size": float(cell_size), "agent_radius": float(agent_radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_recast_navmesh_details': {e}")
    return _envelope("set_recast_navmesh_details", r)


@mcp.tool()
def bridge_mass_entity(scene_id: str = "main", bridge_mode: str = "RepresentSubsystem") -> Dict[str, Any]:
    """bridge_mass_entity -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("bridge_mass_entity", {"scene_id": scene_id, "bridge_mode": bridge_mode})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bridge_mass_entity': {e}")
    return _envelope("bridge_mass_entity", r)


@mcp.tool()
def create_state_tree(asset_path: str = "/Game/AI", asset_name: str = "ST_New") -> Dict[str, Any]:
    """create_state_tree -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_state_tree", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_state_tree': {e}")
    return _envelope("create_state_tree", r)


@mcp.tool()
def add_state_tree_state(state_tree_path: str, state_name: str) -> Dict[str, Any]:
    """add_state_tree_state -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(state_tree_path, "state_tree_path")
        validate_string(state_name, "state_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_state_tree_state", {"state_tree_path": state_tree_path, "state_name": state_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_state_tree_state': {e}")
    return _envelope("add_state_tree_state", r)


@mcp.tool()
def add_state_tree_task(state_tree_path: str, state_name: str, task_type: str = "DebugLog") -> Dict[str, Any]:
    """add_state_tree_task -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(state_tree_path, "state_tree_path")
        validate_string(state_name, "state_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_state_tree_task", {"state_tree_path": state_tree_path, "state_name": state_name, "task_type": task_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_state_tree_task': {e}")
    return _envelope("add_state_tree_task", r)


@mcp.tool()
def set_ai_behavior_tag(actor_name: str, tag: str) -> Dict[str, Any]:
    """set_ai_behavior_tag -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(tag, "tag")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_ai_behavior_tag", {"actor_name": actor_name, "tag": tag})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_ai_behavior_tag': {e}")
    return _envelope("set_ai_behavior_tag", r)


@mcp.tool()
def configure_cognitive_ai_controller(actor_name: str, model_id: str = "gpt-5", temperature: float = 0.7) -> Dict[str, Any]:
    """configure_cognitive_ai_controller -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_cognitive_ai_controller", {"actor_name": actor_name, "model_id": model_id, "temperature": float(temperature)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_cognitive_ai_controller': {e}")
    return _envelope("configure_cognitive_ai_controller", r)
