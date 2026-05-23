"""Landscape / Terrain MCP tools (Sub-batch J, issue #43).

23 tools wrapping FEpicUnrealMCPLandscapeCommands (route 25). Each tool sends a
literal command name via unreal.send_command so the route-contract audit picks
the binding up statically.
"""

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
        if hint:
            return make_error_response(f"{name}: {err} (hint: {hint})")
        return make_error_response(f"{name}: {err}")
    return result


@mcp.tool()
def create_landscape(actor_name: str = "Landscape", sections_per_component: int = 1, quads_per_section: int = 63) -> Dict[str, Any]:
    """Spawn ALandscape at world origin and set ComponentSizeQuads."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_landscape", {"actor_name": actor_name, "sections_per_component": int(sections_per_component), "quads_per_section": int(quads_per_section)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_landscape': {e}")
    return _envelope("create_landscape", r)


@mcp.tool()
def set_landscape_size(actor_name: str, width_quads: int, height_quads: int) -> Dict[str, Any]:
    """Queue a Landscape resize (LandscapeEditMode is interactive in 5.7)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_size", {"actor_name": actor_name, "width_quads": int(width_quads), "height_quads": int(height_quads)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_size': {e}")
    return _envelope("set_landscape_size", r)


@mcp.tool()
def set_landscape_section_component(actor_name: str, sections_per_component: int = 1, quads_per_section: int = 63) -> Dict[str, Any]:
    """Queue Landscape section/component tuning."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_section_component", {"actor_name": actor_name, "sections_per_component": int(sections_per_component), "quads_per_section": int(quads_per_section)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_section_component': {e}")
    return _envelope("set_landscape_section_component", r)


@mcp.tool()
def import_landscape_heightmap(actor_name: str, heightmap_path: str) -> Dict[str, Any]:
    """Queue a heightmap import (PNG/RAW). Interactive landscape mode finishes it."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(heightmap_path, "heightmap_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("import_landscape_heightmap", {"actor_name": actor_name, "heightmap_path": heightmap_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'import_landscape_heightmap': {e}")
    return _envelope("import_landscape_heightmap", r)


@mcp.tool()
def export_landscape_heightmap(actor_name: str, output_path: str) -> Dict[str, Any]:
    """Queue a heightmap export."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(output_path, "output_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("export_landscape_heightmap", {"actor_name": actor_name, "output_path": output_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'export_landscape_heightmap': {e}")
    return _envelope("export_landscape_heightmap", r)


def _send_simple(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper for landscape sculpt/edit commands that only need round-trip payload."""
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command(name, payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command '{name}': {e}")
    return _envelope(name, r)


@mcp.tool()
def landscape_sculpt(actor_name: str, brush_radius: float = 100.0, brush_strength: float = 0.5, location_xy: Optional[list] = None) -> Dict[str, Any]:
    """Queue a sculpt brush stroke on a Landscape actor."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_sculpt", {"actor_name": actor_name, "brush_radius": float(brush_radius), "brush_strength": float(brush_strength), "location_xy": location_xy or [0.0, 0.0]})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_sculpt': {e}")
    return _envelope("landscape_sculpt", r)


@mcp.tool()
def landscape_smooth(actor_name: str, brush_radius: float = 200.0, iterations: int = 1) -> Dict[str, Any]:
    """Queue a smooth brush sweep."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_smooth", {"actor_name": actor_name, "brush_radius": float(brush_radius), "iterations": int(iterations)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_smooth': {e}")
    return _envelope("landscape_smooth", r)


@mcp.tool()
def landscape_flatten(actor_name: str, target_height: float = 0.0, brush_radius: float = 200.0) -> Dict[str, Any]:
    """Queue a flatten brush stroke."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_flatten", {"actor_name": actor_name, "target_height": float(target_height), "brush_radius": float(brush_radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_flatten': {e}")
    return _envelope("landscape_flatten", r)


@mcp.tool()
def landscape_ramp(actor_name: str, start_xy: list, end_xy: list, ramp_height: float = 100.0) -> Dict[str, Any]:
    """Queue a ramp tool stroke."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_ramp", {"actor_name": actor_name, "start_xy": start_xy, "end_xy": end_xy, "ramp_height": float(ramp_height)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_ramp': {e}")
    return _envelope("landscape_ramp", r)


@mcp.tool()
def landscape_erosion(actor_name: str, iterations: int = 10, strength: float = 0.5) -> Dict[str, Any]:
    """Queue an erosion brush pass."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_erosion", {"actor_name": actor_name, "iterations": int(iterations), "strength": float(strength)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_erosion': {e}")
    return _envelope("landscape_erosion", r)


@mcp.tool()
def landscape_noise(actor_name: str, frequency: float = 0.05, amplitude: float = 100.0) -> Dict[str, Any]:
    """Queue a noise/displacement brush."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_noise", {"actor_name": actor_name, "frequency": float(frequency), "amplitude": float(amplitude)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_noise': {e}")
    return _envelope("landscape_noise", r)


@mcp.tool()
def create_landscape_paint_layer(actor_name: str, layer_name: str, layer_info_path: str = "") -> Dict[str, Any]:
    """Queue weight-blend paint layer creation."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(layer_name, "layer_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_landscape_paint_layer", {"actor_name": actor_name, "layer_name": layer_name, "layer_info_path": layer_info_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_landscape_paint_layer': {e}")
    return _envelope("create_landscape_paint_layer", r)


@mcp.tool()
def set_landscape_layer_blend(actor_name: str, layer_name: str, weight: float = 1.0) -> Dict[str, Any]:
    """Queue a weight-blend layer adjustment."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(layer_name, "layer_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_layer_blend", {"actor_name": actor_name, "layer_name": layer_name, "weight": float(weight)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_layer_blend': {e}")
    return _envelope("set_landscape_layer_blend", r)


@mcp.tool()
def apply_landscape_material(actor_name: str, material_path: str) -> Dict[str, Any]:
    """Queue UMaterialInterface assignment to ALandscape::LandscapeMaterial."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(material_path, "material_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("apply_landscape_material", {"actor_name": actor_name, "material_path": material_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'apply_landscape_material': {e}")
    return _envelope("apply_landscape_material", r)


@mcp.tool()
def set_landscape_grass_output(actor_name: str, grass_type_path: str = "", density: float = 1.0) -> Dict[str, Any]:
    """Queue Landscape Grass Output configuration."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_grass_output", {"actor_name": actor_name, "grass_type_path": grass_type_path, "density": float(density)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_grass_output': {e}")
    return _envelope("set_landscape_grass_output", r)


@mcp.tool()
def set_landscape_collision(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """Toggle Landscape collision."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_collision", {"actor_name": actor_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_collision': {e}")
    return _envelope("set_landscape_collision", r)


@mcp.tool()
def add_landscape_hole(actor_name: str, location_xy: list, radius: float = 100.0) -> Dict[str, Any]:
    """Queue a hole / cave opening on the Landscape."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_landscape_hole", {"actor_name": actor_name, "location_xy": location_xy, "radius": float(radius)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_landscape_hole': {e}")
    return _envelope("add_landscape_hole", r)


@mcp.tool()
def add_landscape_spline(actor_name: str, points: list, segment_length: float = 256.0) -> Dict[str, Any]:
    """Queue a ULandscapeSplinesComponent spline addition."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_landscape_spline", {"actor_name": actor_name, "points": points, "segment_length": float(segment_length)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_landscape_spline': {e}")
    return _envelope("add_landscape_spline", r)


@mcp.tool()
def add_road_spline(actor_name: str, points: list, road_mesh_path: str = "", road_width: float = 600.0) -> Dict[str, Any]:
    """Queue a road spline (road mesh swept along ULandscapeSplinesComponent)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_road_spline", {"actor_name": actor_name, "points": points, "road_mesh_path": road_mesh_path, "road_width": float(road_width)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_road_spline': {e}")
    return _envelope("add_road_spline", r)


@mcp.tool()
def carve_river_terrain(actor_name: str, water_body_actor: str = "", carve_depth: float = 200.0) -> Dict[str, Any]:
    """Queue a river carve using Water Brush Manager (Sub-batch S)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("carve_river_terrain", {"actor_name": actor_name, "water_body_actor": water_body_actor, "carve_depth": float(carve_depth)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'carve_river_terrain': {e}")
    return _envelope("carve_river_terrain", r)


@mcp.tool()
def attach_landscape_rvt(actor_name: str, rvt_asset_path: str) -> Dict[str, Any]:
    """Queue an RVT asset attach (ALandscape::RuntimeVirtualTextures)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(rvt_asset_path, "rvt_asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("attach_landscape_rvt", {"actor_name": actor_name, "rvt_asset_path": rvt_asset_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_landscape_rvt': {e}")
    return _envelope("attach_landscape_rvt", r)


@mcp.tool()
def set_landscape_nanite(actor_name: str, enable: bool = True) -> Dict[str, Any]:
    """Toggle ALandscape::bEnableNanite."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_nanite", {"actor_name": actor_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_nanite': {e}")
    return _envelope("set_landscape_nanite", r)


@mcp.tool()
def set_landscape_world_partition(actor_name: str, grid_size: int = 4) -> Dict[str, Any]:
    """Queue World Partition landscape splitting."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_world_partition", {"actor_name": actor_name, "grid_size": int(grid_size)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_world_partition': {e}")
    return _envelope("set_landscape_world_partition", r)