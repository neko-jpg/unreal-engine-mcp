import logging
from typing import Any, Dict, List, Optional

from server.core import mcp
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.generation.geometry import Aabb3
from server.generation.lsystem import evaluate_lsystem
from server.generation.sdf import sdf_to_voxel_surface_mesh
from server.generation.superformula import SuperformulaParams, superformula_mesh
from server.generation.wfc import solve_wfc_grid
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")

import server.scene_tools_common as _stc

from server.scene_tools_common import (
    _scene_syncd_error_response,
    _scene_syncd_data,
    _object_to_draft_instance,
    _send_draft_proxy_replace,
    _unreal_envelope,
)
from server.scene_crud_tools import scene_upsert_actors


def _is_failed(result: Dict[str, Any]) -> bool:
    return isinstance(result, dict) and result.get("success") is False


def _python_mesh_response(operation: str, payload: Any, sync_error: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.to_dict() if hasattr(payload, "to_dict") else payload
    return {
        "success": True,
        "operation": operation,
        "realized_in_unreal": False,
        "python_fallback": True,
        "data": data,
        "warning": "scene-syncd/Unreal realization was unavailable; returned Python-generated payload for preview/migration.",
        "sync_error": sync_error,
    }

@mcp.tool()
def scene_upsert_procedural_mesh(
    mcp_id: str,
    actor_name: Optional[str] = None,
    vertex_count: int = 3,
    index_count: int = 3,
    positions: List[List[float]] = None,
    normals: List[List[float]] = None,
    indices: List[int] = None,
    uvs: List[List[float]] = None,
    material_path: str = "",
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    focus_viewport: bool = True,
) -> Dict[str, Any]:
    """Upsert a procedural mesh in Unreal Engine by sending vertex data through the Rust scene-syncd service.

    This tool bypasses the JSON-only UnrealConnection and uses the Rust scene-syncd
    TCP binary protocol for efficient large mesh transfer. mcp_id is required.
    """
    positions = positions or []
    normals = normals or []
    indices = indices or []
    uvs = uvs or []
    
    try:
        validate_string(mcp_id, "mcp_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if len(positions) != vertex_count:
        return make_error_response(f"positions length ({len(positions)}) does not match vertex_count ({vertex_count})")
    if len(normals) != vertex_count:
        return make_error_response(f"normals length ({len(normals)}) does not match vertex_count ({vertex_count})")
    if len(indices) != index_count:
        return make_error_response(f"indices length ({len(indices)}) does not match index_count ({index_count})")

    payload = {
        "mcp_id": mcp_id,
        "actor_name": actor_name or mcp_id,
        "vertex_count": vertex_count,
        "index_count": index_count,
        "positions": positions,
        "normals": normals,
        "indices": indices,
        "material_path": material_path,
        "focus_viewport": focus_viewport,
    }
    
    if location:
        payload["location"] = [location.get("x", 0.0), location.get("y", 0.0), location.get("z", 0.0)]
    if rotation:
        payload["rotation"] = [rotation.get("pitch", 0.0), rotation.get("yaw", 0.0), rotation.get("roll", 0.0)]
    if scale:
        payload["scale"] = [scale.get("x", 1.0), scale.get("y", 1.0), scale.get("z", 1.0)]

    if uvs:
        payload["uvs"] = uvs
        payload["flags"] = 0x01

    result = _stc.call_scene_syncd("/procedural/create-mesh", payload)
    return _scene_syncd_error_response(result, "scene_upsert_procedural_mesh")




@mcp.tool()
def scene_create_sdf_mesh(
    mcp_id: str,
    sdf_tree: Optional[Dict[str, Any]] = None,
    sdf_type: str = "sphere",
    center: Optional[Dict[str, float]] = None,
    radius: float = 100.0,
    box_min: Optional[Dict[str, float]] = None,
    box_max: Optional[Dict[str, float]] = None,
    major_radius: float = 100.0,
    minor_radius: float = 30.0,
    frequency: float = 1.0,
    thickness: float = 10.0,
    resolution: int = 32,
    bounds: Optional[Dict[str, Dict[str, float]]] = None,
    bounds_padding: float = 10.0,
    actor_name: Optional[str] = None,
    material_path: str = "",
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    focus_viewport: bool = True,
    python_fallback: bool = True,
) -> Dict[str, Any]:
    """Generate a procedural mesh from a Signed Distance Function (SDF) using Marching Cubes.

    Supports: sphere, box, torus, gyroid, scherk. SDF meshes do not have UVs 驕ｯ・ｶ郢晢ｽｻ
    use World-Aligned materials on the Unreal side for texturing.
    """
    try:
        validate_string(mcp_id, "mcp_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    sdf_payload = sdf_tree or {
        "type": sdf_type,
        "center": [center.get("x", 0.0), center.get("y", 0.0), center.get("z", 0.0)] if center else [0.0, 0.0, 0.0],
        "radius": radius,
        "min": [box_min.get("x", -100.0), box_min.get("y", -100.0), box_min.get("z", -100.0)] if box_min else [-100.0, -100.0, -100.0],
        "max": [box_max.get("x", 100.0), box_max.get("y", 100.0), box_max.get("z", 100.0)] if box_max else [100.0, 100.0, 100.0],
        "major_radius": major_radius,
        "minor_radius": minor_radius,
        "frequency": frequency,
        "thickness": thickness,
    }

    payload = {
        "mcp_id": mcp_id,
        "sdf": sdf_payload,
        "resolution": resolution,
        "bounds_padding": bounds_padding,
        "actor_name": actor_name or mcp_id,
        "material_path": material_path,
        "focus_viewport": focus_viewport,
    }

    if bounds:
        payload["bounds"] = {
            "min": [bounds["min"].get("x", 0.0), bounds["min"].get("y", 0.0), bounds["min"].get("z", 0.0)],
            "max": [bounds["max"].get("x", 0.0), bounds["max"].get("y", 0.0), bounds["max"].get("z", 0.0)],
        }

    if location:
        payload["location"] = [location.get("x", 0.0), location.get("y", 0.0), location.get("z", 0.0)]
    if rotation:
        payload["rotation"] = [rotation.get("pitch", 0.0), rotation.get("yaw", 0.0), rotation.get("roll", 0.0)]
    if scale:
        payload["scale"] = [scale.get("x", 1.0), scale.get("y", 1.0), scale.get("z", 1.0)]

    result = _scene_syncd_error_response(_stc.call_scene_syncd("/procedural/sdf-mesh", payload), "scene_create_sdf_mesh")
    if _is_failed(result) and python_fallback:
        try:
            py_bounds = None
            if bounds:
                py_bounds = Aabb3(tuple(payload["bounds"]["min"]), tuple(payload["bounds"]["max"]))
            mesh = sdf_to_voxel_surface_mesh(sdf_payload, bounds=py_bounds, resolution=resolution, mcp_id=mcp_id)
            return _python_mesh_response("scene_create_sdf_mesh", mesh, result)
        except Exception as exc:
            result.setdefault("python_fallback_error", f"{type(exc).__name__}: {exc}")
    return result




@mcp.tool()
def scene_create_superformula_mesh(
    mcp_id: str,
    m1: float = 6.0,
    n1_1: float = 1.0,
    n2_1: float = 1.0,
    n3_1: float = 1.0,
    a1: float = 1.0,
    b1: float = 1.0,
    m2: float = 6.0,
    n1_2: float = 1.0,
    n2_2: float = 1.0,
    n3_2: float = 1.0,
    a2: float = 1.0,
    b2: float = 1.0,
    resolution: int = 32,
    scale: float = 100.0,
    actor_name: Optional[str] = None,
    material_path: str = "",
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale_override: Optional[Dict[str, float]] = None,
    focus_viewport: bool = True,
    python_fallback: bool = True,
) -> Dict[str, Any]:
    """Generate a procedural mesh from the 3D Superformula (Gielis).

    The Superformula creates parametric shapes from two 2D superformulas applied
    in spherical coordinates. UV mapping is derived from (theta, phi).
    Try m=8, n1=0.5 for star-like shapes, or m=4, n1=10 for rounded squares.
    """
    try:
        validate_string(mcp_id, "mcp_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload = {
        "mcp_id": mcp_id,
        "m1": m1, "n1_1": n1_1, "n2_1": n2_1, "n3_1": n3_1, "a1": a1, "b1": b1,
        "m2": m2, "n1_2": n1_2, "n2_2": n2_2, "n3_2": n3_2, "a2": a2, "b2": b2,
        "resolution": resolution,
        "scale": scale,
        "actor_name": actor_name or mcp_id,
        "material_path": material_path,
        "focus_viewport": focus_viewport,
    }

    if location:
        payload["location"] = [location.get("x", 0.0), location.get("y", 0.0), location.get("z", 0.0)]
    if rotation:
        payload["rotation"] = [rotation.get("pitch", 0.0), rotation.get("yaw", 0.0), rotation.get("roll", 0.0)]
    if scale_override:
        payload["scale_override"] = [scale_override.get("x", 1.0), scale_override.get("y", 1.0), scale_override.get("z", 1.0)]

    result = _scene_syncd_error_response(_stc.call_scene_syncd("/procedural/superformula-mesh", payload), "scene_create_superformula_mesh")
    if _is_failed(result) and python_fallback:
        try:
            params = SuperformulaParams(
                m1=m1,
                n1_1=n1_1,
                n2_1=n2_1,
                n3_1=n3_1,
                a1=a1,
                b1=b1,
                m2=m2,
                n1_2=n1_2,
                n2_2=n2_2,
                n3_2=n3_2,
                a2=a2,
                b2=b2,
            )
            mesh = superformula_mesh(params, resolution=resolution, scale=scale, mcp_id=mcp_id)
            return _python_mesh_response("scene_create_superformula_mesh", mesh, result)
        except Exception as exc:
            result.setdefault("python_fallback_error", f"{type(exc).__name__}: {exc}")
    return result




@mcp.tool()
def scene_create_lsystem_spline(
    mcp_id: str,
    preset: Optional[str] = None,
    axiom: str = "F",
    rules: Optional[List[List[str]]] = None,
    iterations: int = 3,
    step_length: float = 50.0,
    angle_degrees: float = 90.0,
    origin: Optional[Dict[str, float]] = None,
    heading: Optional[Dict[str, float]] = None,
    up: Optional[Dict[str, float]] = None,
    closed_loop: bool = False,
    tangent_mode: str = "curve",
    spline_name: Optional[str] = None,
    focus_viewport: bool = True,
    python_fallback: bool = True,
) -> Dict[str, Any]:
    """Generate a spline from an L-System grammar and create it in Unreal.

    The L-System turtle produces segments that are sent to Unreal as a
    create_spline_from_points command. Supports 3D operations: +/- for yaw,
    &/^ for pitch, \\\\/ for roll, [/] for push/pop branching.
    Common grammars: Koch curve (F驕ｶ髮・ｽｷ・ｽ+F-F-F+F, angle=90), tree (F驕ｶ髮・ｽｷ・ｽ[+F]F[-F]F).

    You can either define a custom grammar (axiom + rules) or use a named
    preset for common shapes:
      - "Koch2D"        驕ｯ・ｶ郢晢ｽｻKoch curve (2D, angle=90)
      - "Tree3D"        驕ｯ・ｶ郢晢ｽｻBranching tree (3D, angle=25.7)
      - "Dragon2D"      驕ｯ・ｶ郢晢ｽｻDragon curve (2D, angle=90)
      - "Sierpinski2D"  驕ｯ・ｶ郢晢ｽｻSierpinski triangle (2D, angle=120)
      - "Hilbert3D"     驕ｯ・ｶ郢晢ｽｻ3D Hilbert curve (3D, angle=90)

    When a preset is used, axiom, rules, and angle_degrees are taken from
    the preset. You can still override iterations, step_length, origin,
    heading, and up.
    """
    try:
        validate_string(mcp_id, "mcp_id")
        if preset is not None:
            validate_string(preset, "preset")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    rules = rules or [["F", "F+F-F-F+F"]]

    # Step 1: Evaluate L-System via scene-syncd to get segments
    lsystem_payload: Dict[str, Any] = {
        "mcp_id": mcp_id,
        "iterations": iterations,
        "step_length": step_length,
        "closed_loop": closed_loop,
        "tangent_mode": tangent_mode,
        "spline_name": spline_name or mcp_id,
        "create_in_unreal": True,
        "focus_viewport": focus_viewport,
    }
    if preset:
        lsystem_payload["preset"] = preset
    else:
        lsystem_payload["axiom"] = axiom
        lsystem_payload["rules"] = rules
        lsystem_payload["angle_degrees"] = angle_degrees

    if origin:
        lsystem_payload["origin"] = [origin.get("x", 0.0), origin.get("y", 0.0), origin.get("z", 0.0)]
    if heading:
        lsystem_payload["heading"] = [heading.get("x", 1.0), heading.get("y", 0.0), heading.get("z", 0.0)]
    if up:
        lsystem_payload["up"] = [up.get("x", 0.0), up.get("y", 0.0), up.get("z", 1.0)]

    result = _scene_syncd_error_response(_stc.call_scene_syncd("/procedural/lsystem-spline", lsystem_payload), "scene_create_lsystem_spline")
    if _is_failed(result) and python_fallback:
        try:
            rule_map = {str(rule[0])[0]: str(rule[1]) for rule in rules}
            generated = evaluate_lsystem(
                axiom=axiom,
                rules=rule_map,
                iterations=iterations,
                step_length=step_length,
                angle_degrees=angle_degrees,
                origin=[(origin or {}).get("x", 0.0), (origin or {}).get("y", 0.0), (origin or {}).get("z", 0.0)],
                heading=[(heading or {}).get("x", 1.0), (heading or {}).get("y", 0.0), (heading or {}).get("z", 0.0)],
                up=[(up or {}).get("x", 0.0), (up or {}).get("y", 0.0), (up or {}).get("z", 1.0)],
            )
            return _python_mesh_response("scene_create_lsystem_spline", generated, result)
        except Exception as exc:
            result.setdefault("python_fallback_error", f"{type(exc).__name__}: {exc}")
    return result




@mcp.tool()
def scene_create_wfc_grid(
    width: int,
    height: int,
    tiles: List[Dict[str, Any]],
    constraints: List[Dict[str, str]],
    seed: Optional[int] = None,
    periodic: bool = False,
    python_fallback: bool = True,
) -> Dict[str, Any]:
    """Generate a tile grid using Wave Function Collapse.

    The WFC solver takes a tileset and adjacency constraints, then produces
    a valid grid where every neighboring pair obeys the constraints.
    Output is a list of TileCell {x, y, tile_id, rotation_degrees}.

    Args:
        width: Grid width in cells.
        height: Grid height in cells.
        tiles: List of {"id": str, "weight": float} dicts.
        constraints: List of {"left": str, "right": str, "direction": str} dicts.
                     direction is one of "north", "south", "east", "west".
        seed: Optional deterministic seed.
        periodic: Whether grid edges wrap around.
    """
    if width <= 0 or height <= 0:
        return make_error_response("width and height must be positive")
    if not tiles:
        return make_error_response("tiles list cannot be empty")

    payload: Dict[str, Any] = {
        "width": width,
        "height": height,
        "tileset": {
            "tiles": tiles,
            "constraints": constraints,
        },
        "periodic": periodic,
    }
    if seed is not None:
        payload["seed"] = seed

    result = _scene_syncd_error_response(_stc.call_scene_syncd("/procedural/wfc-grid", payload), "scene_create_wfc_grid")
    if _is_failed(result) and python_fallback:
        try:
            generated = solve_wfc_grid(width, height, tiles, constraints, seed=seed, periodic=periodic)
            return {
                "success": True,
                "operation": "scene_create_wfc_grid",
                "python_fallback": True,
                "realized_in_unreal": False,
                **generated,
                "warning": "scene-syncd was unavailable; returned Python WFC result.",
                "sync_error": result,
            }
        except Exception as exc:
            result.setdefault("python_fallback_error", f"{type(exc).__name__}: {exc}")
    return result



# -----------------------------------------------------------------------
# WFC Unreal realization helpers
# -----------------------------------------------------------------------


@mcp.tool()
def scene_create_wfc_grid_unreal(
    width: int,
    height: int,
    tiles: List[Dict[str, Any]],
    constraints: List[Dict[str, str]],
    tile_asset_map: Dict[str, str],
    seed: Optional[int] = None,
    periodic: bool = False,
    set_id_prefix: str = "wfc",
    cell_size: Optional[Dict[str, float]] = None,
    origin: Optional[Dict[str, float]] = None,
    default_mesh_path: Optional[str] = None,
    material_map: Optional[Dict[str, str]] = None,
    default_material_path: Optional[str] = None,
    replace_existing: bool = True,
    focus_viewport: bool = False,
) -> Dict[str, Any]:
    """Generate a WFC grid in Rust and realize it natively in Unreal as HISM-per-tile.

    Combines `scene_create_wfc_grid` (Rust) with the Unreal native `spawn_tile_grid`
    command. One HierarchicalInstancedStaticMeshComponent actor is spawned per
    unique tile_id with all instances batched in a single component for efficient
    rendering of large grids.

    Args:
        width / height: Grid dimensions in cells.
        tiles: WFC tileset definitions ({"id":str,"weight":float}).
        constraints: Adjacency rules ({"left":str,"right":str,"direction":str}).
        tile_asset_map: tile_id to "/Game/.../SM_Asset" mapping.
        seed: Optional deterministic seed.
        periodic: Wrap grid edges.
        set_id_prefix: Prefix for spawned actor names + mcp_id tags.
        cell_size: {"x":100.0,"y":100.0} in Unreal units (cm). Default 100x100.
        origin: World origin offset for cell (0,0).
        default_mesh_path: Fallback mesh for tile_ids missing from the map.
        material_map / default_material_path: Optional materials.
        replace_existing: Destroy any existing tile-grid actors with the same prefix.
        focus_viewport: Move editor camera to spawned actors.
    """
    if not tile_asset_map:
        return make_error_response(
            "tile_asset_map cannot be empty. Provide tile_id to '/Game/.../SM_Asset' mappings."
        )

    grid_result = scene_create_wfc_grid(
        width=width,
        height=height,
        tiles=tiles,
        constraints=constraints,
        seed=seed,
        periodic=periodic,
    )
    if grid_result.get("success") is False:
        return grid_result

    grid_data = _scene_syncd_data(grid_result)
    grid_tiles = grid_data.get("tiles") or []

    spawn_params: Dict[str, Any] = {
        "set_id_prefix": set_id_prefix,
        "tiles": grid_tiles,
        "tile_asset_map": tile_asset_map,
        "replace_existing": replace_existing,
        "focus_viewport": focus_viewport,
    }
    if cell_size:
        spawn_params["cell_size"] = cell_size
    if origin:
        spawn_params["origin"] = origin
    if default_mesh_path:
        spawn_params["default_mesh_path"] = default_mesh_path
    if material_map:
        spawn_params["material_map"] = material_map
    if default_material_path:
        spawn_params["default_material_path"] = default_material_path

    try:
        conn = _stc.get_unreal_connection()
        unreal_result = conn.send_command("spawn_tile_grid", spawn_params)
    except Exception as e:
        return make_error_response(f"Failed to spawn tile grid in Unreal: {e}")

    if not unreal_result.get("success", False):
        err = unreal_result.get("error", "unknown error")
        hint = unreal_result.get("hint")
        msg = f"Unreal spawn_tile_grid failed: {err}"
        if hint:
            msg += f" Hint: {hint}"
        return make_error_response(msg)

    return {
        "success": True,
        "grid": {
            "width": grid_data.get("width", width),
            "height": grid_data.get("height", height),
            "tile_count": len(grid_tiles),
        },
        "unreal_result": unreal_result,
        "stats": grid_data.get("stats"),
    }




@mcp.tool()
def scene_wfc_to_semantic_layout(
    scene_id: str = "main",
    width: int = 4,
    height: int = 4,
    tiles: Optional[List[Dict[str, Any]]] = None,
    constraints: Optional[List[Dict[str, str]]] = None,
    tile_asset_map: Optional[Dict[str, str]] = None,
    seed: Optional[int] = None,
    periodic: bool = False,
    cell_size: Optional[Dict[str, float]] = None,
    origin: Optional[Dict[str, float]] = None,
    group_id_prefix: str = "wfc",
    desired_name_prefix: str = "WfcTile",
    extra_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate WFC + upsert each tile as a Semantic Layout entity in scene-syncd.

    The WFC output is materialized into the scene database as one StaticMeshActor
    per tile, tagged with `wfc_generated`, `wfc_tile_id:<id>`, and
    `layout_kind:wfc_<id>` so it can be reviewed by `scene_show_wfc_proxy`,
    edited individually, snapshotted, or compiled with the rest of the layout.

    The actors are NOT pushed to Unreal directly. Use `scene_compile_apply` or
    `scene_show_wfc_proxy` to realize them.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if not tiles:
        return make_error_response("tiles list cannot be empty")
    if constraints is None:
        constraints = []
    if not tile_asset_map:
        return make_error_response(
            "tile_asset_map cannot be empty. Provide tile_id to '/Game/.../SM_Asset' mappings."
        )

    grid_result = scene_create_wfc_grid(
        width=width,
        height=height,
        tiles=tiles,
        constraints=constraints,
        seed=seed,
        periodic=periodic,
    )
    if grid_result.get("success") is False:
        return grid_result

    grid_data = _scene_syncd_data(grid_result)
    grid_tiles = grid_data.get("tiles") or []
    if not grid_tiles:
        return make_error_response("WFC produced an empty grid")

    cs_x = (cell_size or {}).get("x", 100.0)
    cs_y = (cell_size or {}).get("y", 100.0)
    origin_x = (origin or {}).get("x", 0.0)
    origin_y = (origin or {}).get("y", 0.0)
    origin_z = (origin or {}).get("z", 0.0)

    base_tags = ["managed_by_mcp", "wfc_generated"]
    if extra_tags:
        base_tags.extend(extra_tags)

    objects: List[Dict[str, Any]] = []
    skipped_tiles: List[Dict[str, Any]] = []
    seen_kinds: Dict[str, int] = {}
    seed_token = seed if seed is not None else 0

    for tile in grid_tiles:
        tile_id = tile.get("tile_id")
        if not tile_id:
            continue
        asset_path = tile_asset_map.get(tile_id)
        if not asset_path:
            skipped_tiles.append({"tile_id": tile_id, "reason": "no asset path in tile_asset_map"})
            continue

        x = int(tile.get("x", 0))
        y = int(tile.get("y", 0))
        rotation_deg = float(tile.get("rotation_degrees", 0.0))

        seen_kinds[tile_id] = seen_kinds.get(tile_id, 0) + 1
        idx = seen_kinds[tile_id]

        mcp_id = f"{group_id_prefix}_{tile_id}_{x}_{y}_{seed_token}"
        try:
            mcp_id = sanitize_mcp_id(mcp_id)
        except ValidationError:
            # Fall back to a safer generic id
            mcp_id = f"{group_id_prefix}_t{idx}_{seed_token}"

        objects.append({
            "mcp_id": mcp_id,
            "desired_name": f"{desired_name_prefix}_{tile_id}_{x}_{y}",
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": asset_path},
            "transform": {
                "location": {
                    "x": origin_x + x * cs_x,
                    "y": origin_y + y * cs_y,
                    "z": origin_z,
                },
                "rotation": {"pitch": 0.0, "yaw": rotation_deg, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            "visual": {
                "draft": {"proxy_group": f"wfc_{tile_id}"},
            },
            "tags": base_tags + [
                f"wfc_tile_id:{tile_id}",
                f"layout_kind:wfc_{tile_id}",
            ],
        })

    if not objects:
        return make_error_response(
            "All WFC tiles skipped: no entries in tile_asset_map matched the tile_ids "
            f"{sorted({t.get('tile_id') for t in grid_tiles})}."
        )

    upsert_result = scene_upsert_actors(
        scene_id=scene_id,
        group_id=f"{group_id_prefix}_grid",
        objects=objects,
    )
    if upsert_result.get("success") is False:
        return upsert_result

    return {
        "success": True,
        "scene_id": scene_id,
        "grid": {
            "width": grid_data.get("width", width),
            "height": grid_data.get("height", height),
            "tile_count": len(grid_tiles),
        },
        "upserted_count": len(objects),
        "skipped_tiles": skipped_tiles,
        "tile_kinds": list(seen_kinds.keys()),
        "stats": grid_data.get("stats"),
        "upsert_result": upsert_result,
    }




@mcp.tool()
def scene_show_wfc_proxy(
    scene_id: str = "main",
    tile_mesh_map: Optional[Dict[str, str]] = None,
    proxy_name_prefix: str = "wfc_proxy",
    fallback_mesh_path: str = "/Engine/BasicShapes/Cube.Cube",
    use_dither: bool = True,
    tag_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Visualize WFC-generated semantic-layout entities as HISM draft proxies.

    Reads the scene's denormalized layout, filters objects tagged with
    `wfc_generated`, groups them by their `wfc_tile_id:<id>` tag, and creates
    one HISM proxy per tile_id using the supplied mesh map. This gives a fast,
    editable preview of the WFC result inside the editor without committing
    individual StaticMeshActors.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
        validate_string(proxy_name_prefix, "proxy_name_prefix")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    tile_mesh_map = tile_mesh_map or {}
    required_tags = set(tag_filter or [])

    # scene_wfc_to_semantic_layout creates desired objects via /objects/upsert,
    # not layout entities, so we query the object list directly.
    list_result = _scene_syncd_error_response(
        _stc.call_scene_syncd("/objects/list", {"scene_id": scene_id, "include_deleted": False}),
        "scene_show_wfc_proxy/list",
    )
    if list_result.get("success") is False:
        return list_result

    list_data = _scene_syncd_data(list_result)
    objects = list_data.get("objects") or []
    if not isinstance(objects, list):
        return make_error_response("scene-syncd preview did not include an objects list")

    def _wfc_tile_id(obj: Dict[str, Any]) -> Optional[str]:
        tags = obj.get("tags") or []
        if not isinstance(tags, list):
            return None
        is_wfc = False
        tile_id: Optional[str] = None
        present: set = set()
        for tag in tags:
            if not isinstance(tag, str):
                continue
            present.add(tag)
            if tag == "wfc_generated":
                is_wfc = True
            elif tag.startswith("wfc_tile_id:"):
                tile_id = tag.split(":", 1)[1]
        if not is_wfc:
            return None
        if required_tags and not required_tags.issubset(present):
            return None
        return tile_id

    batches: Dict[str, List[Dict[str, Any]]] = {}
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        tile_id = _wfc_tile_id(obj)
        if not tile_id:
            continue
        batches.setdefault(tile_id, []).append(_object_to_draft_instance(obj))

    if not batches:
        return make_error_response(
            "No WFC-generated objects found. Run scene_wfc_to_semantic_layout first."
        )

    try:
        conn = _stc.get_unreal_connection()
        proxy_results = []
        for tile_id, instances in sorted(batches.items()):
            mesh_path = tile_mesh_map.get(tile_id, fallback_mesh_path)
            proxy_name = f"{proxy_name_prefix}_{tile_id}"
            unreal_result = _send_draft_proxy_replace(
                conn,
                proxy_name,
                mesh_path,
                None,
                instances,
                use_dither,
            )
            if not unreal_result.get("success", False):
                return make_error_response(
                    f"Unreal draft proxy '{proxy_name}' failed: "
                    f"{unreal_result.get('error', 'unknown error')}"
                )
            proxy_results.append(
                {
                    "tile_id": tile_id,
                    "proxy_name": proxy_name,
                    "mesh_path": mesh_path,
                    "instance_count": len(instances),
                    "unreal_result": unreal_result,
                }
            )
    except Exception as e:
        return make_error_response(f"Failed to show WFC proxy in Unreal: {e}")

    return {
        "success": True,
        "scene_id": scene_id,
        "tile_kind_count": len(proxy_results),
        "total_instances": sum(p["instance_count"] for p in proxy_results),
        "proxies": proxy_results,
    }



# -----------------------------------------------------------------------
# Procedural background-job tools (avoid bridge timeouts on big WFC/L-System runs)
# -----------------------------------------------------------------------
import time as _time



@mcp.tool()
def scene_spawn_procedural_actor_batch(
    placements: List[Dict[str, Any]],
    group_id: Optional[str] = None,
    max_actors: int = 5000,
    focus_viewport: bool = False,
) -> Dict[str, Any]:
    """Bulk-spawn actors from an array of placement hints (Unreal Editor only).

    Each placement is a dict with at least `actor_class` (default
    "StaticMeshActor"), `location`, `rotation`, `scale`, and optionally
    `mcp_id`, `static_mesh`, `desired_name`, `tags`. When `group_id` is set,
    every spawned actor is tagged `procedural_group:<group_id>` so
    `scene_clear_generated_group` can clean them up later.

    Guardrails: requests larger than `max_actors` (default 5000) are clipped
    and a warning entry of type `ActorCountCapped` is included in the response.
    """
    if not isinstance(placements, list):
        return make_error_response("placements must be a list of placement dicts")

    params: Dict[str, Any] = {
        "placements": placements,
        "max_actors": int(max_actors),
        "focus_viewport": bool(focus_viewport),
    }
    if group_id is not None:
        try:
            validate_string(group_id, "group_id")
        except ValidationError as e:
            return make_validation_error_response_from_exception(e)
        params["group_id"] = group_id

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("spawn_procedural_actor_batch", params)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_procedural_actor_batch': {e}")
    return _unreal_envelope("spawn_procedural_actor_batch", result)




@mcp.tool()
def scene_create_spline_mesh_from_segments(
    actor_name: str,
    segments: List[Dict[str, Any]],
    mesh_path: str,
    mcp_id: Optional[str] = None,
    material_path: Optional[str] = None,
    forward_axis: str = "X",
    max_segments: int = 10000,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build one USplineMeshComponent per segment under a single parent actor.

    `segments` is a list of dicts: `{"start": [x,y,z], "end": [x,y,z],
    "start_tangent"?: [x,y,z], "end_tangent"?: [x,y,z]}`. Tangents default to
    `end - start` when omitted. `forward_axis` is "X" / "Y" / "Z" and selects
    which mesh axis is bent along the spline.

    Reuses an existing actor named `actor_name` if present; otherwise spawns a
    fresh one with a USceneComponent root. Designed for L-System turtle output
    or other procedurally-generated branch geometry.
    """
    try:
        validate_string(actor_name, "actor_name")
        validate_string(mesh_path, "mesh_path")
        validate_string(forward_axis, "forward_axis")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if not isinstance(segments, list) or not segments:
        return make_error_response("segments must be a non-empty list of dicts")

    params: Dict[str, Any] = {
        "actor_name": actor_name,
        "segments": segments,
        "mesh_path": mesh_path,
        "forward_axis": forward_axis,
        "max_segments": int(max_segments),
    }
    if mcp_id is not None:
        params["mcp_id"] = mcp_id
    if material_path is not None:
        params["material_path"] = material_path
    if tags:
        params["tags"] = list(tags)

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("create_spline_mesh_from_segments", params)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_spline_mesh_from_segments': {e}")
    return _unreal_envelope("create_spline_mesh_from_segments", result)




@mcp.tool()
def scene_create_data_layer_for_generation(
    data_layer_name: str,
    actor_mcp_ids: List[str],
    color_hex: Optional[str] = None,
    initial_state: Optional[str] = None,
) -> Dict[str, Any]:
    """Assign procedurally-generated actors to a logical data layer.

    First-pass implementation: every matched actor gets a
    `data_layer:<data_layer_name>` tag in addition to `managed_by_mcp`. A
    follow-up will wire `UDataLayerEditorSubsystem` to create a real
    `UDataLayerAsset` / `UDataLayerInstanceWithAsset` when the level uses
    World Partition; the response always includes a `method` field
    (`"tag"` today, `"data_layer_instance"` later) so callers can branch.

    `color_hex` and `initial_state` are accepted but reserved for the
    follow-up implementation.
    """
    try:
        validate_string(data_layer_name, "data_layer_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    if not isinstance(actor_mcp_ids, list) or not actor_mcp_ids:
        return make_error_response("actor_mcp_ids must be a non-empty list of strings")

    params: Dict[str, Any] = {
        "data_layer_name": data_layer_name,
        "actor_mcp_ids": list(actor_mcp_ids),
    }
    if color_hex is not None:
        params["color_hex"] = color_hex
    if initial_state is not None:
        params["initial_state"] = initial_state

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("create_data_layer_for_generation", params)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_data_layer_for_generation': {e}")
    return _unreal_envelope("create_data_layer_for_generation", result)




@mcp.tool()
def scene_clear_generated_group(
    group_id: Optional[str] = None,
    required_tags: Optional[List[str]] = None,
    dry_run: bool = True,
    max_delete: int = 10000,
) -> Dict[str, Any]:
    """Bulk-delete procedurally-generated actors filtered by group_id and/or tags.

    SAFETY: This call defaults to `dry_run=True`. The response will include
    `would_delete_count` and the list of `actor_paths` that match. Pass
    `dry_run=False` only after reviewing the dry-run result.

    AT LEAST one of `group_id` or non-empty `required_tags` MUST be provided -
    the C++ side refuses an empty filter to avoid accidentally deleting every
    actor in the level.
    """
    if (group_id is None or not group_id) and (not required_tags):
        return make_error_response(
            "Refusing to clear without 'group_id' or non-empty 'required_tags' "
            "(this would match every actor in the level)."
        )

    params: Dict[str, Any] = {
        "dry_run": bool(dry_run),
        "max_delete": int(max_delete),
    }
    if group_id:
        try:
            validate_string(group_id, "group_id")
        except ValidationError as e:
            return make_validation_error_response_from_exception(e)
        params["group_id"] = group_id
    if required_tags:
        params["required_tags"] = list(required_tags)

    try:
        conn = _stc.get_unreal_connection()
        result = conn.send_command("clear_generated_group", params)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'clear_generated_group': {e}")
    return _unreal_envelope("clear_generated_group", result)

