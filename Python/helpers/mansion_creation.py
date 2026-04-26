"""
Mansion Creation Helper Functions for Unreal MCP Server.
Contains logic for building luxurious mansions with multiple wings, grand rooms,
gardens, fountains, and opulent features perfect for dramatic reveals.
"""

import math
from typing import List, Dict, Any, Optional
import logging
from utils.responses import is_success_response

logger = logging.getLogger(__name__)

# Import safe spawning functions
try:
    from .actor_name_manager import safe_spawn_actor
except ImportError:
    logger.warning("Could not import actor_name_manager, using fallback spawning")
    def safe_spawn_actor(unreal_connection, params, auto_unique_name=True):
        return unreal_connection.send_command("spawn_actor", params)

from server.actor_sink import ActorSink, params_to_spec


def _spawn(sink: Optional[ActorSink], unreal, params: Dict[str, Any], tags: List[str], all_actors: List) -> bool:
    """Spawn via sink if provided, otherwise via safe_spawn_actor. Returns True on success."""
    if sink is not None:
        sink.spawn(params_to_spec(params, tags=tags))
        return True
    resp = safe_spawn_actor(unreal, params, auto_unique_name=True)
    if resp and is_success_response(resp):
        all_actors.append(resp.get("result"))
        return True
    return False

def _safe_spawn_mansion_actor(unreal, params):
    """Helper function to safely spawn mansion actors and track results."""
    resp = safe_spawn_actor(unreal, params, auto_unique_name=True)
    return resp


def get_mansion_size_params(mansion_scale: str) -> Dict[str, Any]:
    """Get size parameters for different mansion scales."""
    size_params = {
        "small": {
            "wings": 2, "floors": 2, "main_rooms": 6, "bedrooms": 4,
            "main_width": 2000, "main_depth": 1600, "wing_length": 1800, "wing_width": 1000, 
            "floor_height": 450, "wall_thickness": 30, "garden_size": 4000, 
            "fountain_count": 2, "car_count": 2
        },
        "large": {
            "wings": 3, "floors": 3, "main_rooms": 12, "bedrooms": 8,
            "main_width": 2800, "main_depth": 2200, "wing_length": 2400, "wing_width": 1400, 
            "floor_height": 500, "wall_thickness": 40, "garden_size": 6000, 
            "fountain_count": 4, "car_count": 3
        },
        "epic": {
            "wings": 4, "floors": 4, "main_rooms": 20, "bedrooms": 12,
            "main_width": 3600, "main_depth": 2800, "wing_length": 3000, "wing_width": 1800, 
            "floor_height": 550, "wall_thickness": 50, "garden_size": 8000, 
            "fountain_count": 6, "car_count": 4
        },
        "legendary": {
            "wings": 5, "floors": 5, "main_rooms": 30, "bedrooms": 16,
            "main_width": 4400, "main_depth": 3400, "wing_length": 3600, "wing_width": 2200, 
            "floor_height": 600, "wall_thickness": 60, "garden_size": 10000, 
            "fountain_count": 8, "car_count": 5
        }
    }
    return size_params.get(mansion_scale, size_params["large"])


def calculate_mansion_layout(params: Dict[str, Any], scale_factor: float = 2.0) -> Dict[str, Any]:
    """Calculate scaled mansion layout based on size parameters."""
    return {
        "wings": params["wings"],
        "floors": params["floors"],
        "main_rooms": params["main_rooms"],
        "bedrooms": params["bedrooms"],
        "main_width": int(params["main_width"] * scale_factor),
        "main_depth": int(params["main_depth"] * scale_factor),
        "wing_length": int(params["wing_length"] * scale_factor),
        "wing_width": int(params["wing_width"] * scale_factor),
        "floor_height": int(params["floor_height"] * scale_factor),
        "garden_size": int(params["garden_size"] * scale_factor),
        "fountain_count": params["fountain_count"],
        "car_count": params["car_count"],
        "scale_factor": scale_factor,
        "wall_thickness": int(params["wall_thickness"] * scale_factor),
        "doorway_width": int(300 * scale_factor),
        "window_width": int(200 * scale_factor),
        "window_height": int(250 * scale_factor),
        "window_spacing": int(400 * scale_factor),
        "roof_height": int(300 * scale_factor)
    }


