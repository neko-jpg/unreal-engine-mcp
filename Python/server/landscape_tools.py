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
def set_landscape_size(
    actor_name: str = "",
    width_quads: int = 0,
    height_quads: int = 0,
    sections_per_component=None,
    quads_per_section=None,
    component_size_quads=None,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a requested Landscape size on the resolved ALandscape actor.

    234-stubs W1 (#80) Part 1: the C++ handler now wraps the change in
    FMCPScopedTransaction and writes MCP-namespaced UPackage::SetMetaData
    keys so the requested size survives editor restart.
    """
    payload: Dict[str, Any] = {}
    if actor_name:
        try:
            validate_string(actor_name, "actor_name")
        except ValidationError as e:
            return make_validation_error_response_from_exception(e)
        payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    if sections_per_component is not None: payload["sections_per_component"] = int(sections_per_component)
    if quads_per_section is not None: payload["quads_per_section"] = int(quads_per_section)
    if component_size_quads is not None: payload["component_size_quads"] = int(component_size_quads)
    if width_quads: payload.setdefault("width_quads", int(width_quads))
    if height_quads: payload.setdefault("height_quads", int(height_quads))
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_size", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_size': {e}")
    return _envelope("set_landscape_size", r)


@mcp.tool()
def set_landscape_section_component(
    actor_name: str = "",
    sections_per_component: int = 1,
    quads_per_section: int = 63,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Apply Landscape NumSubsections / SubsectionSizeQuads on the resolved actor.

    234-stubs W1 (#80) Part 2: the C++ handler now writes both ALandscape
    properties directly inside FMCPScopedTransaction and persists them in
    MCP metadata.
    """
    payload: Dict[str, Any] = {
        "sections_per_component": int(sections_per_component),
        "quads_per_section": int(quads_per_section),
    }
    if actor_name:
        try:
            validate_string(actor_name, "actor_name")
        except ValidationError as e:
            return make_validation_error_response_from_exception(e)
        payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_section_component", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_section_component': {e}")
    return _envelope("set_landscape_section_component", r)


@mcp.tool()
def import_landscape_heightmap(
    actor_name: str = "",
    heightmap_path: str = "",
    *,
    mcp_id: str = "",
    format: str = "png",
    scale: float = 1.0,
) -> Dict[str, Any]:
    """Persist a heightmap import request on the resolved ALandscape.

    234-stubs W1 (#80) Part 2: live import requires LandscapeEditMode in 5.7;
    the C++ handler records the requested path + format on MCP metadata
    inside FMCPScopedTransaction so the wave-close replay can apply it.
    """
    try:
        validate_string(heightmap_path, "heightmap_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload = {"heightmap_path": heightmap_path, "format": format, "scale": float(scale)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("import_landscape_heightmap", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'import_landscape_heightmap': {e}")
    return _envelope("import_landscape_heightmap", r)


@mcp.tool()
def export_landscape_heightmap(
    actor_name: str = "",
    output_path: str = "",
    *,
    mcp_id: str = "",
    format: str = "png",
) -> Dict[str, Any]:
    """Persist a heightmap export request on the resolved ALandscape."""
    try:
        validate_string(output_path, "output_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload = {"output_path": output_path, "format": format}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("export_landscape_heightmap", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'export_landscape_heightmap': {e}")
    return _envelope("export_landscape_heightmap", r)


@mcp.tool()
def landscape_sculpt(
    actor_name: str = "",
    brush_radius: float = 100.0,
    brush_strength: float = 0.5,
    location_xy: Optional[list] = None,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a sculpt brush stroke on the resolved ALandscape.

    234-stubs W1 (#80) Part 3: live brush strokes need LandscapeEditMode in
    5.7; the C++ handler records the brush parameters on MCP metadata
    inside FMCPScopedTransaction so the wave-close replay can apply them.
    """
    payload: Dict[str, Any] = {
        "brush_radius": float(brush_radius),
        "brush_strength": float(brush_strength),
        # Always echo location_xy so tooling can rely on its presence.
        "location_xy": [float(location_xy[0]), float(location_xy[1])] if (location_xy and len(location_xy) >= 2) else [0.0, 0.0],
    }
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_sculpt", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_sculpt': {e}")
    return _envelope("landscape_sculpt", r)


@mcp.tool()
def landscape_smooth(
    actor_name: str = "",
    brush_radius: float = 200.0,
    iterations: int = 1,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a smooth brush spec on the resolved ALandscape."""
    payload: Dict[str, Any] = {"brush_radius": float(brush_radius), "iterations": int(iterations)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_smooth", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_smooth': {e}")
    return _envelope("landscape_smooth", r)


@mcp.tool()
def landscape_flatten(
    actor_name: str = "",
    target_height: float = 0.0,
    brush_radius: float = 200.0,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a flatten brush spec on the resolved ALandscape."""
    payload: Dict[str, Any] = {"target_height": float(target_height), "brush_radius": float(brush_radius)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_flatten", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_flatten': {e}")
    return _envelope("landscape_flatten", r)


@mcp.tool()
def landscape_ramp(
    actor_name: str = "",
    start_xy: Optional[list] = None,
    end_xy: Optional[list] = None,
    ramp_height: float = 100.0,
    *,
    mcp_id: str = "",
    ramp_width: float = 200.0,
) -> Dict[str, Any]:
    """Persist a ramp spec (start_xy / end_xy / ramp_height) on the resolved ALandscape."""
    if not start_xy or len(start_xy) < 2:
        return make_error_response("landscape_ramp: 'start_xy' must be [x, y]")
    if not end_xy or len(end_xy) < 2:
        return make_error_response("landscape_ramp: 'end_xy' must be [x, y]")
    payload: Dict[str, Any] = {
        "start_xy": [float(start_xy[0]), float(start_xy[1])],
        "end_xy": [float(end_xy[0]), float(end_xy[1])],
        "ramp_height": float(ramp_height),
        "ramp_width": float(ramp_width),
    }
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_ramp", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_ramp': {e}")
    return _envelope("landscape_ramp", r)


@mcp.tool()
def landscape_erosion(
    actor_name: str = "",
    iterations: int = 10,
    strength: float = 0.5,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist an erosion spec on the resolved ALandscape."""
    payload: Dict[str, Any] = {"iterations": int(iterations), "strength": float(strength)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_erosion", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_erosion': {e}")
    return _envelope("landscape_erosion", r)


@mcp.tool()
def landscape_noise(
    actor_name: str = "",
    frequency: float = 0.05,
    amplitude: float = 100.0,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a noise/displacement brush spec on the resolved ALandscape."""
    payload: Dict[str, Any] = {"frequency": float(frequency), "amplitude": float(amplitude)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("landscape_noise", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'landscape_noise': {e}")
    return _envelope("landscape_noise", r)


@mcp.tool()
def create_landscape_paint_layer(
    actor_name: str = "",
    layer_name: str = "",
    layer_info_path: str = "",
    *,
    mcp_id: str = "",
    blend_mode: str = "WeightBlend",
) -> Dict[str, Any]:
    """Persist a weight-blend paint layer spec on the resolved ALandscape."""
    try:
        validate_string(layer_name, "layer_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload = {"layer_name": layer_name, "blend_mode": blend_mode}
    if layer_info_path: payload["layer_info_path"] = layer_info_path
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_landscape_paint_layer", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_landscape_paint_layer': {e}")
    return _envelope("create_landscape_paint_layer", r)


@mcp.tool()
def set_landscape_layer_blend(
    actor_name: str = "",
    layer_name: str = "",
    weight: float = 1.0,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a paint-layer blend weight on the resolved ALandscape.

    234-stubs W1 (#80) Part 2: the C++ handler clamps weight to [0,1] and
    surfaces a weight_clamped flag in the response.
    """
    try:
        validate_string(layer_name, "layer_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload = {"layer_name": layer_name, "weight": float(weight)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_layer_blend", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_layer_blend': {e}")
    return _envelope("set_landscape_layer_blend", r)


@mcp.tool()
def apply_landscape_material(
    actor_name: str = "",
    material_path: str = "",
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Set ALandscape::LandscapeMaterial on the resolved actor.

    234-stubs W1 (#80) Part 1: the C++ handler loads the UMaterialInterface
    and assigns it inside FMCPScopedTransaction.
    """
    if not material_path:
        return make_error_response("apply_landscape_material: material_path is required")
    try:
        validate_string(material_path, "material_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload: Dict[str, Any] = {"material_path": material_path}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("apply_landscape_material", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'apply_landscape_material': {e}")
    return _envelope("apply_landscape_material", r)


@mcp.tool()
def set_landscape_grass_output(
    actor_name: str = "",
    *,
    grass_type_path: str = "",
    mcp_id: str = "",
    layer_name: str = "",
    density: float = 1.0,
) -> Dict[str, Any]:
    """Attach a ULandscapeGrassType to the resolved ALandscape."""
    if not grass_type_path:
        return make_error_response("set_landscape_grass_output: grass_type_path is required")
    try:
        validate_string(grass_type_path, "grass_type_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload: Dict[str, Any] = {"grass_type_path": grass_type_path, "density": float(density)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    if layer_name: payload["layer_name"] = layer_name
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_grass_output", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_grass_output': {e}")
    return _envelope("set_landscape_grass_output", r)


@mcp.tool()
def set_landscape_collision(
    actor_name: str = "",
    enable: bool = True,
    mcp_id: str = "",
    collision_mip_level=None,
    simple_collision_mip_level=None,
    generate_overlap_events=None,
) -> Dict[str, Any]:
    """Apply collision settings on the resolved ALandscape."""
    payload: Dict[str, Any] = {"enable": bool(enable)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    if collision_mip_level is not None: payload["collision_mip_level"] = int(collision_mip_level)
    if simple_collision_mip_level is not None: payload["simple_collision_mip_level"] = int(simple_collision_mip_level)
    if generate_overlap_events is not None: payload["generate_overlap_events"] = bool(generate_overlap_events)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_collision", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_collision': {e}")
    return _envelope("set_landscape_collision", r)


@mcp.tool()
def add_landscape_hole(
    actor_name: str = "",
    location_xy: Optional[list] = None,
    radius: float = 100.0,
    mcp_id: str = "",
    shape: str = "circle",
    x=None, y=None, width=None, height=None,
) -> Dict[str, Any]:
    """Record a landscape hole shape on the resolved ALandscape."""
    payload: Dict[str, Any] = {"shape": shape, "radius": float(radius)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    if location_xy and len(location_xy) >= 2:
        payload.setdefault("x", float(location_xy[0]))
        payload.setdefault("y", float(location_xy[1]))
    if x is not None: payload["x"] = float(x)
    if y is not None: payload["y"] = float(y)
    if width is not None: payload["width"] = float(width)
    if height is not None: payload["height"] = float(height)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_landscape_hole", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_landscape_hole': {e}")
    return _envelope("add_landscape_hole", r)


@mcp.tool()
def add_landscape_spline(
    actor_name: str = "",
    points: Optional[list] = None,
    segment_length: float = 256.0,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a landscape spline spec (>=2 points) on the resolved ALandscape."""
    if not points or len(points) < 2:
        return make_error_response("add_landscape_spline: 'points' must have >= 2 entries")
    payload = {"points": list(points), "segment_length": float(segment_length)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_landscape_spline", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_landscape_spline': {e}")
    return _envelope("add_landscape_spline", r)


@mcp.tool()
def add_road_spline(
    actor_name: str = "",
    points: Optional[list] = None,
    road_mesh_path: str = "",
    road_width: float = 600.0,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Persist a road spline spec on the resolved ALandscape.

    234-stubs W1 (#80) Part 2: the C++ handler attempts to resolve the
    optional road mesh via StaticLoadObject and surfaces a mesh_resolved
    flag in the response.
    """
    if not points or len(points) < 2:
        return make_error_response("add_road_spline: 'points' must have >= 2 entries")
    payload = {"points": list(points), "road_width": float(road_width)}
    if road_mesh_path: payload["road_mesh_path"] = road_mesh_path
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_road_spline", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_road_spline': {e}")
    return _envelope("add_road_spline", r)


@mcp.tool()
def carve_river_terrain(
    actor_name: str = "",
    water_body_actor: str = "",
    carve_depth: float = 200.0,
    *,
    mcp_id: str = "",
    bank_slope: float = 0.0,
) -> Dict[str, Any]:
    """Persist a river-carve spec on the resolved ALandscape."""
    payload = {
        "water_body_actor": water_body_actor,
        "carve_depth": float(carve_depth),
        "bank_slope": float(bank_slope),
    }
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("carve_river_terrain", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'carve_river_terrain': {e}")
    return _envelope("carve_river_terrain", r)


@mcp.tool()
def attach_landscape_rvt(
    actor_name: str = "",
    rvt_asset_path: str = "",
    *,
    rvt_path: str = "",
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Attach a URuntimeVirtualTexture to ALandscape::RuntimeVirtualTextures.

    Accepts either `rvt_path` (new) or `rvt_asset_path` (legacy).
    """
    effective = rvt_path or rvt_asset_path
    if not effective:
        return make_error_response("attach_landscape_rvt: rvt_path is required")
    try:
        validate_string(effective, "rvt_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    payload: Dict[str, Any] = {"rvt_path": effective, "rvt_asset_path": effective}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("attach_landscape_rvt", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'attach_landscape_rvt': {e}")
    return _envelope("attach_landscape_rvt", r)


@mcp.tool()
def set_landscape_nanite(
    actor_name: str = "",
    enable: bool = True,
    *,
    mcp_id: str = "",
) -> Dict[str, Any]:
    """Toggle ALandscape::bEnableNanite on the resolved actor."""
    payload: Dict[str, Any] = {"enable_nanite": bool(enable), "enable": bool(enable)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_nanite", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_nanite': {e}")
    return _envelope("set_landscape_nanite", r)


@mcp.tool()
def set_landscape_world_partition(
    actor_name: str = "",
    grid_size: int = 4,
    *,
    mcp_id: str = "",
    include_grid_size_in_name=None,
) -> Dict[str, Any]:
    """Configure World Partition flags on the resolved ALandscape.

    234-stubs W1 (#80) Part 1: the C++ handler writes
    bIncludeGridSizeInNameForLandscapeActors directly on the actor and
    persists the requested grid_size in MCP metadata for the wave-close
    replay.
    """
    payload = {"wp_grid_size": float(grid_size), "grid_size": int(grid_size)}
    if actor_name: payload["actor_name"] = actor_name
    if mcp_id: payload["mcp_id"] = mcp_id
    if include_grid_size_in_name is not None:
        payload["include_grid_size_in_name"] = bool(include_grid_size_in_name)
    u = get_unreal_connection()
    if u is None: return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_landscape_world_partition", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_landscape_world_partition': {e}")
    return _envelope("set_landscape_world_partition", r)