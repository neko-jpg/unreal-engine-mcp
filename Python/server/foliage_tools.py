"""Foliage / Vegetation (Sub-batch N, issue #44) MCP tools (auto-generated scaffold).

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
def create_foliage_type(asset_path: str = "/Game/Foliage", asset_name: str = "Foliage_New") -> Dict[str, Any]:
    """create_foliage_type -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_foliage_type", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_foliage_type': {e}")
    return _envelope("create_foliage_type", r)


@mcp.tool()
def register_static_mesh_foliage(foliage_type_path: str, static_mesh_path: str) -> Dict[str, Any]:
    """register_static_mesh_foliage -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
        validate_string(static_mesh_path, "static_mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("register_static_mesh_foliage", {"foliage_type_path": foliage_type_path, "static_mesh_path": static_mesh_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'register_static_mesh_foliage': {e}")
    return _envelope("register_static_mesh_foliage", r)


@mcp.tool()
def register_actor_foliage(foliage_type_path: str, actor_class_path: str) -> Dict[str, Any]:
    """register_actor_foliage -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
        validate_string(actor_class_path, "actor_class_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("register_actor_foliage", {"foliage_type_path": foliage_type_path, "actor_class_path": actor_class_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'register_actor_foliage': {e}")
    return _envelope("register_actor_foliage", r)


@mcp.tool()
def foliage_paint(foliage_type_path: str, location_xyz: list, radius: float = 500.0) -> Dict[str, Any]:
    """foliage_paint -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("foliage_paint", {"foliage_type_path": foliage_type_path, "location_xyz": location_xyz, "radius": float(radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'foliage_paint': {e}")
    return _envelope("foliage_paint", r)


@mcp.tool()
def foliage_erase(foliage_type_path: str, location_xyz: list, radius: float = 500.0) -> Dict[str, Any]:
    """foliage_erase -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("foliage_erase", {"foliage_type_path": foliage_type_path, "location_xyz": location_xyz, "radius": float(radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'foliage_erase': {e}")
    return _envelope("foliage_erase", r)


@mcp.tool()
def set_foliage_density(foliage_type_path: str, density: float = 1.0) -> Dict[str, Any]:
    """set_foliage_density -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_density", {"foliage_type_path": foliage_type_path, "density": float(density)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_density': {e}")
    return _envelope("set_foliage_density", r)


@mcp.tool()
def set_foliage_scale_range(foliage_type_path: str, min_scale: float = 0.9, max_scale: float = 1.1) -> Dict[str, Any]:
    """set_foliage_scale_range -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_scale_range", {"foliage_type_path": foliage_type_path, "min_scale": float(min_scale), "max_scale": float(max_scale)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_scale_range': {e}")
    return _envelope("set_foliage_scale_range", r)


@mcp.tool()
def set_foliage_random_yaw(foliage_type_path: str, enable: bool = True) -> Dict[str, Any]:
    """set_foliage_random_yaw -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_random_yaw", {"foliage_type_path": foliage_type_path, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_random_yaw': {e}")
    return _envelope("set_foliage_random_yaw", r)


@mcp.tool()
def set_foliage_align_to_normal(foliage_type_path: str, enable: bool = True) -> Dict[str, Any]:
    """set_foliage_align_to_normal -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_align_to_normal", {"foliage_type_path": foliage_type_path, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_align_to_normal': {e}")
    return _envelope("set_foliage_align_to_normal", r)


@mcp.tool()
def set_foliage_cull_distance(foliage_type_path: str, start: float = 5000.0, end: float = 10000.0) -> Dict[str, Any]:
    """set_foliage_cull_distance -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_cull_distance", {"foliage_type_path": foliage_type_path, "start": float(start), "end": float(end)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_cull_distance': {e}")
    return _envelope("set_foliage_cull_distance", r)


@mcp.tool()
def set_foliage_lod(foliage_type_path: str, screen_size_overrides: list = []) -> Dict[str, Any]:
    """set_foliage_lod -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_lod", {"foliage_type_path": foliage_type_path, "screen_size_overrides": screen_size_overrides})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_lod': {e}")
    return _envelope("set_foliage_lod", r)


@mcp.tool()
def create_procedural_foliage_spawner(asset_path: str = "/Game/Foliage", asset_name: str = "PFS_New") -> Dict[str, Any]:
    """create_procedural_foliage_spawner -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_procedural_foliage_spawner", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_procedural_foliage_spawner': {e}")
    return _envelope("create_procedural_foliage_spawner", r)


@mcp.tool()
def create_procedural_foliage_volume(actor_name: str = "ProceduralFoliageVolume") -> Dict[str, Any]:
    """create_procedural_foliage_volume -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_procedural_foliage_volume", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_procedural_foliage_volume': {e}")
    return _envelope("create_procedural_foliage_volume", r)


@mcp.tool()
def set_procedural_foliage_seed(actor_name: str, seed: int = 1) -> Dict[str, Any]:
    """set_procedural_foliage_seed -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_procedural_foliage_seed", {"actor_name": actor_name, "seed": int(seed)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_procedural_foliage_seed': {e}")
    return _envelope("set_procedural_foliage_seed", r)


@mcp.tool()
def spawn_biome_foliage(biome: str, origin_xyz: list) -> Dict[str, Any]:
    """spawn_biome_foliage -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(biome, "biome")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_biome_foliage", {"biome": biome, "origin_xyz": origin_xyz})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_biome_foliage': {e}")
    return _envelope("spawn_biome_foliage", r)


@mcp.tool()
def create_grass_type(asset_path: str = "/Game/Foliage", asset_name: str = "Grass_New") -> Dict[str, Any]:
    """create_grass_type -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_grass_type", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_grass_type': {e}")
    return _envelope("create_grass_type", r)


@mcp.tool()
def bind_landscape_grass(landscape_actor: str, grass_type_path: str) -> Dict[str, Any]:
    """bind_landscape_grass -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(landscape_actor, "landscape_actor")
        validate_string(grass_type_path, "grass_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("bind_landscape_grass", {"landscape_actor": landscape_actor, "grass_type_path": grass_type_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bind_landscape_grass': {e}")
    return _envelope("bind_landscape_grass", r)


@mcp.tool()
def set_foliage_nanite(foliage_type_path: str, enable: bool = True) -> Dict[str, Any]:
    """set_foliage_nanite -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_nanite", {"foliage_type_path": foliage_type_path, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_nanite': {e}")
    return _envelope("set_foliage_nanite", r)


@mcp.tool()
def set_foliage_wind(foliage_type_path: str, wind_actor: str = "") -> Dict[str, Any]:
    """set_foliage_wind -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(foliage_type_path, "foliage_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_foliage_wind", {"foliage_type_path": foliage_type_path, "wind_actor": wind_actor})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_foliage_wind': {e}")
    return _envelope("set_foliage_wind", r)


@mcp.tool()
def configure_pivot_painter(mesh_path: str, wind_strength: float = 1.0) -> Dict[str, Any]:
    """configure_pivot_painter -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(mesh_path, "mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_pivot_painter", {"mesh_path": mesh_path, "wind_strength": float(wind_strength)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_pivot_painter': {e}")
    return _envelope("configure_pivot_painter", r)