def build_mansion_main_structure(unreal, name_prefix: str, location: List[float],
                                layout: Dict[str, Any], all_actors: List,
                                sink: Optional[ActorSink] = None) -> None:
    """Build the main mansion structure with realistic walls, windows, doors, and roofs."""
    logger.info("Building magnificent mansion main structure...")

    main_width = layout["main_width"]
    main_depth = layout["main_depth"]
    floors = layout["floors"]
    floor_height = layout["floor_height"]
    wall_thickness = layout["wall_thickness"]

    # Build main mansion body (central structure)
    _build_main_mansion_body(unreal, name_prefix, location, layout, all_actors, sink)

    # Build wings extending from main body
    wing_angles = [0, 90, 180, 270][:layout["wings"]]  # East, North, West, South

    for wing_idx, angle in enumerate(wing_angles):
        _build_mansion_wing_realistic(unreal, name_prefix, location, layout, wing_idx, angle, all_actors, sink)

    # Add grand entrance and doorways
    _build_mansion_entrances(unreal, name_prefix, location, layout, all_actors, sink)

    # Add roofs to all structures
    _build_mansion_roofs(unreal, name_prefix, location, layout, all_actors, sink)

    # Add grand staircase inside
    _build_grand_staircase(unreal, name_prefix, location, layout, all_actors, sink)

    # Add rooftop bar deck on stilts
    _build_rooftop_bar_deck(unreal, name_prefix, location, layout, all_actors, sink)


