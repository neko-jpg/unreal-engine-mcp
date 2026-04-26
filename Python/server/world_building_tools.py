"""World building tools for the Unreal MCP server."""

import logging
import math
import random
import time
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_vector3, validate_float, validate_string,
    validate_positive_int, MAX_ACTORS_PER_BATCH,
    ValidationError, make_validation_error_response_from_exception,
)
from utils.responses import make_error_response, is_success_response
from server.actor_sink import ActorSpec, DryRunActorSink, UnrealActorSink
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

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        for level in range(base_size):
            count = base_size - level
            for x in range(count):
                for y in range(count):
                    mcp_id = f"{name_prefix}_{level}_{x}_{y}"
                    sink.spawn(ActorSpec(
                        mcp_id=mcp_id,
                        desired_name=mcp_id,
                        actor_type="StaticMeshActor",
                        asset_ref={"path": mesh},
                        transform={
                            "location": {
                                "x": location[0] + (x - (count - 1) / 2) * block_size,
                                "y": location[1] + (y - (count - 1) / 2) * block_size,
                                "z": location[2] + level * block_size,
                            },
                            "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                            "scale": {"x": block_size / 100.0, "y": block_size / 100.0, "z": block_size / 100.0},
                        },
                        tags=["pyramid", name_prefix],
                    ))

        result = sink.flush()
        if dry_run:
            result["message"] = f"Would spawn {len(sink.specs)} actors for pyramid (base_size={base_size})."
        else:
            result["message"] = f"Pyramid created: base_size={base_size}"
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

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        for h in range(height):
            for i in range(length):
                if orientation == "x":
                    loc_x = location[0] + i * block_size
                    loc_y = location[1]
                else:
                    loc_x = location[0]
                    loc_y = location[1] + i * block_size
                loc_z = location[2] + h * block_size
                mcp_id = f"{name_prefix}_{h}_{i}"
                sink.spawn(ActorSpec(
                    mcp_id=mcp_id,
                    desired_name=mcp_id,
                    actor_type="StaticMeshActor",
                    asset_ref={"path": mesh},
                    transform={
                        "location": {"x": loc_x, "y": loc_y, "z": loc_z},
                        "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                        "scale": {"x": block_size / 100.0, "y": block_size / 100.0, "z": block_size / 100.0},
                    },
                    tags=["wall", name_prefix],
                ))

        result = sink.flush()
        if dry_run:
            result["message"] = f"Would spawn {len(sink.specs)} actors for wall (length={length}, height={height})."
        else:
            result["message"] = f"Wall created: length={length}, height={height}"
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
    tower_style: str = "cylindrical",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a realistic tower with various architectural styles."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
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
                    mcp_id = f"{name_prefix}_{level}_{i}"
                    sink.spawn(ActorSpec(
                        mcp_id=mcp_id, desired_name=mcp_id,
                        actor_type="StaticMeshActor",
                        asset_ref={"path": mesh},
                        transform={
                            "location": {"x": x, "y": y, "z": level_height},
                            "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                            "scale": {"x": scale, "y": scale, "z": scale},
                        },
                        tags=["tower", name_prefix],
                    ))

            elif tower_style == "tapered":
                current_size = max(1, base_size - (level // 2))
                half_size = current_size / 2

                for side in range(4):
                    for i in range(current_size):
                        if side == 0:
                            x = location[0] + (i - half_size + 0.5) * block_size
                            y = location[1] - half_size * block_size
                            side_label = "front"
                        elif side == 1:
                            x = location[0] + half_size * block_size
                            y = location[1] + (i - half_size + 0.5) * block_size
                            side_label = "right"
                        elif side == 2:
                            x = location[0] + (half_size - i - 0.5) * block_size
                            y = location[1] + half_size * block_size
                            side_label = "back"
                        else:
                            x = location[0] - half_size * block_size
                            y = location[1] + (half_size - i - 0.5) * block_size
                            side_label = "left"
                        mcp_id = f"{name_prefix}_{level}_{side_label}_{i}"
                        sink.spawn(ActorSpec(
                            mcp_id=mcp_id, desired_name=mcp_id,
                            actor_type="StaticMeshActor",
                            asset_ref={"path": mesh},
                            transform={
                                "location": {"x": x, "y": y, "z": level_height},
                                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                                "scale": {"x": scale, "y": scale, "z": scale},
                            },
                            tags=["tower", name_prefix],
                        ))

            else:  # square tower
                half_size = base_size / 2

                for side in range(4):
                    for i in range(base_size):
                        if side == 0:
                            x = location[0] + (i - half_size + 0.5) * block_size
                            y = location[1] - half_size * block_size
                            side_label = "front"
                        elif side == 1:
                            x = location[0] + half_size * block_size
                            y = location[1] + (i - half_size + 0.5) * block_size
                            side_label = "right"
                        elif side == 2:
                            x = location[0] + (half_size - i - 0.5) * block_size
                            y = location[1] + half_size * block_size
                            side_label = "back"
                        else:
                            x = location[0] - half_size * block_size
                            y = location[1] + (half_size - i - 0.5) * block_size
                            side_label = "left"
                        mcp_id = f"{name_prefix}_{level}_{side_label}_{i}"
                        sink.spawn(ActorSpec(
                            mcp_id=mcp_id, desired_name=mcp_id,
                            actor_type="StaticMeshActor",
                            asset_ref={"path": mesh},
                            transform={
                                "location": {"x": x, "y": y, "z": level_height},
                                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                                "scale": {"x": scale, "y": scale, "z": scale},
                            },
                            tags=["tower", name_prefix],
                        ))

            if level % 3 == 2 and level < height - 1:
                for corner in range(4):
                    angle = corner * math.pi / 2
                    detail_x = location[0] + (base_size/2 + 0.5) * block_size * math.cos(angle)
                    detail_y = location[1] + (base_size/2 + 0.5) * block_size * math.sin(angle)
                    mcp_id = f"{name_prefix}_{level}_detail_{corner}"
                    sink.spawn(ActorSpec(
                        mcp_id=mcp_id, desired_name=mcp_id,
                        actor_type="StaticMeshActor",
                        asset_ref={"path": "/Engine/BasicShapes/Cylinder.Cylinder"},
                        transform={
                            "location": {"x": detail_x, "y": detail_y, "z": level_height},
                            "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                            "scale": {"x": scale * 0.7, "y": scale * 0.7, "z": scale * 0.7},
                        },
                        tags=["tower_detail", name_prefix],
                    ))

        result = sink.flush()
        result["tower_style"] = tower_style
        return result
    except Exception as e:
        logger.error(f"create_tower error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_staircase(
    steps: int = 5,
    step_size: Optional[List[float]] = None,
    location: Optional[List[float]] = None,
    name_prefix: str = "Stair",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Create a staircase from cubes."""
    try:
        if step_size is None:
            step_size = [100.0, 100.0, 50.0]
        if location is None:
            location = [0.0, 0.0, 0.0]

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        sx, sy, sz = step_size
        for i in range(steps):
            mcp_id = f"{name_prefix}_{i}"
            sink.spawn(ActorSpec(
                mcp_id=mcp_id, desired_name=mcp_id,
                actor_type="StaticMeshActor",
                asset_ref={"path": mesh},
                transform={
                    "location": {"x": location[0] + i * sx, "y": location[1], "z": location[2] + i * sz},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": sx / 100.0, "y": sy / 100.0, "z": sz / 100.0},
                },
                tags=["staircase", name_prefix],
            ))

        result = sink.flush()
        if dry_run:
            result["message"] = f"Would spawn {len(sink.specs)} actors for staircase ({steps} steps)."
        else:
            result["message"] = f"Staircase created: {steps} steps"
        return result
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
    house_style: str = "modern",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Construct a realistic house with architectural details and multiple rooms."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        build_house(None, width, depth, height, location, name_prefix, mesh, house_style, sink=sink)
        result = sink.flush()
        if dry_run:
            result["message"] = f"Would spawn {len(sink.specs)} actors for house ({house_style})."
        else:
            result["message"] = f"House ({house_style}) created."
        return result

    except Exception as e:
        logger.error(f"construct_house error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def construct_mansion(
    mansion_scale: str = "large",
    location: Optional[List[float]] = None,
    name_prefix: str = "Mansion",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Construct a mansion with multiple wings, grand rooms, gardens, fountains, and luxury features."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        logger.info(f"Creating {mansion_scale} mansion")

        params = get_mansion_size_params(mansion_scale)
        layout = calculate_mansion_layout(params)

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        build_mansion_main_structure(None, name_prefix, location, layout, [], sink=sink)
        build_mansion_exterior(None, name_prefix, location, layout, [], sink=sink)
        add_mansion_interior(None, name_prefix, location, layout, [], sink=sink)

        result = sink.flush()
        if dry_run:
            count = len(sink.specs) if hasattr(sink, 'specs') else 0
            result["message"] = f"Would spawn {count} actors for {mansion_scale} mansion."
        else:
            count = result.get("count", 0)
            result["message"] = f"Magnificent {mansion_scale} mansion created with {count} elements!"
        result["stats"] = {
            "scale": mansion_scale,
            "wings": layout["wings"],
            "floors": layout["floors"],
            "main_rooms": layout["main_rooms"],
            "bedrooms": layout["bedrooms"],
            "garden_size": layout["garden_size"],
            "fountain_count": layout["fountain_count"],
            "car_count": layout["car_count"],
            "total_actors": count
        }
        return result

    except Exception as e:
        logger.error(f"construct_mansion error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_arch(
    radius: float = 300.0,
    segments: int = 6,
    location: Optional[List[float]] = None,
    name_prefix: str = "ArchBlock",
    mesh: str = "/Engine/BasicShapes/Cube.Cube",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Create a simple arch using cubes in a semicircle."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        angle_step = math.pi / segments
        scale = radius / 300.0 / 2
        for i in range(segments + 1):
            theta = angle_step * i
            x = radius * math.cos(theta)
            z = radius * math.sin(theta)
            mcp_id = f"{name_prefix}_{i}"
            sink.spawn(ActorSpec(
                mcp_id=mcp_id, desired_name=mcp_id,
                actor_type="StaticMeshActor",
                asset_ref={"path": mesh},
                transform={
                    "location": {"x": location[0] + x, "y": location[1], "z": location[2] + z},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": scale, "y": scale, "z": scale},
                },
                tags=["arch", name_prefix],
            ))

        result = sink.flush()
        if dry_run:
            result["message"] = f"Would spawn {len(sink.specs)} actors for arch (radius={radius}, segments={segments})."
        else:
            result["message"] = f"Arch created: radius={radius}, segments={segments}"
        return result
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
    location: Optional[List[float]] = None,
    dry_run: bool = False
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

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        maze_height = rows * 2 + 1
        maze_width = cols * 2 + 1
        wall_scale = cell_size / 100.0

        for r in range(maze_height):
            for c in range(maze_width):
                if maze[r][c]:
                    for h in range(wall_height):
                        mcp_id = f"Maze_Wall_{r}_{c}_{h}"
                        sink.spawn(ActorSpec(
                            mcp_id=mcp_id, desired_name=mcp_id,
                            actor_type="StaticMeshActor",
                            asset_ref={"path": "/Engine/BasicShapes/Cube.Cube"},
                            transform={
                                "location": {
                                    "x": location[0] + (c - maze_width / 2) * cell_size,
                                    "y": location[1] + (r - maze_height / 2) * cell_size,
                                    "z": location[2] + h * cell_size,
                                },
                                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                                "scale": {"x": wall_scale, "y": wall_scale, "z": wall_scale},
                            },
                            tags=["maze", "wall"],
                        ))

        sink.spawn(ActorSpec(
            mcp_id="Maze_Entrance", desired_name="Maze_Entrance",
            actor_type="StaticMeshActor",
            asset_ref={"path": "/Engine/BasicShapes/Cylinder.Cylinder"},
            transform={
                "location": {
                    "x": location[0] - maze_width / 2 * cell_size - cell_size,
                    "y": location[1] + (-maze_height / 2 + 1) * cell_size,
                    "z": location[2] + cell_size,
                },
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 0.5, "y": 0.5, "z": 0.5},
            },
            tags=["maze", "entrance"],
        ))

        sink.spawn(ActorSpec(
            mcp_id="Maze_Exit", desired_name="Maze_Exit",
            actor_type="StaticMeshActor",
            asset_ref={"path": "/Engine/BasicShapes/Sphere.Sphere"},
            transform={
                "location": {
                    "x": location[0] + maze_width / 2 * cell_size + cell_size,
                    "y": location[1] + (-maze_height / 2 + rows * 2 - 1) * cell_size,
                    "z": location[2] + cell_size,
                },
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 0.5, "y": 0.5, "z": 0.5},
            },
            tags=["maze", "exit"],
        ))

        result = sink.flush()
        result["maze_size"] = f"{rows}x{cols}"
        result["wall_count"] = actual_wall_cells
        result["entrance"] = "Left side (cylinder marker)"
        result["exit"] = "Right side (sphere marker)"
        return result
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
    architectural_style: str = "mixed",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Create a full dynamic town with buildings, streets, infrastructure, and vehicles."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]
        random.seed()

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

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        street_width = block_size * 0.3
        building_area = block_size * 0.7

        # Create street grid first
        logger.info("Creating street grid...")
        _create_street_grid(blocks, block_size, street_width, location, name_prefix, [], sink=sink)

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
                    building_count,
                    all_actors=[],
                    sink=sink
                )

                if building_result.get("success"):
                    building_count += 1

        # Add infrastructure if requested
        infrastructure_count = 0
        if include_infrastructure:
            logger.info("Adding infrastructure...")

            infra_calls = [
                ("light", _create_street_lights, [blocks, block_size, location, name_prefix]),
                ("vehicle", _create_town_vehicles, [blocks, block_size, street_width, location, name_prefix, target_population // 3]),
                ("decoration", _create_town_decorations, [blocks, block_size, location, name_prefix]),
                ("traffic", _create_traffic_lights, [blocks, block_size, location, name_prefix]),
                ("signage", _create_street_signage, [blocks, block_size, location, name_prefix, town_size]),
                ("sidewalk", _create_sidewalks_crosswalks, [blocks, block_size, street_width, location, name_prefix]),
                ("furniture", _create_urban_furniture, [blocks, block_size, location, name_prefix]),
                ("utility", _create_street_utilities, [blocks, block_size, location, name_prefix]),
            ]

            for name, func, args in infra_calls:
                result = func(*args, all_actors=[], sink=sink)
                infrastructure_count += len(result.get("actors", []))

            if town_size in ["large", "metropolis"]:
                _create_central_plaza(blocks, block_size, location, name_prefix, [], sink=sink)

        result = sink.flush()
        total = len(sink.specs) if hasattr(sink, 'specs') else result.get("count", 0)
        if dry_run:
            result["message"] = f"Would spawn {total} actors for {town_size} town."
        else:
            result["message"] = f"Created {town_size} town with {building_count} buildings and {infrastructure_count} infrastructure items"
        result["town_stats"] = {
            "size": town_size,
            "density": building_density,
            "blocks": blocks,
            "buildings": building_count,
            "infrastructure_items": infrastructure_count,
            "total_actors": total,
            "architectural_style": architectural_style
        }
        return result

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
    architectural_style: str = "medieval",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Create a massive castle fortress with walls, towers, courtyards, throne room, and surrounding village."""
    try:
        if location is None:
            location = [0.0, 0.0, 0.0]

        logger.info(f"Creating {castle_size} {architectural_style} castle fortress")

        params = get_castle_size_params(castle_size)
        dimensions = calculate_scaled_dimensions(params, scale_factor=2.0)

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        all_actors: List[Dict[str, Any]] = []

        build_outer_bailey_walls(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_inner_bailey_walls(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_gate_complex(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_corner_towers(None, name_prefix, location, dimensions, architectural_style, all_actors, sink=sink)
        build_inner_corner_towers(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_intermediate_towers(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_central_keep(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_courtyard_complex(None, name_prefix, location, dimensions, all_actors, sink=sink)
        build_bailey_annexes(None, name_prefix, location, dimensions, all_actors, sink=sink)

        if include_siege_weapons:
            build_siege_weapons(None, name_prefix, location, dimensions, all_actors, sink=sink)

        if include_village:
            build_village_settlement(None, name_prefix, location, dimensions, castle_size, all_actors, sink=sink)

        build_drawbridge_and_moat(None, name_prefix, location, dimensions, all_actors, sink=sink)
        add_decorative_flags(None, name_prefix, location, dimensions, all_actors, sink=sink)

        logger.info(f"Castle fortress creation complete! Spawned {len(sink.specs)} actors")

        result = sink.flush()
        wall_sections = int(dimensions["outer_width"]/200) * 2 + int(dimensions["outer_depth"]/200) * 2
        total = len(sink.specs)
        if dry_run:
            result["message"] = f"Would spawn {total} actors for {castle_size} {architectural_style} castle fortress."
        else:
            result["message"] = f"Epic {castle_size} {architectural_style} castle fortress created with {total} elements!"
        result["stats"] = {
            "size": castle_size,
            "style": architectural_style,
            "wall_sections": wall_sections,
            "towers": dimensions["tower_count"],
            "has_village": include_village,
            "has_siege_weapons": include_siege_weapons,
            "total_actors": total
        }
        return result

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

        logger.info(f"Creating suspension bridge: span={span_length}, width={deck_width}, height={tower_height}")

        sink = DryRunActorSink() if dry_run else UnrealActorSink()

        counts = build_suspension_bridge_structure(
            None,
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
            all_actors=[],
            sink=sink
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        total_actors = sum(counts.values())

        logger.info(f"Bridge construction complete: {total_actors} actors in {elapsed_ms}ms")

        result = sink.flush()
        if dry_run:
            actual_count = len(sink.specs) if hasattr(sink, 'specs') else total_actors
            result["message"] = f"Would spawn {actual_count} actors for suspension bridge."
        else:
            result["message"] = f"Created suspension bridge with {total_actors} components"
        result["metrics"] = {
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
        return result

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

        logger.info(f"Creating aqueduct: {arches} arches, {tiers} tiers, radius={arch_radius}")

        total_length = arches * (2 * arch_radius + pier_width) + pier_width

        sink = DryRunActorSink() if dry_run else UnrealActorSink()
        counts = build_aqueduct_structure(
            None,
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
            all_actors=[],
            sink=sink
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        total_actors = sum(counts.values())

        logger.info(f"Aqueduct construction complete: {total_actors} actors in {elapsed_ms}ms")

        result = sink.flush()
        if dry_run:
            actual_count = len(sink.specs) if hasattr(sink, 'specs') else total_actors
            result["message"] = f"Would spawn {actual_count} actors for aqueduct."
        else:
            result["message"] = f"Created {tiers}-tier aqueduct with {arches} arches ({total_actors} components)"
        result["metrics"] = {
            "total_actors": total_actors,
            "arch_segments": counts["arch_segments"],
            "pier_count": counts["piers"],
            "tiers": tiers,
            "deck_segments": counts["deck_segments"],
            "total_length": total_length,
            "est_area": total_length * deck_width,
            "elapsed_ms": elapsed_ms
        }
        return result

    except Exception as e:
        logger.error(f"create_aqueduct error: {e}")
        return make_error_response(str(e))
