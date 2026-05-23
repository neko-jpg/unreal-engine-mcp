"""Water System (Sub-batch S, issue #46) MCP tools (auto-generated scaffold).

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
def enable_water_plugin() -> Dict[str, Any]:
    """enable_water_plugin -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("enable_water_plugin", {})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'enable_water_plugin': {e}")
    return _envelope("enable_water_plugin", r)


@mcp.tool()
def spawn_water_body_ocean(actor_name: str = "WaterBodyOcean", scale: float = 1.0) -> Dict[str, Any]:
    """spawn_water_body_ocean -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_water_body_ocean", {"actor_name": actor_name, "scale": float(scale)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_water_body_ocean': {e}")
    return _envelope("spawn_water_body_ocean", r)


@mcp.tool()
def spawn_water_body_lake(actor_name: str = "WaterBodyLake", spline_points: list = []) -> Dict[str, Any]:
    """spawn_water_body_lake -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_water_body_lake", {"actor_name": actor_name, "spline_points": spline_points})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_water_body_lake': {e}")
    return _envelope("spawn_water_body_lake", r)


@mcp.tool()
def spawn_water_body_river(actor_name: str = "WaterBodyRiver", spline_points: list = []) -> Dict[str, Any]:
    """spawn_water_body_river -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_water_body_river", {"actor_name": actor_name, "spline_points": spline_points})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_water_body_river': {e}")
    return _envelope("spawn_water_body_river", r)


@mcp.tool()
def spawn_water_body_custom(actor_name: str = "WaterBodyCustom") -> Dict[str, Any]:
    """spawn_water_body_custom -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_water_body_custom", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_water_body_custom': {e}")
    return _envelope("spawn_water_body_custom", r)


@mcp.tool()
def configure_river_spline(actor_name: str, spline_points: list) -> Dict[str, Any]:
    """configure_river_spline -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_river_spline", {"actor_name": actor_name, "spline_points": spline_points})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_river_spline': {e}")
    return _envelope("configure_river_spline", r)


@mcp.tool()
def set_water_material(actor_name: str, material_path: str) -> Dict[str, Any]:
    """set_water_material -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(material_path, "material_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_water_material", {"actor_name": actor_name, "material_path": material_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_water_material': {e}")
    return _envelope("set_water_material", r)


@mcp.tool()
def configure_water_wave(actor_name: str, asset_path: str = "") -> Dict[str, Any]:
    """configure_water_wave -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_water_wave", {"actor_name": actor_name, "asset_path": asset_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_water_wave': {e}")
    return _envelope("configure_water_wave", r)


@mcp.tool()
def configure_water_flow(actor_name: str, flow_velocity: float = 100.0) -> Dict[str, Any]:
    """configure_water_flow -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_water_flow", {"actor_name": actor_name, "flow_velocity": float(flow_velocity)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_water_flow': {e}")
    return _envelope("configure_water_flow", r)


@mcp.tool()
def configure_buoyancy(actor_name: str, weight: float = 1.0, damping: float = 0.5) -> Dict[str, Any]:
    """configure_buoyancy -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_buoyancy", {"actor_name": actor_name, "weight": float(weight), "damping": float(damping)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_buoyancy': {e}")
    return _envelope("configure_buoyancy", r)


@mcp.tool()
def configure_water_mesh_actor(actor_name: str = "WaterMeshActor", tile_size: float = 2400.0) -> Dict[str, Any]:
    """configure_water_mesh_actor -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_water_mesh_actor", {"actor_name": actor_name, "tile_size": float(tile_size)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_water_mesh_actor': {e}")
    return _envelope("configure_water_mesh_actor", r)


@mcp.tool()
def configure_underwater_post_process(post_process_actor: str = "WaterPostProcess") -> Dict[str, Any]:
    """configure_underwater_post_process -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_underwater_post_process", {"post_process_actor": post_process_actor})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_underwater_post_process': {e}")
    return _envelope("configure_underwater_post_process", r)


@mcp.tool()
def configure_shoreline(actor_name: str, smoothness: float = 0.5) -> Dict[str, Any]:
    """configure_shoreline -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_shoreline", {"actor_name": actor_name, "smoothness": float(smoothness)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_shoreline': {e}")
    return _envelope("configure_shoreline", r)


@mcp.tool()
def configure_water_landscape_carving(landscape_actor: str, enable: bool = True) -> Dict[str, Any]:
    """configure_water_landscape_carving -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(landscape_actor, "landscape_actor")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_water_landscape_carving", {"landscape_actor": landscape_actor, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_water_landscape_carving': {e}")
    return _envelope("configure_water_landscape_carving", r)


@mcp.tool()
def attach_floating_actor(actor_name: str, pontoon_locations: list = []) -> Dict[str, Any]:
    """attach_floating_actor -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("attach_floating_actor", {"actor_name": actor_name, "pontoon_locations": pontoon_locations})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_floating_actor': {e}")
    return _envelope("attach_floating_actor", r)
