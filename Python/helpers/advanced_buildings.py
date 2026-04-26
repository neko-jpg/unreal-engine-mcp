"""
Advanced building creation helper functions for complex structures.
Includes skyscrapers, office towers, apartment complexes, shopping malls, and parking garages.
"""
from typing import Dict, Any, List, Optional
import logging
import random

logger = logging.getLogger(__name__)

# Import safe spawning functions
try:
    from .actor_name_manager import safe_spawn_actor
except ImportError:
    logger.warning("Could not import actor_name_manager, using fallback spawning")
    def safe_spawn_actor(unreal_connection, params, auto_unique_name=True):
        return unreal_connection.send_command("spawn_actor", params)

try:
    from server.actor_sink import ActorSink, _spawn_actor_via_sink_or_direct
except ImportError:
    ActorSink = None  # type: ignore[assignment,misc]
    _spawn_actor_via_sink_or_direct = None  # type: ignore[assignment]


def _spawn(sink, unreal, params: Dict[str, Any], all_actors: List[Dict[str, Any]], tags: List[str] = None) -> bool:
    """Spawn via sink if provided, otherwise via safe_spawn_actor."""
    if tags is None:
        tags = ["building"]
    if sink is not None:
        from server.actor_sink import params_to_spec
        sink.spawn(params_to_spec(params, tags=tags))
        return True
    from helpers.actor_name_manager import safe_spawn_actor
    from utils.responses import is_success_response
    resp = safe_spawn_actor(unreal, params)
    if resp and is_success_response(resp):
        all_actors.append(resp.get("result"))
        return True
    return False


