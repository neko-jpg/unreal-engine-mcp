"""Animation / Skeletal / Rigging MCP tools (Sub-batch K, issue #48)."""

from typing import Any, Dict, Optional

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
def create_skeleton_asset(asset_path: str = "/Game/Anim", asset_name: str = "SKEL_New") -> Dict[str, Any]:
    """Create a USkeleton asset via USkeletonFactory."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_skeleton_asset", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_skeleton_asset': {e}")
    return _envelope("create_skeleton_asset", r)


@mcp.tool()
def create_physics_asset(asset_path: str = "/Game/Anim", asset_name: str = "PHYS_New") -> Dict[str, Any]:
    """Create a UPhysicsAsset via UPhysicsAssetFactory."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_physics_asset", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_physics_asset': {e}")
    return _envelope("create_physics_asset", r)


@mcp.tool()
def add_anim_graph_node(anim_bp_path: str, node_type: str, location_x: float = 0.0, location_y: float = 0.0) -> Dict[str, Any]:
    """Queue an AnimGraph node insertion."""
    try:
        validate_string(anim_bp_path, "anim_bp_path")
        validate_string(node_type, "node_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_anim_graph_node", {"anim_bp_path": anim_bp_path, "node_type": node_type, "location_x": float(location_x), "location_y": float(location_y)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_anim_graph_node': {e}")
    return _envelope("add_anim_graph_node", r)


@mcp.tool()
def create_anim_state_machine(anim_bp_path: str, graph_name: str = "NewStateMachine") -> Dict[str, Any]:
    """Queue State Machine creation."""
    try:
        validate_string(anim_bp_path, "anim_bp_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_anim_state_machine", {"anim_bp_path": anim_bp_path, "graph_name": graph_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_anim_state_machine': {e}")
    return _envelope("create_anim_state_machine", r)


@mcp.tool()
def add_anim_state(anim_bp_path: str, state_machine: str, state_name: str, asset_path: str = "") -> Dict[str, Any]:
    """Queue State node addition."""
    try:
        validate_string(anim_bp_path, "anim_bp_path")
        validate_string(state_machine, "state_machine")
        validate_string(state_name, "state_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_anim_state", {"anim_bp_path": anim_bp_path, "state_machine": state_machine, "state_name": state_name, "asset_path": asset_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_anim_state': {e}")
    return _envelope("add_anim_state", r)


@mcp.tool()
def create_anim_transition_rule(anim_bp_path: str, from_state: str, to_state: str, condition: str = "true") -> Dict[str, Any]:
    """Queue Transition rule creation."""
    try:
        validate_string(anim_bp_path, "anim_bp_path")
        validate_string(from_state, "from_state")
        validate_string(to_state, "to_state")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_anim_transition_rule", {"anim_bp_path": anim_bp_path, "from_state": from_state, "to_state": to_state, "condition": condition})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_anim_transition_rule': {e}")
    return _envelope("create_anim_transition_rule", r)


@mcp.tool()
def create_aim_offset(asset_path: str = "/Game/Anim", asset_name: str = "AO_New", skeleton_path: str = "") -> Dict[str, Any]:
    """Queue UAimOffsetBlendSpace asset creation."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_aim_offset", {"asset_path": asset_path, "asset_name": asset_name, "skeleton_path": skeleton_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_aim_offset': {e}")
    return _envelope("create_aim_offset", r)


@mcp.tool()
def add_notify_state(anim_sequence_path: str, notify_state_class: str, start_time: float = 0.0, duration: float = 0.5) -> Dict[str, Any]:
    """Queue AnimNotifyState insertion."""
    try:
        validate_string(anim_sequence_path, "anim_sequence_path")
        validate_string(notify_state_class, "notify_state_class")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_notify_state", {"anim_sequence_path": anim_sequence_path, "notify_state_class": notify_state_class, "start_time": float(start_time), "duration": float(duration)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_notify_state': {e}")
    return _envelope("add_notify_state", r)


@mcp.tool()
def set_retarget_manager(
    skeleton_path: str,
    rig_bp_path: str = "",
    rig_mode: str = "Humanoid",
    preview_mesh: str = "",
) -> Dict[str, Any]:
    """Persist the requested retarget manager configuration on a USkeleton.

    234-stubs W1 (#79) Part 1: this handler now runs the C++ promotion path,
    writing MCP-namespaced metadata onto the skeleton's package so an
    IKRigEditor follow-up can apply the chosen rig mode.
    """
    try:
        validate_string(skeleton_path, "skeleton_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {
        "skeleton_path": skeleton_path,
        "rig_mode": rig_mode,
    }
    if rig_bp_path:
        payload["rig_bp_path"] = rig_bp_path
    if preview_mesh:
        payload["preview_mesh"] = preview_mesh
    try:
        r = u.send_command("set_retarget_manager", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_retarget_manager': {e}")
    return _envelope("set_retarget_manager", r)




@mcp.tool()
def create_ik_rig(asset_path: str = "/Game/Anim", asset_name: str = "IKRig_New", skeletal_mesh_path: str = "") -> Dict[str, Any]:
    """Queue UIKRigDefinition asset creation."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_ik_rig", {"asset_path": asset_path, "asset_name": asset_name, "skeletal_mesh_path": skeletal_mesh_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_ik_rig': {e}")
    return _envelope("create_ik_rig", r)


@mcp.tool()
def add_ik_goal(ik_rig_path: str, goal_name: str, bone: str) -> Dict[str, Any]:
    """Queue IK goal addition."""
    try:
        validate_string(ik_rig_path, "ik_rig_path")
        validate_string(goal_name, "goal_name")
        validate_string(bone, "bone")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_ik_goal", {"ik_rig_path": ik_rig_path, "goal_name": goal_name, "bone": bone})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_ik_goal': {e}")
    return _envelope("add_ik_goal", r)


@mcp.tool()
def add_ik_solver(ik_rig_path: str, solver_type: str = "FBIK") -> Dict[str, Any]:
    """Queue IK solver addition."""
    try:
        validate_string(ik_rig_path, "ik_rig_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_ik_solver", {"ik_rig_path": ik_rig_path, "solver_type": solver_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_ik_solver': {e}")
    return _envelope("add_ik_solver", r)


@mcp.tool()
def create_ik_retargeter(asset_path: str = "/Game/Anim", asset_name: str = "IKRetarget_New", source_ik_rig: str = "", target_ik_rig: str = "") -> Dict[str, Any]:
    """Queue UIKRetargeter asset creation."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_ik_retargeter", {"asset_path": asset_path, "asset_name": asset_name, "source_ik_rig": source_ik_rig, "target_ik_rig": target_ik_rig})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_ik_retargeter': {e}")
    return _envelope("create_ik_retargeter", r)


@mcp.tool()
def set_retarget_chain(ik_rig_path: str, chain_name: str, start_bone: str, end_bone: str) -> Dict[str, Any]:
    """Queue retarget chain definition."""
    try:
        validate_string(ik_rig_path, "ik_rig_path")
        validate_string(chain_name, "chain_name")
        validate_string(start_bone, "start_bone")
        validate_string(end_bone, "end_bone")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_retarget_chain", {"ik_rig_path": ik_rig_path, "chain_name": chain_name, "start_bone": start_bone, "end_bone": end_bone})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_retarget_chain': {e}")
    return _envelope("set_retarget_chain", r)


@mcp.tool()
def create_control_rig(asset_path: str = "/Game/Anim", asset_name: str = "CR_New", skeleton_path: str = "") -> Dict[str, Any]:
    """Queue Control Rig blueprint creation."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_control_rig", {"asset_path": asset_path, "asset_name": asset_name, "skeleton_path": skeleton_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_control_rig': {e}")
    return _envelope("create_control_rig", r)


@mcp.tool()
def add_control_rig_control(control_rig_path: str, control_name: str, control_type: str = "Transform", bone: str = "") -> Dict[str, Any]:
    """Queue Control addition."""
    try:
        validate_string(control_rig_path, "control_rig_path")
        validate_string(control_name, "control_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_control_rig_control", {"control_rig_path": control_rig_path, "control_name": control_name, "control_type": control_type, "bone": bone})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_control_rig_control': {e}")
    return _envelope("add_control_rig_control", r)


@mcp.tool()
def add_control_rig_bone(control_rig_path: str, bone_name: str, parent_bone: str = "") -> Dict[str, Any]:
    """Queue Bone addition."""
    try:
        validate_string(control_rig_path, "control_rig_path")
        validate_string(bone_name, "bone_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_control_rig_bone", {"control_rig_path": control_rig_path, "bone_name": bone_name, "parent_bone": parent_bone})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_control_rig_bone': {e}")
    return _envelope("add_control_rig_bone", r)


@mcp.tool()
def set_control_rig_constraint(control_rig_path: str, control_name: str, constraint_type: str = "Parent", target: str = "") -> Dict[str, Any]:
    """Queue Constraint setup."""
    try:
        validate_string(control_rig_path, "control_rig_path")
        validate_string(control_name, "control_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_control_rig_constraint", {"control_rig_path": control_rig_path, "control_name": control_name, "constraint_type": constraint_type, "target": target})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_control_rig_constraint': {e}")
    return _envelope("set_control_rig_constraint", r)


@mcp.tool()
def sequencer_control_rig_track(level_sequence_path: str, skeletal_actor: str, control_rig_path: str) -> Dict[str, Any]:
    """Queue Sequencer Control Rig track binding."""
    try:
        validate_string(level_sequence_path, "level_sequence_path")
        validate_string(skeletal_actor, "skeletal_actor")
        validate_string(control_rig_path, "control_rig_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("sequencer_control_rig_track", {"level_sequence_path": level_sequence_path, "skeletal_actor": skeletal_actor, "control_rig_path": control_rig_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'sequencer_control_rig_track': {e}")
    return _envelope("sequencer_control_rig_track", r)


@mcp.tool()
def set_facial_animation(
    skeletal_mesh_path: str,
    anim_sequence_path: str = "",
    curve_name: str = "",
    weight: float = 0.0,
    rig_type: str = "MetaHumanFacial",
) -> Dict[str, Any]:
    """Persist a facial animation curve weight onto a USkeleton's package metadata.

    234-stubs W1 (#79) Part 1: this handler is now executed in C++ via
    `AnimMetaPersist` so the requested curve/weight survives editor restart and
    can be replayed by the MetaHuman / facial follow-up.
    Legacy callers may still pass ``anim_sequence_path`` (forwarded verbatim).
    """
    try:
        validate_string(skeletal_mesh_path, "skeletal_mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"skeleton_path": skeletal_mesh_path}
    if anim_sequence_path:
        payload["anim_sequence_path"] = anim_sequence_path
    if curve_name:
        payload["curve_name"] = curve_name
    payload["weight"] = float(weight)
    payload["rig_type"] = rig_type
    try:
        r = u.send_command("set_facial_animation", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_facial_animation': {e}")
    return _envelope("set_facial_animation", r)




@mcp.tool()
def set_morph_target(skeletal_mesh_path: str, morph_target: str, weight: float = 1.0) -> Dict[str, Any]:
    """Queue morph-target weight set."""
    try:
        validate_string(skeletal_mesh_path, "skeletal_mesh_path")
        validate_string(morph_target, "morph_target")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_morph_target", {"skeletal_mesh_path": skeletal_mesh_path, "morph_target": morph_target, "weight": float(weight)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_morph_target': {e}")
    return _envelope("set_morph_target", r)


@mcp.tool()
def connect_metahuman(metahuman_blueprint_path: str, target_actor: str = "") -> Dict[str, Any]:
    """Queue MetaHuman blueprint connection."""
    try:
        validate_string(metahuman_blueprint_path, "metahuman_blueprint_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("connect_metahuman", {"metahuman_blueprint_path": metahuman_blueprint_path, "target_actor": target_actor})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'connect_metahuman': {e}")
    return _envelope("connect_metahuman", r)
