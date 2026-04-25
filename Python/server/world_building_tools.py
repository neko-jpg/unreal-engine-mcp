"""World building tools for the Unreal MCP server."""

import logging
import math
import random
import time
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_vector3, validate_int, validate_float, validate_string,
    validate_positive_int, validate_unreal_path, MAX_ACTORS_PER_BATCH,
    ValidationError, make_validation_error_response_from_exception,
)
from utils.responses import make_error_response, is_success_response
from server.actor_tools import batch_spawn_actors
from helpers.infrastructure_creation import (
    _create_street_grid, _create_street_lights, _create_town_vehicles,
    _create_town_decorations, _create_traffic_lights, _create_street_signage,
    _create_sidewalks_crosswalks, _create_urban_furniture,
    _create_street_utilities, _create_central_plaza
)
from helpers.building_creation import _create_town_building
from helpers.castle_creation import (
    get_castle_size_params, calculate_scaled_dimensions, build_outer_bailey_walls,
    build_inner_bailey_walls, build_gate_complex, build_corner_towers,
    build_inner_corner_towers, build_intermediate_towers, build_central_keep,
    build_courtyard_complex, build_bailey_annexes, build_siege_weapons,
    build_village_settlement, build_drawbridge_and_moat, add_decorative_flags
)
from helpers.house_construction import build_house
from helpers.mansion_creation import (
    get_mansion_size_params, calculate_mansion_layout,
    build_mansion_main_structure, build_mansion_exterior, add_mansion_interior
)
from helpers.actor_utilities import spawn_blueprint_actor
from helpers.actor_name_manager import safe_spawn_actor
from helpers.bridge_aqueduct_creation import (
    build_suspension_bridge_structure, build_aqueduct_structure
)

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def create_pyramid(
    base_size: int = 3,
    block_size: float = 100.0,
    location: Optional[List[float]] = None,
    name_prefix: str = "PyramidBlock",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Spawn a pyramid made of cube actors."""
    try:
        validate_positive_int(base_size, "base_size", max_val=50)
        validate_float(block_size, "block_size", min_val=1.0, max_val=10000.0)
        validate_vector3(location, "location", allow_none=True)
        validate_string(name_prefix, "name_prefix")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        scale = block_size / 100.0
        actor_specs = []
        for level in range(base_size):
            count = base_size - level
            for x in range(count):
                for y in range(count):
                    actor_specs.append({
                        "name": f"{name_prefix}_{level}_{x}_{y}",
                        "type": "StaticMeshActor",
                        "location": [
                            location[0] + (x - (count - 1) / 2) * block_size,
                            location[1] + (y - (count - 1) / 2) * block_size,
                            location[2] + level * block_size,
                        ],
                        "scale": [scale, scale, scale],
                        "static_mesh": mesh,
                    })

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "actor_count": len(actor_specs),
                "actors": actor_specs,
                "message": f"Would spawn {len(actor_specs)} actors for pyramid (base_size={base_size}).",
            }

        result = batch_spawn_actors(actor_specs)
        result["message"] = f"Pyramid created: base_size={base_size}, spawned {result.get('spawned_count', 0)} actors"
        return result
    except Exception as e:
        logger.error(f"create_pyramid error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_wall(
    length: int = 5,
    height: int = 2,
    block_size: float = 100.0,
    location: Optional[List[float]] = None,
    orientation: str = "x",
    name_prefix: str = "WallBlock",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Create a simple wall from cubes."""
    try:
        validate_positive_int(length, "length", max_val=200)
        validate_positive_int(height, "height", max_val=100)
        validate_float(block_size, "block_size", min_val=1.0, max_val=10000.0)
        validate_vector3(location, "location", allow_none=True)
        validate_string(name_prefix, "name_prefix")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        scale = block_size / 100.0
        actor_specs = []
        for h in range(height):
            for i in range(length):
                if orientation == "x":
                    loc = [location[0] + i * block_size, location[1], location[2] + h * block_size]
                else:
                    loc = [location[0], location[1] + i * block_size, location[2] + h * block_size]
                actor_specs.append({
                    "name": f"{name_prefix}_{h}_{i}",
                    "type": "StaticMeshActor",
                    "location": loc,
                    "scale": [scale, scale, scale],
                    "static_mesh": mesh,
                })

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "actor_count": len(actor_specs),
                "actors": actor_specs,
                "message": f"Would spawn {len(actor_specs)} actors for wall (length={length}, height={height}).",
            }

        result = batch_spawn_actors(actor_specs)
        result["message"] = f"Wall created: length={length}, height={height}, spawned {result.get('spawned_count', 0)} actors"
        return result
    except Exception as e:
        logger.error(f"create_wall error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_tower(
    height: int = 10,
    base_size: int = 4,
    block_size: float = 100.0,
    location: Optional[List[float]] = None,
    name_prefix: str = "TowerBlock",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    tower_style: str = "cylindrical"
) -> Dict[str, Any]:
    """Create a realistic tower with various architectural styles."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")
        spawned = []
        scale = block_size / 100.0

        for level in range(height):
            level_height = location[2] + level * block_size

            if tower_style == "cylindrical":
                radius = (base_size / 2) * block_size
                circumference = 2 * math.pi * radius
                num_blocks = max(8, int(circumference / block_size))

                for i in range(num_blocks):
                    angle = (2 * math.pi * i) / num_blocks
                    x = location[0] + radius * math.cos(angle)
                    y = location[1] + radius * math.sin(angle)

                    actor_name = f"{name_prefix}_{level}_{i}"
                    params = {
                        "name": actor_name,
                        "type": "StaticMeshActor",
                        "location": [x, y, level_height],
                        "scale": [scale, scale, scale],
                        "static_mesh": mesh
                    }
                    resp = safe_spawn_actor(unreal, params)
                    if resp and is_success_response(resp):
                        spawned.append(resp)

            elif tower_style == "tapered":
                current_size = max(1, base_size - (level // 2))
                half_size = current_size / 2

                for side in range(4):
                    for i in range(current_size):
                        if side == 0:
                            x = location[0] + (i - half_size + 0.5) * block_size
                            y = location[1] - half_size * block_size
                            actor_name = f"{name_prefix}_{level}_front_{i}"
                        elif side == 1:
                            x = location[0] + half_size * block_size
                            y = location[1] + (i - half_size + 0.5) * block_size
                            actor_name = f"{name_prefix}_{level}_right_{i}"
                        elif side == 2:
                            x = location[0] + (half_size - i - 0.5) * block_size
                            y = location[1] + half_size * block_size
                            actor_name = f"{name_prefix}_{level}_back_{i}"
                        else:
                            x = location[0] - half_size * block_size
                            y = location[1] + (half_size - i - 0.5) * block_size
                            actor_name = f"{name_prefix}_{level}_left_{i}"

                        params = {
                            "name": actor_name,
                            "type": "StaticMeshActor",
                            "location": [x, y, level_height],
                            "scale": [scale, scale, scale],
                            "static_mesh": mesh
                        }
                        resp = safe_spawn_actor(unreal, params)
                        if resp and is_success_response(resp):
                            spawned.append(resp)

            else:  # square tower
                half_size = base_size / 2

                for side in range(4):
                    for i in range(base_size):
                        if side == 0:
                            x = location[0] + (i - half_size + 0.5) * block_size
                            y = location[1] - half_size * block_size
                            actor_name = f"{name_prefix}_{level}_front_{i}"
                        elif side == 1:
                            x = location[0] + half_size * block_size
                            y = location[1] + (i - half_size + 0.5) * block_size
                            actor_name = f"{name_prefix}_{level}_right_{i}"
                        elif side == 2:
                            x = location[0] + (half_size - i - 0.5) * block_size
                            y = location[1] + half_size * block_size
                            actor_name = f"{name_prefix}_{level}_back_{i}"
                        else:
                            x = location[0] - half_size * block_size
                            y = location[1] + (half_size - i - 0.5) * block_size
                            actor_name = f"{name_prefix}_{level}_left_{i}"

                        params = {
                            "name": actor_name,
                            "type": "StaticMeshActor",
                            "location": [x, y, level_height],
                            "scale": [scale, scale, scale],
                            "static_mesh": mesh
                        }
                        resp = safe_spawn_actor(unreal, params)
                        if resp and is_success_response(resp):
                            spawned.append(resp)

            if level % 3 == 2 and level < height - 1:
                for corner in range(4):
                    angle = corner * math.pi / 2
                    detail_x = location[0] + (base_size/2 + 0.5) * block_size * math.cos(angle)
                    detail_y = location[1] + (base_size/2 + 0.5) * block_size * math.sin(angle)

                    actor_name = f"{name_prefix}_{level}_detail_{corner}"
                    params = {
                        "name": actor_name,
                        "type": "StaticMeshActor",
                        "location": [detail_x, detail_y, level_height],
                        "scale": [scale * 0.7, scale * 0.7, scale * 0.7],
                        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
                    }
                    resp = safe_spawn_actor(unreal, params)
                    if resp and is_success_response(resp):
                        spawned.append(resp)

        return {"success": True, "actors": spawned, "tower_style": tower_style}
    except Exception as e:
        logger.error(f"create_tower error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_staircase(
    steps: int = 5,
    step_size: Optional[List[float]] = None,
    location: Optional[List[float]] = None,
    name_prefix: str = "Stair",
    mesh: str = "/Engine/BasicShapes/Cube.Cube"
) -> Dict[str, Any]:
    """Create a staircase from cubes."""
    try:
        if step_size is None:
            step_size = [100.0, 100.0, 50.0]
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")
        spawned = []
        sx, sy, sz = step_size
        for i in range(steps):
            actor_name = f"{name_prefix}_{i}"
            loc = [location[0] + i * sx, location[1], location[2] + i * sz]
            scale = [sx/100.0, sy/100.0, sz/100.0]
            params = {
                "name": actor_name,
                "type": "StaticMeshActor",
                "location": loc,
                "scale": scale,
                "static_mesh": mesh
            }
            resp = safe_spawn_actor(unreal, params)
            if resp and is_success_response(resp):
                spawned.append(resp)
        return {"success": True, "actors": spawned}
    except Exception as e:
        logger.error(f"create_staircase error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def construct_house(
    width: int = 1200,
    depth: int = 1000,
    height: int = 600,
    location: Optional[List[float]] = None,
    name_prefix: str = "House",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    house_style: str = "modern"
) -> Dict[str, Any]:
    """Construct a realistic house with architectural details and multiple rooms."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        return build_house(unreal, width, depth, height, location, name_prefix, mesh, house_style)

    except Exception as e:
        logger.error(f"construct_house error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def construct_mansion(
    mansion_scale: str = "large",
    location: Optional[List[float]] = None,
    name_prefix: str = "Mansion"
) -> Dict[str, Any]:
    """Construct a mansion with multiple wings, grand rooms, gardens, fountains, and luxury features."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        logger.info(f"Creating {mansion_scale} mansion")
        all_actors = []

        params = get_mansion_size_params(mansion_scale)
        layout = calculate_mansion_layout(params)

        build_mansion_main_structure(unreal, name_prefix, location, layout, all_actors)
        build_mansion_exterior(unreal, name_prefix, location, layout, all_actors)
        add_mansion_interior(unreal, name_prefix, location, layout, all_actors)

        logger.info(f"Mansion construction complete! Created {len(all_actors)} elements")

        return {
            "success": True,
            "message": f"Magnificent {mansion_scale} mansion created with {len(all_actors)} elements!",
            "actors": all_actors,
            "stats": {
                "scale": mansion_scale,
                "wings": layout["wings"],
                "floors": layout["floors"],
                "main_rooms": layout["main_rooms"],
                "bedrooms": layout["bedrooms"],
                "garden_size": layout["garden_size"],
                "fountain_count": layout["fountain_count"],
                "car_count": layout["car_count"],
                "total_actors": len(all_actors)
            }
        }

    except Exception as e:
        logger.error(f"construct_mansion error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_arch(
    radius: float = 300.0,
    segments: int = 6,
    location: Optional[List[float]] = None,
    name_prefix: str = "ArchBlock",
    mesh: str = "/Engine/BasicShapes/Cube.Cube"
) -> Dict[str, Any]:
    """Create a simple arch using cubes in a semicircle."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")
        spawned = []
        angle_step = math.pi / segments
        scale = radius / 300.0 / 2
        for i in range(segments + 1):
            theta = angle_step * i
            x = radius * math.cos(theta)
            z = radius * math.sin(theta)
            actor_name = f"{name_prefix}_{i}"
            params = {
                "name": actor_name,
                "type": "StaticMeshActor",
                "location": [location[0] + x, location[1], location[2] + z],
                "scale": [scale, scale, scale],
                "static_mesh": mesh
            }
            resp = safe_spawn_actor(unreal, params)
            if resp and is_success_response(resp):
                spawned.append(resp)
        return {"success": True, "actors": spawned}
    except Exception as e:
        logger.error(f"create_arch error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def spawn_physics_blueprint_actor(
    name: str,
    mesh_path: str = "/Engine/BasicShapes/Cube.Cube",
    location: Optional[List[float]] = None,
    mass: float = 1.0,
    simulate_physics: bool = True,
    gravity_enabled: bool = True,
    color: Optional[List[float]] = None,
    scale: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Quickly spawn a single actor with physics, color, and a specific mesh."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        if scale is None:
            scale = [1.0, 1.0, 1.0]
        bp_name = f"{name}_BP"
        # These are tools registered on the same mcp instance via server.blueprint_tools
        # We import and call them directly to avoid circular imports
        from server.blueprint_tools import create_blueprint, add_component_to_blueprint
        from server.blueprint_tools import set_static_mesh_properties, set_physics_properties
        from server.material_tools import set_mesh_material_color

        create_blueprint(bp_name, "Actor")
        add_component_to_blueprint(bp_name, "StaticMeshComponent", "Mesh", scale=scale)
        set_static_mesh_properties(bp_name, "Mesh", mesh_path)
        set_physics_properties(bp_name, "Mesh", simulate_physics, gravity_enabled, mass)

        if color is not None:
            if len(color) == 3:
                color = color + [1.0]
            elif len(color) != 4:
                logger.warning(f"Invalid color format: {color}. Expected [R,G,B] or [R,G,B,A]. Skipping color.")
                color = None

            if color is not None:
                color_result = set_mesh_material_color(bp_name, "Mesh", color)
                if not is_success_response(color_result):
                    logger.warning(f"Failed to set color {color} for {bp_name}: {color_result.get('error', 'Unknown error')}")

        # Import compile_blueprint locally to avoid circular import
        from server.blueprint_tools import compile_blueprint
        compile_blueprint(bp_name)

        # Spawn the blueprint actor using helper function
        unreal = get_unreal_connection()
        result = spawn_blueprint_actor(
            unreal,
            bp_name,
            name,
            location,
            auto_unique_name=False
        )

        # Ensure proper scale is set on the spawned actor
        if is_success_response(result):
            spawned_name = (
                result.get("final_name")
                or result.get("name")
                or result.get("result", {}).get("final_name")
                or result.get("result", {}).get("name")
                or name
            )
            # Import set_actor_transform locally to avoid circular import
            from server.actor_tools import set_actor_transform
            set_actor_transform(spawned_name, scale=scale)

        return result
    except Exception as e:
        logger.error(f"spawn_physics_blueprint_actor  error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_maze(
    rows: int = 4,
    cols: int = 4,
    cell_size: float = 300.0,
    wall_height: int = 3,
    location: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Create a proper solvable maze with entrance, exit, and guaranteed path using recursive backtracking algorithm."""
    try:
        validate_positive_int(rows, "rows", max_val=100)
        validate_positive_int(cols, "cols", max_val=100)
        validate_float(cell_size, "cell_size", min_val=10.0, max_val=10000.0)
        validate_positive_int(wall_height, "wall_height", max_val=50)
        validate_vector3(location, "location", allow_none=True)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        max_wall_estimate = (rows * 2 + 1) * (cols * 2 + 1) * wall_height + 2
        if max_wall_estimate > MAX_ACTORS_PER_BATCH:
            return make_error_response(
                f"Maximum possible actors {max_wall_estimate} exceeds limit of {MAX_ACTORS_PER_BATCH}. "
                f"Reduce rows, cols, or wall_height.",
                max_possible_actor_count=max_wall_estimate,
                max_actors=MAX_ACTORS_PER_BATCH,
            )

        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        spawned = []

        maze = [[True for _ in range(cols * 2 + 1)] for _ in range(rows * 2 + 1)]

        def carve_path(row, col):
            maze[row * 2 + 1][col * 2 + 1] = False
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            random.shuffle(directions)

            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < rows and 0 <= new_col < cols and
                    maze[new_row * 2 + 1][new_col * 2 + 1]):
                    maze[row * 2 + 1 + dr][col * 2 + 1 + dc] = False
                    carve_path(new_row, new_col)

        carve_path(0, 0)

        maze[1][0] = False
        maze[rows * 2 - 1][cols * 2] = False

        actual_wall_cells = sum(
            1 for r in range(rows * 2 + 1)
            for c in range(cols * 2 + 1)
            if maze[r][c]
        )
        estimated_actors = actual_wall_cells * wall_height + 2
        if estimated_actors > MAX_ACTORS_PER_BATCH:
            return make_error_response(
                f"Maze would produce {estimated_actors} actors, exceeding limit of {MAX_ACTORS_PER_BATCH}. "
                f"Reduce wall_height or maze dimensions.",
                estimated_actor_count=estimated_actors,
                max_actors=MAX_ACTORS_PER_BATCH,
            )

        maze_height = rows * 2 + 1
        maze_width = cols * 2 + 1

        for r in range(maze_height):
            for c in range(maze_width):
                if maze[r][c]:
                    for h in range(wall_height):
                        x_pos = location[0] + (c - maze_width/2) * cell_size
                        y_pos = location[1] + (r - maze_height/2) * cell_size
                        z_pos = location[2] + h * cell_size

                        actor_name = f"Maze_Wall_{r}_{c}_{h}"
                        params = {
                            "name": actor_name,
                            "type": "StaticMeshActor",
                            "location": [x_pos, y_pos, z_pos],
                            "scale": [cell_size/100.0, cell_size/100.0, cell_size/100.0],
                            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
                        }
                        resp = safe_spawn_actor(unreal, params)
                        if resp and is_success_response(resp):
                            spawned.append(resp)

        # Add entrance and exit markers
        entrance_marker = safe_spawn_actor(unreal, {
            "name": "Maze_Entrance",
            "type": "StaticMeshActor",
            "location": [location[0] - maze_width/2 * cell_size - cell_size,
                       location[1] + (-maze_height/2 + 1) * cell_size,
                       location[2] + cell_size],
            "scale": [0.5, 0.5, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        })
        if entrance_marker and is_success_response(entrance_marker):
            spawned.append(entrance_marker)

        exit_marker = safe_spawn_actor(unreal, {
            "name": "Maze_Exit",
            "type": "StaticMeshActor",
            "location": [location[0] + maze_width/2 * cell_size + cell_size,
                       location[1] + (-maze_height/2 + rows * 2 - 1) * cell_size,
                       location[2] + cell_size],
            "scale": [0.5, 0.5, 0.5],
            "static_mesh": "/Engine/BasicShapes/Sphere.Sphere"
        })
        if exit_marker and is_success_response(exit_marker):
            spawned.append(exit_marker)

        return {
            "success": True,
            "actors": spawned,
            "maze_size": f"{rows}x{cols}",
            "wall_count": actual_wall_cells,
            "entrance": "Left side (cylinder marker)",
            "exit": "Right side (sphere marker)"
        }
    except Exception as e:
        logger.error(f"create_maze error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_town(
    town_size: str = "medium",
    building_density: float = 0.7,
    location: Optional[List[float]] = None,
    name_prefix: str = "Town",
    include_infrastructure: bool = True,
    architectural_style: str = "mixed"
) -> Dict[str, Any]:
    """Create a full dynamic town with buildings, streets, infrastructure, and vehicles."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        random.seed()

        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        logger.info(f"Creating {town_size} town with {building_density} density at {location}")

        town_params = {
            "small": {"blocks": 3, "block_size": 1500, "max_building_height": 5, "population": 20, "skyscraper_chance": 0.1},
            "medium": {"blocks": 5, "block_size": 2000, "max_building_height": 10, "population": 50, "skyscraper_chance": 0.3},
            "large": {"blocks": 7, "block_size": 2500, "max_building_height": 20, "population": 100, "skyscraper_chance": 0.5},
            "metropolis": {"blocks": 10, "block_size": 3000, "max_building_height": 40, "population": 200, "skyscraper_chance": 0.7}
        }

        params = town_params.get(town_size, town_params["medium"])
        blocks = params["blocks"]
        block_size = params["block_size"]
        max_height = params["max_building_height"]
        target_population = int(params["population"] * building_density)
        skyscraper_chance = params["skyscraper_chance"]

        all_spawned = []
        street_width = block_size * 0.3
        building_area = block_size * 0.7

        # Create street grid first
        logger.info("Creating street grid...")
        street_results = _create_street_grid(blocks, block_size, street_width, location, name_prefix)
        all_spawned.extend(street_results.get("actors", []))

        # Create buildings in each block
        logger.info("Placing buildings...")
        building_count = 0
        for block_x in range(blocks):
            for block_y in range(blocks):
                if building_count >= target_population:
                    break

                if random.random() > building_density:
                    continue

                block_center_x = location[0] + (block_x - blocks/2) * block_size
                block_center_y = location[1] + (block_y - blocks/2) * block_size

                if architectural_style == "downtown" or architectural_style == "futuristic":
                    building_types = ["skyscraper", "office_tower", "apartment_complex", "shopping_mall", "parking_garage", "hotel"]
                elif architectural_style == "mixed":
                    is_central = abs(block_x - blocks//2) <= 1 and abs(block_y - blocks//2) <= 1
                    if is_central and random.random() < skyscraper_chance:
                        building_types = ["skyscraper", "office_tower", "apartment_complex", "hotel", "shopping_mall"]
                    else:
                        building_types = ["house", "tower", "mansion", "commercial", "apartment_building", "restaurant", "store"]
                else:
                    building_types = [architectural_style] * 3 + ["commercial", "restaurant", "store"]

                building_type = random.choice(building_types)

                building_result = _create_town_building(
                    building_type,
                    [block_center_x, block_center_y, location[2]],
                    building_area,
                    max_height,
                    f"{name_prefix}_Building_{block_x}_{block_y}",
                    building_count
                )

                if is_success_response(building_result):
                    all_spawned.extend(building_result.get("actors", []))
                    building_count += 1

        # Add infrastructure if requested
        infrastructure_count = 0
        if include_infrastructure:
            logger.info("Adding infrastructure...")

            light_results = _create_street_lights(blocks, block_size, location, name_prefix)
            all_spawned.extend(light_results.get("actors", []))
            infrastructure_count += len(light_results.get("actors", []))

            vehicle_results = _create_town_vehicles(blocks, block_size, street_width, location, name_prefix, target_population // 3)
            all_spawned.extend(vehicle_results.get("actors", []))
            infrastructure_count += len(vehicle_results.get("actors", []))

            decoration_results = _create_town_decorations(blocks, block_size, location, name_prefix)
            all_spawned.extend(decoration_results.get("actors", []))
            infrastructure_count += len(decoration_results.get("actors", []))

            traffic_results = _create_traffic_lights(blocks, block_size, location, name_prefix)
            all_spawned.extend(traffic_results.get("actors", []))
            infrastructure_count += len(traffic_results.get("actors", []))

            signage_results = _create_street_signage(blocks, block_size, location, name_prefix, town_size)
            all_spawned.extend(signage_results.get("actors", []))
            infrastructure_count += len(signage_results.get("actors", []))

            sidewalk_results = _create_sidewalks_crosswalks(blocks, block_size, street_width, location, name_prefix)
            all_spawned.extend(sidewalk_results.get("actors", []))
            infrastructure_count += len(sidewalk_results.get("actors", []))

            furniture_results = _create_urban_furniture(blocks, block_size, location, name_prefix)
            all_spawned.extend(furniture_results.get("actors", []))
            infrastructure_count += len(furniture_results.get("actors", []))

            utility_results = _create_street_utilities(blocks, block_size, location, name_prefix)
            all_spawned.extend(utility_results.get("actors", []))
            infrastructure_count += len(utility_results.get("actors", []))

            if town_size in ["large", "metropolis"]:
                plaza_results = _create_central_plaza(blocks, block_size, location, name_prefix)
                all_spawned.extend(plaza_results.get("actors", []))
                infrastructure_count += len(plaza_results.get("actors", []))

        return {
            "success": True,
            "town_stats": {
                "size": town_size,
                "density": building_density,
                "blocks": blocks,
                "buildings": building_count,
                "infrastructure_items": infrastructure_count,
                "total_actors": len(all_spawned),
                "architectural_style": architectural_style
            },
            "actors": all_spawned,
            "message": f"Created {town_size} town with {building_count} buildings and {infrastructure_count} infrastructure items"
        }

    except Exception as e:
        logger.error(f"create_town error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_castle_fortress(
    castle_size: str = "large",
    location: Optional[List[float]] = None,
    name_prefix: str = "Castle",
    include_siege_weapons: bool = True,
    include_village: bool = True,
    architectural_style: str = "medieval"
) -> Dict[str, Any]:
    """Create a massive castle fortress with walls, towers, courtyards, throne room, and surrounding village."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        logger.info(f"Creating {castle_size} {architectural_style} castle fortress")
        all_actors = []

        params = get_castle_size_params(castle_size)
        dimensions = calculate_scaled_dimensions(params, scale_factor=2.0)

        build_outer_bailey_walls(unreal, name_prefix, location, dimensions, all_actors)
        build_inner_bailey_walls(unreal, name_prefix, location, dimensions, all_actors)
        build_gate_complex(unreal, name_prefix, location, dimensions, all_actors)
        build_corner_towers(unreal, name_prefix, location, dimensions, architectural_style, all_actors)
        build_inner_corner_towers(unreal, name_prefix, location, dimensions, all_actors)
        build_intermediate_towers(unreal, name_prefix, location, dimensions, all_actors)
        build_central_keep(unreal, name_prefix, location, dimensions, all_actors)
        build_courtyard_complex(unreal, name_prefix, location, dimensions, all_actors)
        build_bailey_annexes(unreal, name_prefix, location, dimensions, all_actors)

        if include_siege_weapons:
            build_siege_weapons(unreal, name_prefix, location, dimensions, all_actors)

        if include_village:
            build_village_settlement(unreal, name_prefix, location, dimensions, castle_size, all_actors)

        build_drawbridge_and_moat(unreal, name_prefix, location, dimensions, all_actors)
        add_decorative_flags(unreal, name_prefix, location, dimensions, all_actors)

        logger.info(f"Castle fortress creation complete! Created {len(all_actors)} actors")

        return {
            "success": True,
            "message": f"Epic {castle_size} {architectural_style} castle fortress created with {len(all_actors)} elements!",
            "actors": all_actors,
            "stats": {
                "size": castle_size,
                "style": architectural_style,
                "wall_sections": int(dimensions["outer_width"]/200) * 2 + int(dimensions["outer_depth"]/200) * 2,
                "towers": dimensions["tower_count"],
                "has_village": include_village,
                "has_siege_weapons": include_siege_weapons,
                "total_actors": len(all_actors)
            }
        }

    except Exception as e:
        logger.error(f"create_castle_fortress error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_suspension_bridge(
    span_length: float = 6000.0,
    deck_width: float = 800.0,
    tower_height: float = 4000.0,
    cable_sag_ratio: float = 0.12,
    module_size: float = 200.0,
    location: Optional[List[float]] = None,
    orientation: str = "x",
    name_prefix: str = "Bridge",
    deck_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    tower_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    cable_mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
    suspender_mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Build a suspension bridge with towers, deck, cables, and suspenders."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        start_time = time.perf_counter()

        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        logger.info(f"Creating suspension bridge: span={span_length}, width={deck_width}, height={tower_height}")

        all_actors = []

        if dry_run:
            expected_towers = 10
            expected_deck = max(1, int(span_length / module_size)) * max(1, int(deck_width / module_size))
            expected_cables = 2 * max(1, int(span_length / module_size))
            expected_suspenders = 2 * max(1, int(span_length / (module_size * 3)))

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return {
                "success": True,
                "dry_run": True,
                "metrics": {
                    "total_actors": expected_towers + expected_deck + expected_cables + expected_suspenders,
                    "deck_segments": expected_deck,
                    "cable_segments": expected_cables,
                    "suspender_count": expected_suspenders,
                    "towers": expected_towers,
                    "span_length": span_length,
                    "deck_width": deck_width,
                    "est_area": span_length * deck_width,
                    "elapsed_ms": elapsed_ms
                }
            }

        counts = build_suspension_bridge_structure(
            unreal,
            span_length,
            deck_width,
            tower_height,
            cable_sag_ratio,
            module_size,
            location,
            orientation,
            name_prefix,
            deck_mesh,
            tower_mesh,
            cable_mesh,
            suspender_mesh,
            all_actors
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        total_actors = sum(counts.values())

        logger.info(f"Bridge construction complete: {total_actors} actors in {elapsed_ms}ms")

        return {
            "success": True,
            "message": f"Created suspension bridge with {total_actors} components",
            "actors": all_actors,
            "metrics": {
                "total_actors": total_actors,
                "deck_segments": counts["deck_segments"],
                "cable_segments": counts["cable_segments"],
                "suspender_count": counts["suspenders"],
                "towers": counts["towers"],
                "span_length": span_length,
                "deck_width": deck_width,
                "est_area": span_length * deck_width,
                "elapsed_ms": elapsed_ms
            }
        }

    except Exception as e:
        logger.error(f"create_suspension_bridge error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_aqueduct(
    arches: int = 18,
    arch_radius: float = 600.0,
    pier_width: float = 200.0,
    tiers: int = 2,
    deck_width: float = 600.0,
    module_size: float = 200.0,
    location: Optional[List[float]] = None,
    orientation: str = "x",
    name_prefix: str = "Aqueduct",
    arch_mesh: str = "/Engine/BasicShapes/Cylinder.Cylinder",
    pier_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    deck_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Build a multi-tier Roman-style aqueduct with arches and water channel."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        start_time = time.perf_counter()

        unreal = get_unreal_connection()
        if not unreal:
            return make_error_response("Failed to connect to Unreal Engine")

        logger.info(f"Creating aqueduct: {arches} arches, {tiers} tiers, radius={arch_radius}")

        all_actors = []

        total_length = arches * (2 * arch_radius + pier_width) + pier_width

        if dry_run:
            arch_circumference = math.pi * arch_radius
            segments_per_arch = max(4, int(arch_circumference / module_size))
            expected_arch_segments = tiers * arches * segments_per_arch

            expected_piers = tiers * (arches + 1)

            deck_length_segments = max(1, int(total_length / module_size))
            deck_width_segments = max(1, int(deck_width / module_size))
            expected_deck = deck_length_segments * deck_width_segments
            expected_deck += 2 * deck_length_segments

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return {
                "success": True,
                "dry_run": True,
                "metrics": {
                    "total_actors": expected_arch_segments + expected_piers + expected_deck,
                    "arch_segments": expected_arch_segments,
                    "pier_count": expected_piers,
                    "tiers": tiers,
                    "deck_segments": expected_deck,
                    "total_length": total_length,
                    "est_area": total_length * deck_width,
                    "elapsed_ms": elapsed_ms
                }
            }

        counts = build_aqueduct_structure(
            unreal,
            arches,
            arch_radius,
            pier_width,
            tiers,
            deck_width,
            module_size,
            location,
            orientation,
            name_prefix,
            arch_mesh,
            pier_mesh,
            deck_mesh,
            all_actors
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        total_actors = sum(counts.values())

        logger.info(f"Aqueduct construction complete: {total_actors} actors in {elapsed_ms}ms")

        return {
            "success": True,
            "message": f"Created {tiers}-tier aqueduct with {arches} arches ({total_actors} components)",
            "actors": all_actors,
            "metrics": {
                "total_actors": total_actors,
                "arch_segments": counts["arch_segments"],
                "pier_count": counts["piers"],
                "tiers": tiers,
                "deck_segments": counts["deck_segments"],
                "total_length": total_length,
                "est_area": total_length * deck_width,
                "elapsed_ms": elapsed_ms
            }
        }

    except Exception as e:
        logger.error(f"create_aqueduct error: {e}")
        return make_error_response(str(e))
