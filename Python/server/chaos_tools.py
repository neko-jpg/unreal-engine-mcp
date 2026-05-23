"""Chaos / Physics extensions (Sub-batch Q, issue #51) MCP tools (auto-generated scaffold).

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
def create_collision_channel(channel_name: str, default_response: str = "Block") -> Dict[str, Any]:
    """create_collision_channel -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(channel_name, "channel_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_collision_channel", {"channel_name": channel_name, "default_response": default_response})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_collision_channel': {e}")
    return _envelope("create_collision_channel", r)


@mcp.tool()
def create_object_channel(channel_name: str, default_response: str = "Block") -> Dict[str, Any]:
    """create_object_channel -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(channel_name, "channel_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_object_channel", {"channel_name": channel_name, "default_response": default_response})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_object_channel': {e}")
    return _envelope("create_object_channel", r)


@mcp.tool()
def create_trace_channel(channel_name: str, default_response: str = "Ignore") -> Dict[str, Any]:
    """create_trace_channel -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(channel_name, "channel_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_trace_channel", {"channel_name": channel_name, "default_response": default_response})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_trace_channel': {e}")
    return _envelope("create_trace_channel", r)


@mcp.tool()
def create_geometry_collection(asset_path: str = "/Game/Chaos", asset_name: str = "GC_New", source_mesh: str = "") -> Dict[str, Any]:
    """create_geometry_collection -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_geometry_collection", {"asset_path": asset_path, "asset_name": asset_name, "source_mesh": source_mesh})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_geometry_collection': {e}")
    return _envelope("create_geometry_collection", r)


@mcp.tool()
def fracture_geometry_collection(asset_path: str, fracture_type: str = "Uniform", seed: int = 0) -> Dict[str, Any]:
    """fracture_geometry_collection -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("fracture_geometry_collection", {"asset_path": asset_path, "fracture_type": fracture_type, "seed": int(seed)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'fracture_geometry_collection': {e}")
    return _envelope("fracture_geometry_collection", r)


@mcp.tool()
def create_chaos_field(field_class: str = "RadialFalloff", actor_name: str = "ChaosField") -> Dict[str, Any]:
    """create_chaos_field -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_chaos_field", {"field_class": field_class, "actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_chaos_field': {e}")
    return _envelope("create_chaos_field", r)


@mcp.tool()
def configure_chaos_solver(solver_actor: str = "ChaosSolverActor", sub_steps: int = 1) -> Dict[str, Any]:
    """configure_chaos_solver -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_chaos_solver", {"solver_actor": solver_actor, "sub_steps": int(sub_steps)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_chaos_solver': {e}")
    return _envelope("configure_chaos_solver", r)


@mcp.tool()
def create_chaos_cache(asset_path: str = "/Game/Chaos", asset_name: str = "ChaosCache_New") -> Dict[str, Any]:
    """create_chaos_cache -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_chaos_cache", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_chaos_cache': {e}")
    return _envelope("create_chaos_cache", r)


@mcp.tool()
def create_chaos_vehicle(actor_name: str = "ChaosVehicle", mesh_path: str = "") -> Dict[str, Any]:
    """create_chaos_vehicle -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_chaos_vehicle", {"actor_name": actor_name, "mesh_path": mesh_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_chaos_vehicle': {e}")
    return _envelope("create_chaos_vehicle", r)


@mcp.tool()
def set_vehicle_wheel(actor_name: str, wheel_index: int = 0, wheel_class: str = "ChaosWheel") -> Dict[str, Any]:
    """set_vehicle_wheel -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_vehicle_wheel", {"actor_name": actor_name, "wheel_index": int(wheel_index), "wheel_class": wheel_class})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_vehicle_wheel': {e}")
    return _envelope("set_vehicle_wheel", r)


@mcp.tool()
def set_vehicle_suspension(actor_name: str, wheel_index: int = 0, stiffness: float = 100.0) -> Dict[str, Any]:
    """set_vehicle_suspension -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_vehicle_suspension", {"actor_name": actor_name, "wheel_index": int(wheel_index), "stiffness": float(stiffness)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_vehicle_suspension': {e}")
    return _envelope("set_vehicle_suspension", r)


@mcp.tool()
def set_vehicle_engine_torque(actor_name: str, torque_curve: list = []) -> Dict[str, Any]:
    """set_vehicle_engine_torque -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_vehicle_engine_torque", {"actor_name": actor_name, "torque_curve": torque_curve})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_vehicle_engine_torque': {e}")
    return _envelope("set_vehicle_engine_torque", r)


@mcp.tool()
def set_cloth_settings(skeletal_mesh_path: str, damping: float = 0.5) -> Dict[str, Any]:
    """set_cloth_settings -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(skeletal_mesh_path, "skeletal_mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_cloth_settings", {"skeletal_mesh_path": skeletal_mesh_path, "damping": float(damping)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_cloth_settings': {e}")
    return _envelope("set_cloth_settings", r)


@mcp.tool()
def create_chaos_cloth_asset(asset_path: str = "/Game/Chaos", asset_name: str = "ChaosCloth_New") -> Dict[str, Any]:
    """create_chaos_cloth_asset -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_chaos_cloth_asset", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_chaos_cloth_asset': {e}")
    return _envelope("create_chaos_cloth_asset", r)


@mcp.tool()
def set_groom_physics(groom_path: str, enable: bool = True) -> Dict[str, Any]:
    """set_groom_physics -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(groom_path, "groom_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_groom_physics", {"groom_path": groom_path, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_groom_physics': {e}")
    return _envelope("set_groom_physics", r)


@mcp.tool()
def set_ragdoll(skeletal_actor: str, enable: bool = True) -> Dict[str, Any]:
    """set_ragdoll -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(skeletal_actor, "skeletal_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_ragdoll", {"skeletal_actor": skeletal_actor, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_ragdoll': {e}")
    return _envelope("set_ragdoll", r)


@mcp.tool()
def edit_physics_asset_body(physics_asset_path: str, bone: str, mass: float = 1.0) -> Dict[str, Any]:
    """edit_physics_asset_body -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(physics_asset_path, "physics_asset_path")
        validate_string(bone, "bone")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_physics_asset_body", {"physics_asset_path": physics_asset_path, "bone": bone, "mass": float(mass)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_physics_asset_body': {e}")
    return _envelope("edit_physics_asset_body", r)


@mcp.tool()
def edit_physics_asset_constraint(physics_asset_path: str, constraint_name: str) -> Dict[str, Any]:
    """edit_physics_asset_constraint -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(physics_asset_path, "physics_asset_path")
        validate_string(constraint_name, "constraint_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_physics_asset_constraint", {"physics_asset_path": physics_asset_path, "constraint_name": constraint_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_physics_asset_constraint': {e}")
    return _envelope("edit_physics_asset_constraint", r)


@mcp.tool()
def attach_chaos_visual_debugger(enable: bool = True) -> Dict[str, Any]:
    """attach_chaos_visual_debugger -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("attach_chaos_visual_debugger", {"enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_chaos_visual_debugger': {e}")
    return _envelope("attach_chaos_visual_debugger", r)
