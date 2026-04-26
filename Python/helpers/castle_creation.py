"""
Castle creation helper functions for Unreal MCP Server.
Contains logic for building complex castle fortresses with walls, towers, and villages.
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


def _castle_spawn(sink, unreal, params, all_actors):
    """Convenience wrapper for castle actors with default 'castle' tag."""
    return _spawn(sink, unreal, params, tags=["castle"], all_actors=all_actors)


def get_castle_size_params(castle_size: str) -> Dict[str, int]:
    """Get size parameters for different castle sizes."""
    size_params = {
        "small": {
            "outer_width": 6000, "outer_depth": 6000,
            "inner_width": 3000, "inner_depth": 3000,
            "wall_height": 800, "tower_count": 8, "tower_height": 1200
        },
        "medium": {
            "outer_width": 8000, "outer_depth": 8000,
            "inner_width": 4000, "inner_depth": 4000,
            "wall_height": 1000, "tower_count": 12, "tower_height": 1600
        },
        "large": {
            "outer_width": 12000, "outer_depth": 12000,
            "inner_width": 6000, "inner_depth": 6000,
            "wall_height": 1200, "tower_count": 16, "tower_height": 2000
        },
        "epic": {
            "outer_width": 16000, "outer_depth": 16000,
            "inner_width": 8000, "inner_depth": 8000,
            "wall_height": 1600, "tower_count": 24, "tower_height": 2800
        }
    }
    return size_params.get(castle_size, size_params["large"])


def calculate_scaled_dimensions(params: Dict[str, int], scale_factor: float = 2.0) -> Dict[str, int]:
    """Calculate scaled dimensions based on size parameters and scale factor."""
    complexity_multiplier = max(1, int(round(scale_factor)))

    return {
        "outer_width": int(params["outer_width"] * scale_factor),
        "outer_depth": int(params["outer_depth"] * scale_factor),
        "inner_width": int(params["inner_width"] * scale_factor),
        "inner_depth": int(params["inner_depth"] * scale_factor),
        "wall_height": int(params["wall_height"] * scale_factor),
        "tower_count": int(params["tower_count"] * complexity_multiplier),
        "tower_height": int(params["tower_height"] * scale_factor),
        "complexity_multiplier": complexity_multiplier,
        "gate_tower_offset": int(700 * scale_factor),
        "barbican_offset": int(400 * scale_factor),
        "drawbridge_offset": int(600 * scale_factor),
        "wall_thickness": int(300 * max(1.0, scale_factor * 0.75))
    }


def build_outer_bailey_walls(unreal, name_prefix: str, location: List[float],
                           dimensions: Dict[str, int], all_actors: List,
                           sink: Optional[ActorSink] = None) -> None:
    """Build the outer bailey walls with battlements."""
    logger.info("Constructing massive outer bailey walls...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    wall_height = dimensions["wall_height"]
    wall_thickness = dimensions["wall_thickness"]

    # North wall
    for i in range(int(outer_width / 200)):
        wall_x = location[0] - outer_width/2 + i * 200 + 100
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_WallNorth_{i}",
            "type": "StaticMeshActor",
            "location": [wall_x, location[1] - outer_depth/2, location[2] + wall_height/2],
            "scale": [2.0, wall_thickness/100, wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        if i % 2 == 0:
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_BattlementNorth_{i}",
                "type": "StaticMeshActor",
                "location": [wall_x, location[1] - outer_depth/2, location[2] + wall_height + 50],
                "scale": [1.0, wall_thickness/100, 1.0],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

    # South wall
    for i in range(int(outer_width / 200)):
        wall_x = location[0] - outer_width/2 + i * 200 + 100
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_WallSouth_{i}",
            "type": "StaticMeshActor",
            "location": [wall_x, location[1] + outer_depth/2, location[2] + wall_height/2],
            "scale": [2.0, wall_thickness/100, wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        if i % 2 == 0:
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_BattlementSouth_{i}",
                "type": "StaticMeshActor",
                "location": [wall_x, location[1] + outer_depth/2, location[2] + wall_height + 50],
                "scale": [1.0, wall_thickness/100, 1.0],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

    # East wall
    for i in range(int(outer_depth / 200)):
        wall_y = location[1] - outer_depth/2 + i * 200 + 100
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_WallEast_{i}",
            "type": "StaticMeshActor",
            "location": [location[0] + outer_width/2, wall_y, location[2] + wall_height/2],
            "scale": [wall_thickness/100, 2.0, wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

    # West wall with main gate
    for i in range(int(outer_depth / 200)):
        wall_y = location[1] - outer_depth/2 + i * 200 + 100
        if abs(wall_y - location[1]) > 700:
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_WallWest_{i}",
                "type": "StaticMeshActor",
                "location": [location[0] - outer_width/2, wall_y, location[2] + wall_height/2],
                "scale": [wall_thickness/100, 2.0, wall_height/100],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)


def build_inner_bailey_walls(unreal, name_prefix: str, location: List[float],
                           dimensions: Dict[str, int], all_actors: List,
                           sink: Optional[ActorSink] = None) -> None:
    """Build the inner bailey walls (higher and stronger)."""
    logger.info("Building inner bailey fortifications...")

    inner_width = dimensions["inner_width"]
    inner_depth = dimensions["inner_depth"]
    wall_thickness = dimensions["wall_thickness"]
    inner_wall_height = dimensions["wall_height"] * 1.3

    # Inner North wall
    for i in range(int(inner_width / 200)):
        wall_x = location[0] - inner_width/2 + i * 200 + 100
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerWallNorth_{i}",
            "type": "StaticMeshActor",
            "location": [wall_x, location[1] - inner_depth/2, location[2] + inner_wall_height/2],
            "scale": [2.0, wall_thickness/100, inner_wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

    # Inner South wall
    for i in range(int(inner_width / 200)):
        wall_x = location[0] - inner_width/2 + i * 200 + 100
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerWallSouth_{i}",
            "type": "StaticMeshActor",
            "location": [wall_x, location[1] + inner_depth/2, location[2] + inner_wall_height/2],
            "scale": [2.0, wall_thickness/100, inner_wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

    # Inner East and West walls
    for i in range(int(inner_depth / 200)):
        wall_y = location[1] - inner_depth/2 + i * 200 + 100

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerWallEast_{i}",
            "type": "StaticMeshActor",
            "location": [location[0] + inner_width/2, wall_y, location[2] + inner_wall_height/2],
            "scale": [wall_thickness/100, 2.0, inner_wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerWallWest_{i}",
            "type": "StaticMeshActor",
            "location": [location[0] - inner_width/2, wall_y, location[2] + inner_wall_height/2],
            "scale": [wall_thickness/100, 2.0, inner_wall_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)


def build_gate_complex(unreal, name_prefix: str, location: List[float],
                      dimensions: Dict[str, int], all_actors: List,
                      sink: Optional[ActorSink] = None) -> None:
    """Build the massive main gate complex."""
    logger.info("Building elaborate main gate complex...")

    outer_width = dimensions["outer_width"]
    inner_width = dimensions["inner_width"]
    tower_height = dimensions["tower_height"]
    wall_height = dimensions["wall_height"]
    gate_tower_offset = dimensions["gate_tower_offset"]
    barbican_offset = dimensions["barbican_offset"]

    for side in [-1, 1]:
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_GateTower_{side}",
            "type": "StaticMeshActor",
            "location": [location[0] - outer_width/2, location[1] + side * gate_tower_offset, location[2] + tower_height/2],
            "scale": [4.0, 4.0, tower_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_GateTowerTop_{side}",
            "type": "StaticMeshActor",
            "location": [location[0] - outer_width/2, location[1] + side * gate_tower_offset, location[2] + tower_height + 200],
            "scale": [5.0, 5.0, 0.8],
            "static_mesh": "/Engine/BasicShapes/Cone.Cone"
        }, all_actors)

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_Barbican",
        "type": "StaticMeshActor",
        "location": [location[0] - outer_width/2 - barbican_offset, location[1], location[2] + wall_height/2],
        "scale": [8.0, 12.0, wall_height/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_Portcullis",
        "type": "StaticMeshActor",
        "location": [location[0] - outer_width/2, location[1], location[2] + 200],
        "scale": [0.5, 12.0, 8.0],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_InnerPortcullis",
        "type": "StaticMeshActor",
        "location": [location[0] - inner_width/2, location[1], location[2] + 200],
        "scale": [0.5, 8.0, 6.0],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)


def get_corner_positions(location: List[float], width: int, depth: int) -> List[List[float]]:
    """Get corner positions for towers."""
    return [
        [location[0] - width/2, location[1] - depth/2],  # NW
        [location[0] + width/2, location[1] - depth/2],  # NE
        [location[0] + width/2, location[1] + depth/2],  # SE
        [location[0] - width/2, location[1] + depth/2],  # SW
    ]


def build_corner_towers(unreal, name_prefix: str, location: List[float],
                       dimensions: Dict[str, int], architectural_style: str, all_actors: List,
                       sink: Optional[ActorSink] = None) -> None:
    """Build massive corner towers for outer bailey."""
    logger.info("Constructing massive corner towers...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    tower_height = dimensions["tower_height"]

    outer_corners = get_corner_positions(location, outer_width, outer_depth)

    for i, corner in enumerate(outer_corners):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_TowerBase_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + 150],
            "scale": [6.0, 6.0, 3.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_Tower_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + tower_height/2],
            "scale": [5.0, 5.0, tower_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        if architectural_style in ["medieval", "fantasy"]:
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_TowerTop_{i}",
                "type": "StaticMeshActor",
                "location": [corner[0], corner[1], location[2] + tower_height + 150],
                "scale": [6.0, 6.0, 2.5],
                "static_mesh": "/Engine/BasicShapes/Cone.Cone"
            }, all_actors)

        for window_level in range(5):
            window_height = location[2] + 300 + window_level * 300
            for angle in [0, 90, 180, 270]:
                window_x = corner[0] + 350 * math.cos(angle * math.pi / 180)
                window_y = corner[1] + 350 * math.sin(angle * math.pi / 180)
                _castle_spawn(sink, unreal, {
                    "name": f"{name_prefix}_TowerWindow_{i}_{window_level}_{angle}",
                    "type": "StaticMeshActor",
                    "location": [window_x, window_y, window_height],
                    "rotation": [0, angle, 0],
                    "scale": [0.3, 0.5, 0.8],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube"
                }, all_actors)


def build_inner_corner_towers(unreal, name_prefix: str, location: List[float],
                             dimensions: Dict[str, int], all_actors: List,
                             sink: Optional[ActorSink] = None) -> None:
    """Build inner bailey corner towers (even more massive)."""
    logger.info("Building inner bailey towers...")

    inner_width = dimensions["inner_width"]
    inner_depth = dimensions["inner_depth"]
    tower_height = dimensions["tower_height"]

    inner_corners = get_corner_positions(location, inner_width, inner_depth)

    for i, corner in enumerate(inner_corners):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerTowerBase_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + 200],
            "scale": [8.0, 8.0, 4.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        inner_tower_height = tower_height * 1.4
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerTower_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + inner_tower_height/2],
            "scale": [6.0, 6.0, inner_tower_height/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_InnerTowerTop_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + inner_tower_height + 200],
            "scale": [8.0, 8.0, 3.0],
            "static_mesh": "/Engine/BasicShapes/Cone.Cone"
        }, all_actors)


def build_intermediate_towers(unreal, name_prefix: str, location: List[float],
                            dimensions: Dict[str, int], all_actors: List,
                            sink: Optional[ActorSink] = None) -> None:
    """Add intermediate towers along walls."""
    logger.info("Adding intermediate wall towers...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    tower_height = dimensions["tower_height"]
    complexity_multiplier = dimensions["complexity_multiplier"]

    for i in range(max(3, 3 * complexity_multiplier)):
        tower_x = location[0] - outer_width/4 + i * outer_width/4
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_NorthWallTower_{i}",
            "type": "StaticMeshActor",
            "location": [tower_x, location[1] - outer_depth/2, location[2] + tower_height * 0.8/2],
            "scale": [3.0, 3.0, tower_height * 0.8/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

    for i in range(max(3, 3 * complexity_multiplier)):
        tower_x = location[0] - outer_width/4 + i * outer_width/4
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_SouthWallTower_{i}",
            "type": "StaticMeshActor",
            "location": [tower_x, location[1] + outer_depth/2, location[2] + tower_height * 0.8/2],
            "scale": [3.0, 3.0, tower_height * 0.8/100],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)


def build_central_keep(unreal, name_prefix: str, location: List[float],
                      dimensions: Dict[str, int], all_actors: List,
                      sink: Optional[ActorSink] = None) -> None:
    """Build the massive central keep complex."""
    logger.info("Building enormous central keep complex...")

    inner_width = dimensions["inner_width"]
    inner_depth = dimensions["inner_depth"]
    tower_height = dimensions["tower_height"]

    keep_width = inner_width * 0.6
    keep_depth = inner_depth * 0.6
    keep_height = tower_height * 2.0

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_KeepBase",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], location[2] + keep_height/2],
        "scale": [keep_width/100, keep_depth/100, keep_height/100],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)

    keep_spire_height = max(1200.0, tower_height * 1.0)
    keep_top_z = location[2] + keep_height
    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_KeepTower",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], keep_top_z + keep_spire_height / 2.0],
        "scale": [4.0, 4.0, keep_spire_height / 100.0],
        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
    }, all_actors)

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_GreatHall",
        "type": "StaticMeshActor",
        "location": [location[0], location[1] + keep_depth/3, location[2] + 200],
        "scale": [keep_width/100 * 0.8, keep_depth/100 * 0.5, 6.0],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)

    logger.info("Adding keep corner towers...")
    keep_corners = [
        [location[0] - keep_width/3, location[1] - keep_depth/3],
        [location[0] + keep_width/3, location[1] - keep_depth/3],
        [location[0] + keep_width/3, location[1] + keep_depth/3],
        [location[0] - keep_width/3, location[1] + keep_depth/3],
    ]

    for i, corner in enumerate(keep_corners):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_KeepCornerTower_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + keep_height * 0.8],
            "scale": [3.0, 3.0, keep_height/100 * 0.8],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)


def build_courtyard_complex(unreal, name_prefix: str, location: List[float],
                          dimensions: Dict[str, int], all_actors: List,
                          sink: Optional[ActorSink] = None) -> None:
    """Build massive inner courtyard complex with various buildings."""
    logger.info("Adding massive courtyard complex...")

    inner_width = dimensions["inner_width"]
    inner_depth = dimensions["inner_depth"]

    buildings = [
        ("Stables", [-inner_width/3, inner_depth/3, 150], [8.0, 4.0, 3.0]),
        ("Barracks", [inner_width/3, inner_depth/3, 150], [10.0, 6.0, 3.0]),
        ("Blacksmith", [inner_width/3, -inner_depth/3, 100], [6.0, 6.0, 2.0]),
        ("Well", [-inner_width/4, 0, 50], [3.0, 3.0, 2.0]),
        ("Armory", [-inner_width/3, -inner_depth/3, 150], [6.0, 4.0, 3.0]),
        ("Chapel", [0, -inner_depth/3, 200], [8.0, 5.0, 4.0]),
        ("Kitchen", [-inner_width/4, inner_depth/4, 120], [5.0, 4.0, 2.5]),
        ("Treasury", [inner_width/4, inner_depth/4, 100], [3.0, 3.0, 2.0]),
        ("Granary", [inner_width/4, -inner_depth/4, 180], [4.0, 6.0, 3.5]),
        ("GuardHouse", [-inner_width/4, -inner_depth/4, 150], [4.0, 4.0, 3.0])
    ]

    for building_name, offset, scale in buildings:
        mesh_type = "/Engine/BasicShapes/Cylinder.Cylinder" if building_name == "Well" else "/Engine/BasicShapes/Cube.Cube"
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_{building_name}",
            "type": "StaticMeshActor",
            "location": [location[0] + offset[0], location[1] + offset[1], location[2] + offset[2]],
            "scale": scale,
            "static_mesh": mesh_type
        }, all_actors)


def build_bailey_annexes(unreal, name_prefix: str, location: List[float],
                        dimensions: Dict[str, int], all_actors: List,
                        sink: Optional[ActorSink] = None) -> None:
    """Fill outer bailey with smaller annex structures and walkways."""
    logger.info("Populating bailey with annex rooms and walkways...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    scale_factor = 2.0

    annex_depth = int(500 * max(1.0, scale_factor))
    annex_width = int(700 * max(1.0, scale_factor))
    annex_height = int(300 * max(1.0, scale_factor))
    walkway_height = 160
    walkway_width = int(300 * max(1.0, scale_factor))
    spacing = int(1200 * max(1.0, scale_factor))

    def _spawn_annex_row(start_x: float, end_x: float, fixed_y: float, align: str, base_name: str):
        count = 0
        x = start_x
        while (x <= end_x and start_x <= end_x) or (x >= end_x and start_x > end_x):
            annex_x = x
            annex_y = fixed_y
            if align == "north":
                annex_y += walkway_width
            elif align == "south":
                annex_y -= walkway_width
            elif align == "east":
                annex_x -= walkway_width
            elif align == "west":
                annex_x += walkway_width

            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_{base_name}_{count}",
                "type": "StaticMeshActor",
                "location": [annex_x, annex_y, location[2] + annex_height/2],
                "scale": [annex_width/100, annex_depth/100, annex_height/100],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

            arch_offset = 0 if align in ["north", "south"] else (annex_width * 0.25)
            door_x = annex_x + (50 if align == "east" else (-50 if align == "west" else arch_offset))
            door_y = annex_y + (50 if align == "south" else (-50 if align == "north" else 0))
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_{base_name}_{count}_Door",
                "type": "StaticMeshActor",
                "location": [door_x, door_y, location[2] + 120],
                "scale": [1.0, 0.6, 2.4],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
            }, all_actors)

            x += spacing if start_x <= end_x else -spacing
            count += 1

    # Build perimeter walkways
    walkway_z = location[2] + 100
    for side, fixed_y in [("north", location[1] - outer_depth/2 + walkway_width/2),
                          ("south", location[1] + outer_depth/2 - walkway_width/2)]:
        segments = int(outer_width / 400)
        for i in range(segments):
            seg_x = location[0] - outer_width/2 + (i * 400) + 200
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_Walkway_{side}_{i}",
                "type": "StaticMeshActor",
                "location": [seg_x, fixed_y, walkway_z],
                "scale": [4.0, walkway_width/100, walkway_height/100],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

    for side, fixed_x in [("east", location[0] + outer_width/2 - walkway_width/2),
                          ("west", location[0] - outer_width/2 + walkway_width/2)]:
        segments = int(outer_depth / 400)
        for i in range(segments):
            seg_y = location[1] - outer_depth/2 + (i * 400) + 200
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_Walkway_{side}_{i}",
                "type": "StaticMeshActor",
                "location": [fixed_x, seg_y, walkway_z],
                "scale": [walkway_width/100, 4.0, walkway_height/100],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

    # Build annex rows along each wall
    _spawn_annex_row(
        start_x=location[0] - outer_width/2 + spacing,
        end_x=location[0] + outer_width/2 - spacing,
        fixed_y=location[1] - outer_depth/2 + walkway_width + annex_depth/2,
        align="north", base_name="NorthAnnex"
    )

    _spawn_annex_row(
        start_x=location[0] - outer_width/2 + spacing,
        end_x=location[0] + outer_width/2 - spacing,
        fixed_y=location[1] + outer_depth/2 - walkway_width - annex_depth/2,
        align="south", base_name="SouthAnnex"
    )

    # West and East wall annexes
    for y in range(int(location[1] - outer_depth/2 + spacing), int(location[1] + outer_depth/2 - spacing) + 1, spacing):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_WestAnnex_{y}",
            "type": "StaticMeshActor",
            "location": [location[0] - outer_width/2 + walkway_width + annex_depth/2, y, location[2] + annex_height/2],
            "scale": [annex_depth/100, annex_width/100, annex_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_EastAnnex_{y}",
            "type": "StaticMeshActor",
            "location": [location[0] + outer_width/2 - walkway_width - annex_depth/2, y, location[2] + annex_height/2],
            "scale": [annex_depth/100, annex_width/100, annex_height/100],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)


def build_siege_weapons(unreal, name_prefix: str, location: List[float],
                       dimensions: Dict[str, int], all_actors: List,
                       sink: Optional[ActorSink] = None) -> None:
    """Deploy siege weapons on walls and towers."""
    logger.info("Deploying siege weapons...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    wall_height = dimensions["wall_height"]
    tower_height = dimensions["tower_height"]

    catapult_positions = [
        [location[0], location[1] - outer_depth/2 + 200, location[2] + wall_height],
        [location[0], location[1] + outer_depth/2 - 200, location[2] + wall_height],
        [location[0] - outer_width/3, location[1] - outer_depth/2 + 200, location[2] + wall_height],
        [location[0] + outer_width/3, location[1] + outer_depth/2 - 200, location[2] + wall_height],
    ]

    for i, pos in enumerate(catapult_positions):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_CatapultBase_{i}",
            "type": "StaticMeshActor",
            "location": pos,
            "scale": [4.0, 3.0, 1.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_CatapultArm_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], pos[2] + 100],
            "rotation": [45, 0, 0],
            "scale": [0.4, 0.4, 6.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        for j in range(5):
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_CatapultAmmo_{i}_{j}",
                "type": "StaticMeshActor",
                "location": [pos[0] + j * 80 - 160, pos[1] + 250, pos[2] + 40],
                "scale": [0.6, 0.6, 0.6],
                "static_mesh": "/Engine/BasicShapes/Sphere.Sphere"
            }, all_actors)

    outer_corners = get_corner_positions(location, outer_width, outer_depth)
    for i in range(4):
        corner = outer_corners[i]
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_Ballista_{i}",
            "type": "StaticMeshActor",
            "location": [corner[0], corner[1], location[2] + tower_height],
            "scale": [0.5, 3.0, 0.5],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)


def build_village_settlement(unreal, name_prefix: str, location: List[float],
                           dimensions: Dict[str, int], castle_size: str, all_actors: List,
                           sink: Optional[ActorSink] = None) -> None:
    """Build massive dense surrounding settlement."""
    logger.info("Building massive dense outer settlement...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    complexity_multiplier = dimensions["complexity_multiplier"]

    village_radius = outer_width * 0.3
    num_houses = (24 if castle_size == "epic" else 16) * complexity_multiplier

    for i in range(num_houses):
        angle = (2 * math.pi * i) / num_houses
        house_x = location[0] + (outer_width/2 + village_radius) * math.cos(angle)
        house_y = location[1] + (outer_depth/2 + village_radius) * math.sin(angle)

        if not (house_x < location[0] - outer_width * 0.4 and abs(house_y - location[1]) < 1000):
            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_VillageHouse_{i}",
                "type": "StaticMeshActor",
                "location": [house_x, house_y, location[2] + 100],
                "rotation": [0, angle * 180/math.pi, 0],
                "scale": [3.0, 2.5, 2.0],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }, all_actors)

            _castle_spawn(sink, unreal, {
                "name": f"{name_prefix}_VillageRoof_{i}",
                "type": "StaticMeshActor",
                "location": [house_x, house_y, location[2] + 250],
                "rotation": [0, angle * 180/math.pi, 0],
                "scale": [3.5, 3.0, 0.8],
                "static_mesh": "/Engine/BasicShapes/Cone.Cone"
            }, all_actors)

    outer_village_radius = outer_width * 0.5
    for i in range(max(1, num_houses // 2)):
        angle = (2 * math.pi * i) / (num_houses // 2)
        house_x = location[0] + (outer_width/2 + outer_village_radius) * math.cos(angle)
        house_y = location[1] + (outer_depth/2 + outer_village_radius) * math.sin(angle)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_OuterVillageHouse_{i}",
            "type": "StaticMeshActor",
            "location": [house_x, house_y, location[2] + 100],
            "rotation": [0, angle * 180/math.pi, 0],
            "scale": [2.5, 2.0, 2.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_OuterVillageRoof_{i}",
            "type": "StaticMeshActor",
            "location": [house_x, house_y, location[2] + 250],
            "rotation": [0, angle * 180/math.pi, 0],
            "scale": [3.0, 2.5, 0.6],
            "static_mesh": "/Engine/BasicShapes/Cone.Cone"
        }, all_actors)

    _build_market_area(unreal, name_prefix, location, dimensions, all_actors, sink)
    _build_workshops(unreal, name_prefix, location, dimensions, all_actors, sink)


def _build_market_area(unreal, name_prefix: str, location: List[float],
                      dimensions: Dict[str, int], all_actors: List,
                      sink: Optional[ActorSink] = None) -> None:
    """Build dense market area near castle."""
    outer_width = dimensions["outer_width"]
    complexity_multiplier = dimensions["complexity_multiplier"]
    scale_factor = 2.0

    market_x_start = location[0] - outer_width/2 - int(800 * scale_factor)
    for i in range(8 * complexity_multiplier):
        stall_x = market_x_start + i * 150
        stall_y = location[1] + (200 if i % 2 == 0 else -200)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_MarketStall_{i}",
            "type": "StaticMeshActor",
            "location": [stall_x, stall_y, location[2] + 80],
            "scale": [2.0, 1.5, 1.5],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_StallCanopy_{i}",
            "type": "StaticMeshActor",
            "location": [stall_x, stall_y, location[2] + 180],
            "scale": [2.5, 2.0, 0.1],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)


def _build_workshops(unreal, name_prefix: str, location: List[float],
                    dimensions: Dict[str, int], all_actors: List,
                    sink: Optional[ActorSink] = None) -> None:
    """Add small outbuildings and workshops around the castle."""
    logger.info("Adding small outbuildings and extensions...")

    outer_width = dimensions["outer_width"]
    scale_factor = 2.0

    workshop_positions = []
    ring_offsets = [int(400 * scale_factor), int(600 * scale_factor), int(800 * scale_factor)]
    for offset in ring_offsets:
        workshop_positions.extend([
            [location[0] - outer_width/2 - offset, location[1] + offset],
            [location[0] - outer_width/2 - offset, location[1] - offset],
            [location[0] + outer_width/2 + offset, location[1] + offset],
            [location[0] + outer_width/2 + offset, location[1] - offset],
        ])

    for i, pos in enumerate(workshop_positions):
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_Workshop_{i}",
            "type": "StaticMeshActor",
            "location": [pos[0], pos[1], location[2] + 80],
            "scale": [2.0, 1.8, 1.6],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)


def build_drawbridge_and_moat(unreal, name_prefix: str, location: List[float],
                            dimensions: Dict[str, int], all_actors: List,
                            sink: Optional[ActorSink] = None) -> None:
    """Add massive drawbridge and moat around castle."""
    logger.info("Adding massive drawbridge...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    drawbridge_offset = dimensions["drawbridge_offset"]
    complexity_multiplier = dimensions["complexity_multiplier"]
    scale_factor = 2.0

    _castle_spawn(sink, unreal, {
        "name": f"{name_prefix}_Drawbridge",
        "type": "StaticMeshActor",
        "location": [location[0] - outer_width/2 - drawbridge_offset, location[1], location[2] + 20],
        "rotation": [0, 0, 0],
        "scale": [12.0 * scale_factor, 10.0 * scale_factor, 0.3],
        "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }, all_actors)

    logger.info("Creating massive moat...")
    moat_width = int(1200 * scale_factor)
    moat_sections = int(30 * complexity_multiplier)

    for i in range(moat_sections):
        angle = (2 * math.pi * i) / moat_sections
        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_Moat_{i}",
            "type": "StaticMeshActor",
            "location": [location[0] + (outer_width/2 + moat_width/2) * math.cos(angle), location[1] + (outer_depth/2 + moat_width/2) * math.sin(angle), location[2] - 50],
            "scale": [moat_width/100, moat_width/100, 0.1],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)


def add_decorative_flags(unreal, name_prefix: str, location: List[float],
                        dimensions: Dict[str, int], all_actors: List,
                        sink: Optional[ActorSink] = None) -> None:
    """Add flags on towers for decoration."""
    logger.info("Adding decorative flags...")

    outer_width = dimensions["outer_width"]
    outer_depth = dimensions["outer_depth"]
    tower_height = dimensions["tower_height"]
    gate_tower_offset = dimensions["gate_tower_offset"]

    outer_corners = get_corner_positions(location, outer_width, outer_depth)

    for i in range(len(outer_corners) + 2):
        if i < len(outer_corners):
            flag_x = outer_corners[i][0]
            flag_y = outer_corners[i][1]
            flag_z = location[2] + tower_height + 300
        else:
            side = 1 if i == len(outer_corners) else -1
            flag_x = location[0] - outer_width/2
            flag_y = location[1] + side * gate_tower_offset
            flag_z = location[2] + tower_height + 200

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_FlagPole_{i}",
            "type": "StaticMeshActor",
            "location": [flag_x, flag_y, flag_z],
            "scale": [0.05, 0.05, 3.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }, all_actors)

        _castle_spawn(sink, unreal, {
            "name": f"{name_prefix}_Flag_{i}",
            "type": "StaticMeshActor",
            "location": [flag_x + 100, flag_y, flag_z + 100],
            "scale": [0.05, 2.0, 1.5],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube"
        }, all_actors)