def _create_skyscraper(
    height: int, base_width: float, base_depth: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create an impressive skyscraper with multiple sections and details."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 150.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 30],
            "scale": [(base_width + 200)/100.0, (base_depth + 200)/100.0, 0.6],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        sections = min(5, height // 5)
        current_width = base_width
        current_depth = base_depth
        current_height = location[2]

        for section in range(sections):
            section_floors = height // sections
            if section == sections - 1:
                section_floors += height % sections

            taper_factor = 1 - (section * 0.1)
            current_width = base_width * max(0.6, taper_factor)
            current_depth = base_depth * max(0.6, taper_factor)

            section_height = section_floors * floor_height
            _spawn(sink, unreal, {
                "name": f"{name_prefix}_Section_{section}",
                "type": "StaticMeshActor",
                "location": [location[0], location[1], current_height + section_height/2],
                "scale": [current_width/100.0, current_depth/100.0, section_height/100.0],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

            if section < sections - 1:
                _spawn(sink, unreal, {
                    "name": f"{name_prefix}_Balcony_{section}",
                    "type": "StaticMeshActor",
                    "location": [location[0], location[1], current_height + section_height - 25],
                    "scale": [(current_width + 100)/100.0, (current_depth + 100)/100.0, 0.5],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, actors)

            current_height += section_height

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Spire",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], current_height + 300],
            "scale": [0.2, 0.2, 6.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        }, actors)

        for i in range(3):
            equipment_x = location[0] + random.uniform(-current_width/4, current_width/4)
            equipment_y = location[1] + random.uniform(-current_depth/4, current_depth/4)
            _spawn(sink, unreal, {
                "name": f"{name_prefix}_RoofEquipment_{i}",
                "type": "StaticMeshActor",
                "location": [equipment_x, equipment_y, current_height + 50],
                "scale": [1.0, 1.0, 1.0],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_skyscraper error: {e}")
        return {"success": False, "actors": []}


def _create_office_tower(
    floors: int, width: float, depth: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a modern office tower with glass facade appearance."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 140.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 15],
            "scale": [(width + 100)/100.0, (depth + 100)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        lobby_height = floor_height * 1.5
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Lobby",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + lobby_height/2],
            "scale": [width/100.0, depth/100.0, lobby_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        tower_height = (floors - 1) * floor_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Tower",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + lobby_height + tower_height/2],
            "scale": [width/100.0, depth/100.0, tower_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        for floor in range(2, floors, 3):
            band_height = location[2] + lobby_height + (floor - 1) * floor_height
            _spawn(sink, unreal, {
                "name": f"{name_prefix}_WindowBand_{floor}",
                "type": "StaticMeshActor",
                "location": [location[0], location[1], band_height],
                "scale": [(width + 20)/100.0, (depth + 20)/100.0, 0.2],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

        rooftop_height = location[2] + lobby_height + tower_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Rooftop",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], rooftop_height + 30],
            "scale": [(width - 100)/100.0, (depth - 100)/100.0, 0.6],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_office_tower error: {e}")
        return {"success": False, "actors": []}


def _create_apartment_complex(
    floors: int, units_per_floor: int,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a multi-unit residential complex with balconies."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 120.0
        width = 200 * units_per_floor // 2
        depth = 800

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 15],
            "scale": [(width + 100)/100.0, (depth + 100)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        building_height = floors * floor_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Building",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + building_height/2],
            "scale": [width/100.0, depth/100.0, building_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        for floor in range(1, floors):
            balcony_height = location[2] + floor * floor_height - 20

            _spawn(sink, unreal, {
                "name": f"{name_prefix}_FrontBalcony_{floor}",
                "type": "StaticMeshActor",
                "location": [location[0], location[1] - depth/2 - 50, balcony_height],
                "scale": [width/100.0, 1.0, 0.2],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

            _spawn(sink, unreal, {
                "name": f"{name_prefix}_BackBalcony_{floor}",
                "type": "StaticMeshActor",
                "location": [location[0], location[1] + depth/2 + 50, balcony_height],
                "scale": [width/100.0, 1.0, 0.2],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Rooftop",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + building_height + 15],
            "scale": [(width + 50)/100.0, (depth + 50)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_apartment_complex error: {e}")
        return {"success": False, "actors": []}


def _create_shopping_mall(
    width: float, depth: float, floors: int,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a large shopping mall with entrance canopy."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 200.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 20],
            "scale": [(width + 200)/100.0, (depth + 200)/100.0, 0.4],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        mall_height = floors * floor_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Main",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + mall_height/2],
            "scale": [width/100.0, depth/100.0, mall_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Canopy",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 150, location[2] + floor_height],
            "scale": [width/100.0 * 0.8, 3.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        for i, x_offset in enumerate([-width/3, 0, width/3]):
            _spawn(sink, unreal, {
                "name": f"{name_prefix}_Pillar_{i}",
                "type": "StaticMeshActor",
                "location": [location[0] + x_offset, location[1] - depth/2 - 100, location[2] + floor_height/2],
                "scale": [0.5, 0.5, floor_height/100.0],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
            }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_RoofParking",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + mall_height + 15],
            "scale": [width/100.0 * 0.9, depth/100.0 * 0.9, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_shopping_mall error: {e}")
        return {"success": False, "actors": []}


def _create_parking_garage(
    levels: int, width: float, depth: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a multi-level parking structure."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        level_height = 120.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 15],
            "scale": [(width + 50)/100.0, (depth + 50)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        for level in range(levels):
            level_z = location[2] + level * level_height

            _spawn(sink, unreal, {
                "name": f"{name_prefix}_Floor_{level}",
                "type": "StaticMeshActor",
                "location": [location[0], location[1], level_z],
                "scale": [width/100.0, depth/100.0, 0.2],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, actors)

            for x in [-width/3, 0, width/3]:
                for y in [-depth/3, 0, depth/3]:
                    _spawn(sink, unreal, {
                        "name": f"{name_prefix}_Pillar_{level}_{x}_{y}",
                        "type": "StaticMeshActor",
                        "location": [location[0] + x, location[1] + y, level_z + level_height/2],
                        "scale": [0.4, 0.4, level_height/100.0],
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, actors)

            if level > 0:
                for side in ["left", "right", "front", "back"]:
                    if side == "left":
                        barrier_loc = [location[0] - width/2, location[1], level_z + 40]
                        barrier_scale = [0.1, depth/100.0, 0.8]
                    elif side == "right":
                        barrier_loc = [location[0] + width/2, location[1], level_z + 40]
                        barrier_scale = [0.1, depth/100.0, 0.8]
                    elif side == "front":
                        barrier_loc = [location[0], location[1] - depth/2, level_z + 40]
                        barrier_scale = [width/100.0, 0.1, 0.8]
                    else:
                        barrier_loc = [location[0], location[1] + depth/2, level_z + 40]
                        barrier_scale = [width/100.0, 0.1, 0.8]

                    _spawn(sink, unreal, {
                        "name": f"{name_prefix}_Barrier_{level}_{side}",
                        "type": "StaticMeshActor",
                        "location": barrier_loc,
                        "scale": barrier_scale,
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Ramp",
            "type": "StaticMeshActor",
            "location": [location[0] + width/2 + 100, location[1], location[2] + (levels * level_height)/2],
            "scale": [1.5, 2.0, levels * level_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_parking_garage error: {e}")
        return {"success": False, "actors": []}


def _create_hotel(
    floors: int, width: float, depth: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a luxury hotel with distinctive features."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 130.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 20],
            "scale": [(width + 150)/100.0, (depth + 150)/100.0, 0.4],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        lobby_height = floor_height * 2
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Lobby",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + lobby_height/2],
            "scale": [width/100.0, depth/100.0, lobby_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        tower_height = (floors - 2) * floor_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Tower",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + lobby_height + tower_height/2],
            "scale": [width/100.0 * 0.9, depth/100.0 * 0.9, tower_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        penthouse_height = location[2] + lobby_height + tower_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Penthouse",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], penthouse_height + floor_height/2],
            "scale": [width/100.0, depth/100.0, floor_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Pool",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], penthouse_height + floor_height + 20],
            "scale": [width/100.0 * 0.5, depth/100.0 * 0.3, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Canopy",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 100, location[2] + 150],
            "scale": [width/100.0 * 0.6, 2.0, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_hotel error: {e}")
        return {"success": False, "actors": []}


def _create_restaurant(
    width: float, depth: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a small restaurant/cafe building."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        height = 150.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 10],
            "scale": [(width + 50)/100.0, (depth + 50)/100.0, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Main",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + height/2],
            "scale": [width/100.0, depth/100.0, height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Patio",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 75, location[2]],
            "scale": [width/100.0, 1.5, 0.1],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Awning",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 50, location[2] + height - 20],
            "scale": [width/100.0 * 1.2, 1.0, 0.1],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_restaurant error: {e}")
        return {"success": False, "actors": []}


def _create_store(
    width: float, depth: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a small retail store."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        height = 140.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 10],
            "scale": [(width + 30)/100.0, (depth + 30)/100.0, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Main",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + height/2],
            "scale": [width/100.0, depth/100.0, height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Sign",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 10, location[2] + height + 20],
            "scale": [width/100.0 * 0.8, 0.1, 0.4],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_store error: {e}")
        return {"success": False, "actors": []}


def _create_apartment_building(
    floors: int, width: float, depth: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a smaller residential apartment building."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        actors: List[Dict[str, Any]] = []
        floor_height = 110.0

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - 15],
            "scale": [(width + 50)/100.0, (depth + 50)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        building_height = floors * floor_height
        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Building",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + building_height/2],
            "scale": [width/100.0, depth/100.0, building_height/100.0],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Steps",
            "type": "StaticMeshActor",
            "location": [location[0], location[1] - depth/2 - 30, location[2] + 10],
            "scale": [width/100.0 * 0.3, 0.6, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        _spawn(sink, unreal, {
            "name": f"{name_prefix}_Roof",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + building_height + 15],
            "scale": [(width + 20)/100.0, (depth + 20)/100.0, 0.3],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, actors)

        return {"success": True, "actors": actors}

    except Exception as e:
        logger.error(f"_create_apartment_building error: {e}")
        return {"success": False, "actors": []}