def _build_main_mansion_body(unreal, name_prefix: str, location: List[float],
                            layout: Dict[str, Any], all_actors: List,
                            sink: Optional[ActorSink] = None) -> None:
    """Build the main central mansion body with realistic walls."""
    logger.info("Building main mansion body...")

    main_width = layout["main_width"]
    main_depth = layout["main_depth"]
    floors = layout["floors"]
    floor_height = layout["floor_height"]
    wall_thickness = layout["wall_thickness"]

    # Build floors (foundations)
    for floor in range(floors):
        floor_z = location[2] + floor * floor_height

        # Floor platform
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_MainFloor_{floor}",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], floor_z],
            "scale": [main_width/100, main_depth/100, wall_thickness/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

        # Build walls around perimeter
        _build_perimeter_walls(unreal, name_prefix, location, main_width, main_depth,
                              floor_z, floor_height, wall_thickness, f"Main_F{floor}", all_actors, sink)

        # Add windows to walls
        _add_realistic_windows(unreal, name_prefix, location, main_width, main_depth,
                              floor_z, floor_height, layout, f"Main_F{floor}", all_actors, sink)


def _build_perimeter_walls(unreal, name_prefix: str, location: List[float],
                          width: int, depth: int, floor_z: float, floor_height: int,
                          wall_thickness: int, identifier: str, all_actors: List,
                          sink: Optional[ActorSink] = None) -> None:
    """Build perimeter walls around a rectangular area."""

    walls = [
        (f"{name_prefix}_{identifier}_FrontWall", [location[0], location[1] - depth/2, floor_z + floor_height/2], [width/100, wall_thickness/100, floor_height/100]),
        (f"{name_prefix}_{identifier}_BackWall", [location[0], location[1] + depth/2, floor_z + floor_height/2], [width/100, wall_thickness/100, floor_height/100]),
        (f"{name_prefix}_{identifier}_LeftWall", [location[0] - width/2, location[1], floor_z + floor_height/2], [wall_thickness/100, depth/100, floor_height/100]),
        (f"{name_prefix}_{identifier}_RightWall", [location[0] + width/2, location[1], floor_z + floor_height/2], [wall_thickness/100, depth/100, floor_height/100]),
    ]

    for wall_name, wall_loc, wall_scale in walls:
        _spawn(sink, unreal, {
            "name": wall_name,
            "type": "StaticMeshActor",
            "location": wall_loc,
            "scale": wall_scale,
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def _add_realistic_windows(unreal, name_prefix: str, location: List[float],
                          width: int, depth: int, floor_z: float, floor_height: int,
                          layout: Dict[str, Any], identifier: str, all_actors: List,
                          sink: Optional[ActorSink] = None) -> None:
    """Add realistic windows with proper openings in walls."""

    window_width = layout["window_width"]
    window_height = layout["window_height"]
    window_spacing = layout["window_spacing"]

    num_front_windows = max(1, int(width / window_spacing))
    num_side_windows = max(1, int(depth / window_spacing))

    def _create_window(window_name, loc_x, loc_y, loc_z, scale_x, scale_y, scale_z):
        _spawn(sink, unreal, {
            "name": window_name,
            "type": "StaticMeshActor",
            "location": [loc_x, loc_y, loc_z],
            "scale": [scale_x, scale_y, scale_z],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

    # Windows on front wall
    front_wall_y = location[1] - depth/2
    for i in range(num_front_windows):
        window_x = location[0] - width/2 + (i + 0.5) * (width / num_front_windows)
        _create_window(f"{name_prefix}_{identifier}_FrontWindow_{i}", window_x, front_wall_y, floor_z + floor_height * 0.6, window_width/100, 0.2, window_height/100)

    # Windows on back wall
    back_wall_y = location[1] + depth/2
    for i in range(num_front_windows):
        window_x = location[0] - width/2 + (i + 0.5) * (width / num_front_windows)
        _create_window(f"{name_prefix}_{identifier}_BackWindow_{i}", window_x, back_wall_y, floor_z + floor_height * 0.6, window_width/100, 0.2, window_height/100)

    # Left wall windows
    left_wall_x = location[0] - width/2
    for i in range(num_side_windows):
        window_y = location[1] - depth/2 + (i + 0.5) * (depth / num_side_windows)
        _create_window(f"{name_prefix}_{identifier}_LeftWindow_{i}", left_wall_x, window_y, floor_z + floor_height * 0.6, 0.2, window_width/100, window_height/100)

    # Right wall windows
    right_wall_x = location[0] + width/2
    for i in range(num_side_windows):
        window_y = location[1] - depth/2 + (i + 0.5) * (depth / num_side_windows)
        _create_window(f"{name_prefix}_{identifier}_RightWindow_{i}", right_wall_x, window_y, floor_z + floor_height * 0.6, 0.2, window_width/100, window_height/100)


def _build_mansion_wing_realistic(unreal, name_prefix: str, location: List[float],
                                 layout: Dict[str, Any], wing_idx: int, angle: float,
                                 all_actors: List, sink: Optional[ActorSink] = None) -> None:
    """Build a realistic mansion wing with proper structure."""
    logger.info(f"Building mansion wing {wing_idx} at angle {angle}...")

    wing_length = layout["wing_length"]
    wing_width = layout["wing_width"]
    floors = layout["floors"]
    floor_height = layout["floor_height"]
    wall_thickness = layout["wall_thickness"]

    # Calculate wing position (attached to main body)
    main_width = layout["main_width"]
    main_depth = layout["main_depth"]

    if angle == 0:  # East wing
        wing_center_x = location[0] + main_width/2 + wing_length/2
        wing_center_y = location[1]
    elif angle == 90:  # North wing
        wing_center_x = location[0]
        wing_center_y = location[1] + main_depth/2 + wing_length/2
    elif angle == 180:  # West wing
        wing_center_x = location[0] - main_width/2 - wing_length/2
        wing_center_y = location[1]
    else:  # South wing (270)
        wing_center_x = location[0]
        wing_center_y = location[1] - main_depth/2 - wing_length/2

    # Build wing floors and walls
    for floor in range(floors):
        floor_z = location[2] + floor * floor_height

        # Wing floor
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Wing{wing_idx}_Floor{floor}",
            "type": "StaticMeshActor",
            "location": [wing_center_x, wing_center_y, floor_z],
            "rotation": [0, angle, 0],
            "scale": [wing_length/100, wing_width/100, wall_thickness/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

        # Build wing walls
        _build_perimeter_walls(unreal, name_prefix, [wing_center_x, wing_center_y, 0],
                              wing_length, wing_width, floor_z, floor_height, wall_thickness,
                              f"Wing{wing_idx}_F{floor}", all_actors, sink)

        # Add wing windows
        _add_realistic_windows(unreal, name_prefix, [wing_center_x, wing_center_y, 0],
                              wing_length, wing_width, floor_z, floor_height, layout,
                              f"Wing{wing_idx}_F{floor}", all_actors, sink)


def _build_mansion_entrances(unreal, name_prefix: str, location: List[float],
                            layout: Dict[str, Any], all_actors: List,
                            sink: Optional[ActorSink] = None) -> None:
    """Build grand entrances and doorways."""
    logger.info("Building mansion entrances...")

    main_depth = layout["main_depth"]
    floor_height = layout["floor_height"]
    doorway_width = layout["doorway_width"]

    # Main front entrance (grand door)
    entrance_y = location[1] - main_depth/2
    _spawn(sink, unreal, {
        "name": f"{name_prefix}_GrandEntrance",
        "type": "StaticMeshActor",
        "location": [location[0], entrance_y, location[2] + floor_height * 0.7],
        "scale": [doorway_width/100, 0.3, floor_height * 0.8/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Side entrances for wings
    for wing_idx in range(layout["wings"]):
        if wing_idx == 0:  # East wing entrance
            ent_x = location[0] + layout["main_width"]/2 + 100
            ent_y = location[1]
        elif wing_idx == 1:  # North wing entrance
            ent_x = location[0]
            ent_y = location[1] + layout["main_depth"]/2 + 100
        elif wing_idx == 2:  # West wing entrance
            ent_x = location[0] - layout["main_width"]/2 - 100
            ent_y = location[1]
        else:  # South wing entrance
            ent_x = location[0]
            ent_y = location[1] - layout["main_depth"]/2 - 100

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_WingEntrance_{wing_idx}",
            "type": "StaticMeshActor",
            "location": [ent_x, ent_y, location[2] + floor_height * 0.6],
            "scale": [doorway_width/100 * 0.8, 0.2, floor_height * 0.7/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def _build_mansion_roofs(unreal, name_prefix: str, location: List[float],
                        layout: Dict[str, Any], all_actors: List,
                        sink: Optional[ActorSink] = None) -> None:
    """Build realistic roofs for the mansion."""
    logger.info("Building mansion roofs...")

    main_width = layout["main_width"]
    main_depth = layout["main_depth"]
    floors = layout["floors"]
    floor_height = layout["floor_height"]
    roof_height = layout["roof_height"]

    roof_z = location[2] + floors * floor_height + roof_height/2

    # Main building roof
    _spawn(sink, unreal, {
        "name": f"{name_prefix}_MainRoof",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], roof_z],
        "scale": [main_width/100 * 1.1, main_depth/100 * 1.1, roof_height/100],
        "static_mesh": "/Engine/BasicShapes/Wedge.Wedge"
    }, tags=["mansion"], all_actors=all_actors)

    # Wing roofs
    wing_length = layout["wing_length"]
    wing_width = layout["wing_width"]

    for wing_idx in range(layout["wings"]):
        angle = wing_idx * 90

        if angle == 0:  # East wing
            roof_x = location[0] + main_width/2 + wing_length/2
            roof_y = location[1]
        elif angle == 90:  # North wing
            roof_x = location[0]
            roof_y = location[1] + main_depth/2 + wing_length/2
        elif angle == 180:  # West wing
            roof_x = location[0] - main_width/2 - wing_length/2
            roof_y = location[1]
        else:  # South wing
            roof_x = location[0]
            roof_y = location[1] - main_depth/2 - wing_length/2

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Wing{wing_idx}_Roof",
            "type": "StaticMeshActor",
            "location": [roof_x, roof_y, roof_z - roof_height/4],
            "rotation": [0, angle, 0],
            "scale": [wing_length/100 * 1.1, wing_width/100 * 1.1, roof_height/100 * 0.8],
            "static_mesh": "/Engine/BasicShapes/Wedge.Wedge"
        }, tags=["mansion"], all_actors=all_actors)


def _build_grand_staircase(unreal, name_prefix: str, location: List[float],
                          layout: Dict[str, Any], all_actors: List,
                          sink: Optional[ActorSink] = None) -> None:
    """Build an epic grand staircase in the central core."""
    logger.info("Building magnificent grand staircase...")

    floors = layout["floors"]
    floor_height = layout["floor_height"]
    wing_width = layout["wing_width"]

    # Main staircase structure
    staircase_width = wing_width * 0.6
    staircase_depth = wing_width * 0.4
    staircase_height = floors * floor_height

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_GrandStaircase",
        "type": "StaticMeshActor",
        "location": [location[0], location[1] + staircase_depth/2, location[2] + staircase_height/2],
        "scale": [staircase_width/100, staircase_depth/100, staircase_height/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Individual staircase steps
    steps_per_floor = 8
    total_steps = floors * steps_per_floor

    for step in range(total_steps):
        step_z = location[2] + (step + 0.5) * (staircase_height / total_steps)
        step_depth = staircase_depth * (1 - step/total_steps * 0.3)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_StairStep_{step}",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] + step_depth/2, step_z],
            "scale": [staircase_width/100, step_depth/100, staircase_height/total_steps/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def _build_rooftop_bar_deck(unreal, name_prefix: str, location: List[float],
                           layout: Dict[str, Any], all_actors: List,
                           sink: Optional[ActorSink] = None) -> None:
    """Build a spectacular rooftop bar deck on stilts above the mansion."""
    logger.info("Building spectacular rooftop bar deck on stilts...")

    main_width = layout["main_width"]
    main_depth = layout["main_depth"]
    floors = layout["floors"]
    floor_height = layout["floor_height"]

    # Calculate rooftop deck position - well above the main roof
    deck_height = location[2] + floors * floor_height + floor_height * 2
    deck_width = main_width * 1.4  # Larger than main building
    deck_depth = main_depth * 1.2
    deck_thickness = 40

    # Main deck platform
    _spawn(sink, unreal, {
        "name": f"{name_prefix}_RooftopDeck",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], deck_height],
        "scale": [deck_width/100, deck_depth/100, deck_thickness/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Support stilts/pillars
    ceiling_height = location[2] + floors * floor_height
    deck_bottom_height = deck_height - deck_thickness / 2
    stilt_height = max(1.0, deck_bottom_height - ceiling_height)
    stilt_center_height = ceiling_height + stilt_height / 2

    stilt_positions = [
        [location[0] - deck_width * 0.3, location[1] - deck_depth * 0.3],
        [location[0] + deck_width * 0.3, location[1] - deck_depth * 0.3],
        [location[0] - deck_width * 0.3, location[1] + deck_depth * 0.3],
        [location[0] + deck_width * 0.3, location[1] + deck_depth * 0.3],
        [location[0], location[1] - deck_depth * 0.3],
        [location[0], location[1] + deck_depth * 0.3],
        [location[0] - deck_width * 0.3, location[1]],
        [location[0] + deck_width * 0.3, location[1]]
    ]

    for i, pos in enumerate(stilt_positions):
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_DeckStilt_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], stilt_center_height],
            "scale": [1.2, 1.2, stilt_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

    # Deck railings around perimeter
    railing_height = 150
    railing_segments = 32

    for i in range(railing_segments):
        if i < 8:
            railing_x = location[0] - deck_width/2 + (i + 0.5) * (deck_width/8)
            railing_y = location[1] - deck_depth/2
        elif i < 16:
            railing_x = location[0] + deck_width/2
            railing_y = location[1] - deck_depth/2 + ((i-8) + 0.5) * (deck_depth/8)
        elif i < 24:
            railing_x = location[0] + deck_width/2 - ((i-16) + 0.5) * (deck_width/8)
            railing_y = location[1] + deck_depth/2
        else:
            railing_x = location[0] - deck_width/2
            railing_y = location[1] + deck_depth/2 - ((i-24) + 0.5) * (deck_depth/8)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_DeckRailing_{i}",
            "type": "StaticMeshActor",
            "location": [railing_x, railing_y, deck_height + railing_height/2],
            "scale": [0.3, 0.3, railing_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

    # Bar counter
    bar_x = location[0] - deck_width * 0.25
    bar_y = location[1]
    _spawn(sink, unreal, {
        "name": f"{name_prefix}_RooftopBar",
        "type": "StaticMeshActor",
        "location": [bar_x, bar_y, deck_height + 120],
        "scale": [8.0, 3.0, 2.4],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Lounge seating areas
    seating_positions = [
        [location[0] + deck_width * 0.2, location[1] - deck_depth * 0.2],
        [location[0] + deck_width * 0.2, location[1] + deck_depth * 0.2],
        [location[0] - deck_width * 0.15, location[1] - deck_depth * 0.3],
        [location[0] - deck_width * 0.15, location[1] + deck_depth * 0.3]
    ]

    for i, pos in enumerate(seating_positions):
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_RooftopSeating_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], deck_height + 40],
            "scale": [2.5, 2.5, 0.8],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

    # Decorative elements - umbrellas/shade structures
    umbrella_positions = [
        [location[0] + deck_width * 0.3, location[1]],
        [location[0] - deck_width * 0.05, location[1] + deck_depth * 0.25]
    ]

    for i, pos in enumerate(umbrella_positions):
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_RooftopUmbrella_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], deck_height + 300],
            "scale": [4.0, 4.0, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)


def build_mansion_exterior(unreal, name_prefix: str, location: List[float],
                          layout: Dict[str, Any], all_actors: List,
                          sink: Optional[ActorSink] = None) -> None:
    """Build mansion exterior features: gardens, driveway, gates."""
    logger.info("Building luxurious mansion exterior...")

    _build_driveway(unreal, name_prefix, location, layout, all_actors, sink)
    _build_front_gates(unreal, name_prefix, location, layout, all_actors, sink)
    _build_gardens(unreal, name_prefix, location, layout, all_actors, sink)
    _build_fountains(unreal, name_prefix, location, layout, all_actors, sink)
    _build_garage(unreal, name_prefix, location, layout, all_actors, sink)


def _build_driveway(unreal, name_prefix: str, location: List[float],
                   layout: Dict[str, Any], all_actors: List,
                   sink: Optional[ActorSink] = None) -> None:
    """Build a magnificent grand curved driveway with sweeping curves."""
    logger.info("Building magnificent grand curved driveway...")

    garden_size = layout["garden_size"]
    main_depth = layout["main_depth"]
    driveway_radius = garden_size * 0.45
    approach_distance = garden_size * 1.2

    # Build main curved driveway
    segments = 64
    for i in range(segments):
        angle = (2.5 * math.pi * i) / segments
        radius_variation = driveway_radius * (0.8 + 0.3 * math.sin(angle * 2))
        drive_x = location[0] + math.cos(angle) * radius_variation
        drive_y = location[1] + math.sin(angle) * radius_variation
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Driveway_{i}",
            "type": "StaticMeshActor",
            "location": [drive_x, drive_y, location[2] - 10],
            "scale": [4.5, 4.5, 0.25],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

    # Approach road
    approach_road_width = 400
    road_segments = int(approach_distance / 300)
    approach_start_y = location[1] + driveway_radius + 200
    for i in range(road_segments):
        road_y = approach_start_y + i * 300
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_ApproachRoad_{i}",
            "type": "StaticMeshActor",
            "location": [location[0], road_y, location[2] - 5],
            "scale": [approach_road_width/100, 3.0, 0.15],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

    # Connecting paths
    entrance_y = location[1] - main_depth/2
    connection_segments = int(abs(entrance_y - (location[1] - driveway_radius)) / 150)
    for i in range(connection_segments):
        segment_y = location[1] - driveway_radius - i * 150
        if segment_y > entrance_y:
            _spawn(sink, unreal, {
                "name": f"{name_prefix}_DriveConnection_{i}",
                "type": "StaticMeshActor",
                "location": [location[0], segment_y, location[2] - 5],
                "scale": [3.0, 1.5, 0.15],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, tags=["mansion"], all_actors=all_actors)


def _build_front_gates(unreal, name_prefix: str, location: List[float],
                      layout: Dict[str, Any], all_actors: List,
                      sink: Optional[ActorSink] = None) -> None:
    """Build ornate front gates."""
    logger.info("Building ornate front gates...")

    garden_size = layout["garden_size"]
    gate_width = layout["wing_width"] * 0.8
    gate_height = layout["floor_height"] * 1.5

    # Gate pillars
    for side in [-1, 1]:
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_GatePillar_{side}",
            "type": "StaticMeshActor",
            "location": [
                location[0] - garden_size * 0.4,
                location[1] + side * gate_width/2,
                location[2] + gate_height/2
            ],
            "scale": [2.0, 2.0, gate_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

    # Gate doors
    for side in [-1, 1]:
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_GateDoor_{side}",
            "type": "StaticMeshActor",
            "location": [
                location[0] - garden_size * 0.4,
                location[1] + side * gate_width/4,
                location[2] + gate_height * 0.6
            ],
            "scale": [0.3, gate_width/100 * 0.4, gate_height/100 * 1.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def _build_gardens(unreal, name_prefix: str, location: List[float],
                  layout: Dict[str, Any], all_actors: List,
                  sink: Optional[ActorSink] = None) -> None:
    """Build landscaped gardens with hedges and flower beds."""
    logger.info("Building landscaped gardens...")

    garden_size = layout["garden_size"]

    # Garden border hedges
    hedge_radius = garden_size * 0.8
    hedge_segments = 24

    for i in range(hedge_segments):
        angle = (2 * math.pi * i) / hedge_segments
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_GardenHedge_{i}",
            "type": "StaticMeshActor",
            "location": [location[0] + math.cos(angle) * hedge_radius, location[1] + math.sin(angle) * hedge_radius, location[2] + 50],
            "scale": [3.0, 3.0, 1.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

    # Flower beds
    bed_positions = [
        [location[0] - garden_size * 0.3, location[1] - garden_size * 0.3],
        [location[0] + garden_size * 0.3, location[1] - garden_size * 0.3],
        [location[0] - garden_size * 0.3, location[1] + garden_size * 0.3],
        [location[0] + garden_size * 0.3, location[1] + garden_size * 0.3]
    ]

    for i, pos in enumerate(bed_positions):
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_FlowerBed_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], location[2] + 25],
            "scale": [4.0, 4.0, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)


def _build_fountains(unreal, name_prefix: str, location: List[float],
                    layout: Dict[str, Any], all_actors: List,
                    sink: Optional[ActorSink] = None) -> None:
    """Build ornate fountains throughout the gardens."""
    logger.info("Building ornate fountains...")

    garden_size = layout["garden_size"]
    fountain_count = layout["fountain_count"]

    for i in range(fountain_count):
        angle = (2 * math.pi * i) / fountain_count
        fountain_radius = garden_size * (0.2 + 0.3 * (i / fountain_count))
        fountain_x = location[0] + math.cos(angle) * fountain_radius
        fountain_y = location[1] + math.sin(angle) * fountain_radius

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainBase_{i}",
            "type": "StaticMeshActor",
            "location": [fountain_x, fountain_y, location[2] + 100],
            "scale": [3.0, 3.0, 2.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainStatue_{i}",
            "type": "StaticMeshActor",
            "location": [fountain_x, fountain_y, location[2] + 250],
            "scale": [1.5, 1.5, 3.0],
            "static_mesh": "/Engine/BasicShapes/Cone.Cone"
        }, tags=["mansion"], all_actors=all_actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainBasin_{i}",
            "type": "StaticMeshActor",
            "location": [fountain_x, fountain_y, location[2] + 50],
            "scale": [4.0, 4.0, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, tags=["mansion"], all_actors=all_actors)


def _build_garage(unreal, name_prefix: str, location: List[float],
                 layout: Dict[str, Any], all_actors: List,
                 sink: Optional[ActorSink] = None) -> None:
    """Build a luxury garage with cars."""
    logger.info("Building luxury garage and cars...")

    wing_length = layout["wing_length"]
    car_count = layout["car_count"]
    garage_x = location[0] + wing_length * 0.8
    garage_y = location[1] - wing_length * 0.4

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_Garage",
        "type": "StaticMeshActor",
        "location": [garage_x, garage_y, location[2] + layout["floor_height"]/2],
        "scale": [6.0, 8.0, layout["floor_height"]/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Garage doors
    for door in range(3):
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_GarageDoor_{door}",
            "type": "StaticMeshActor",
            "location": [garage_x - 300 + door * 300, garage_y - 420, location[2] + layout["floor_height"] * 0.6],
            "scale": [2.5, 0.2, 2.5],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

    # Luxury cars
    for car in range(car_count):
        car_x = garage_x - 200 + (car % 2) * 400
        car_y = garage_y + 100 - (car // 2) * 300
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_LuxuryCar_{car}",
            "type": "StaticMeshActor",
            "location": [car_x, car_y, location[2] + 80],
            "rotation": [0, 90 if car % 2 == 1 else 0, 0],
            "scale": [3.0, 1.5, 1.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def add_mansion_interior(unreal, name_prefix: str, location: List[float],
                        layout: Dict[str, Any], all_actors: List,
                        sink: Optional[ActorSink] = None) -> None:
    """Add luxurious interior features and furniture."""
    logger.info("Adding luxurious mansion interior...")

    _build_ballroom(unreal, name_prefix, location, layout, all_actors, sink)
    _build_dining_room(unreal, name_prefix, location, layout, all_actors, sink)
    _build_library(unreal, name_prefix, location, layout, all_actors, sink)
    _build_bedrooms(unreal, name_prefix, location, layout, all_actors, sink)


def _build_ballroom(unreal, name_prefix: str, location: List[float],
                   layout: Dict[str, Any], all_actors: List,
                   sink: Optional[ActorSink] = None) -> None:
    """Build a magnificent ballroom."""
    logger.info("Building grand ballroom...")

    wing_width = layout["wing_width"]
    floor_height = layout["floor_height"]

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_Ballroom",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], location[2] + floor_height * 2.5],
        "scale": [wing_width/100 * 0.8, wing_width/100 * 0.8, floor_height/100 * 2],
        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
    }, tags=["mansion"], all_actors=all_actors)

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_GrandChandelier",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], location[2] + floor_height * 4],
        "scale": [2.0, 2.0, 3.0],
        "static_mesh": "/Engine/BasicShapes/Sphere.Sphere"
    }, tags=["mansion"], all_actors=all_actors)


def _build_dining_room(unreal, name_prefix: str, location: List[float],
                      layout: Dict[str, Any], all_actors: List,
                      sink: Optional[ActorSink] = None) -> None:
    """Build an elegant dining room."""
    logger.info("Building elegant dining room...")

    wing_length = layout["wing_length"]
    floor_height = layout["floor_height"]

    dining_x = location[0] + wing_length * 0.3
    dining_y = location[1] - wing_length * 0.2

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_DiningRoom",
        "type": "StaticMeshActor",
        "location": [dining_x, dining_y, location[2] + floor_height * 1.5],
        "scale": [4.0, 6.0, floor_height/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_DiningTable",
        "type": "StaticMeshActor",
        "location": [dining_x, dining_y, location[2] + floor_height + 75],
        "scale": [3.0, 1.0, 0.3],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)


def _build_library(unreal, name_prefix: str, location: List[float],
                  layout: Dict[str, Any], all_actors: List,
                  sink: Optional[ActorSink] = None) -> None:
    """Build a magnificent library."""
    logger.info("Building magnificent library...")

    wing_length = layout["wing_length"]
    floor_height = layout["floor_height"]

    library_x = location[0] - wing_length * 0.3
    library_y = location[1] + wing_length * 0.2

    _spawn(sink, unreal, {
        "name": f"{name_prefix}_Library",
        "type": "StaticMeshActor",
        "location": [library_x, library_y, location[2] + floor_height * 1.5],
        "scale": [5.0, 4.0, floor_height/100 * 2],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, tags=["mansion"], all_actors=all_actors)

    # Bookshelves
    for shelf in range(12):
        shelf_angle = shelf * 30
        shelf_rad = math.radians(shelf_angle)
        shelf_x = library_x + math.cos(shelf_rad) * 300
        shelf_y = library_y + math.sin(shelf_rad) * 300

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Bookshelf_{shelf}",
            "type": "StaticMeshActor",
            "location": [shelf_x, shelf_y, location[2] + floor_height * 1.5],
            "rotation": [0, shelf_angle, 0],
            "scale": [2.0, 0.5, floor_height/100 * 2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)


def _build_bedrooms(unreal, name_prefix: str, location: List[float],
                   layout: Dict[str, Any], all_actors: List,
                   sink: Optional[ActorSink] = None) -> None:
    """Build luxurious bedrooms."""
    logger.info("Building luxurious bedrooms...")

    wing_length = layout["wing_length"]
    floor_height = layout["floor_height"]
    bedrooms = layout["bedrooms"]

    bedroom_positions = []
    for floor in range(layout["floors"]):
        for wing in range(layout["wings"]):
            bedroom_positions.append((floor, wing))

    for i, (floor, wing) in enumerate(bedroom_positions[:bedrooms]):
        wing_angle = wing * 90
        rad_angle = math.radians(wing_angle)
        dir_x = math.cos(rad_angle)
        dir_y = math.sin(rad_angle)

        bedroom_x = location[0] + dir_x * wing_length * 0.6
        bedroom_y = location[1] + dir_y * wing_length * 0.6
        bedroom_z = location[2] + floor * floor_height + floor_height * 1.5

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Bedroom_{i}",
            "type": "StaticMeshActor",
            "location": [bedroom_x, bedroom_y, bedroom_z],
            "scale": [3.0, 3.0, floor_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Bed_{i}",
            "type": "StaticMeshActor",
            "location": [bedroom_x, bedroom_y, bedroom_z],
            "scale": [2.0, 1.5, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, tags=["mansion"], all_actors=all_actors)