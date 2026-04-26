"""
Infrastructure creation helper functions for town generation.
Includes streets, lights, vehicles, and decorations.
"""
from typing import Dict, Any, List, Optional
import logging
import random
from utils.responses import is_success_response

logger = logging.getLogger(__name__)

try:
    from .actor_name_manager import safe_spawn_actor
except ImportError:
    logger.warning("Could not import actor_name_manager, using fallback spawning")
    def safe_spawn_actor(unreal_connection, params, auto_unique_name=True):
        return unreal_connection.send_command("spawn_actor", params)

from server.actor_sink import ActorSink, _spawn_actor_via_sink_or_direct


def _spawn(sink, unreal, params: Dict[str, Any], tags: List[str] = None) -> bool:
    """Spawn via sink if provided, otherwise via safe_spawn_actor."""
    return _spawn_actor_via_sink_or_direct(sink, unreal, params, tags=tags)


def _create_street_grid(
    blocks: int, block_size: float, street_width: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a grid of streets for the town."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            set_actor_transform = server.set_actor_transform
        else:
            unreal = None
            set_actor_transform = None

        streets: List[Dict[str, Any]] = []

        for i in range(blocks + 1):
            street_y = location[1] + (i - blocks/2) * block_size
            for j in range(blocks):
                street_x = location[0] + (j - blocks/2 + 0.5) * block_size
                actor_name = f"{name_prefix}_Street_H_{i}_{j}"
                params = {
                    "name": actor_name,
                    "type": "StaticMeshActor",
                    "location": [street_x, street_y, location[2] - 5],
                    "scale": [block_size/100.0 * 0.7, street_width/100.0, 0.1],
                }
                if _spawn(sink, unreal, params, tags=["infrastructure", "street"]):
                    streets.append(actor_name)
                elif unreal is not None:
                    resp = safe_spawn_actor(unreal, {"name": actor_name, "type": "StaticMeshActor", "location": [street_x, street_y, location[2] - 5]})
                    if resp and is_success_response(resp):
                        set_actor_transform(actor_name, scale=[block_size/100.0 * 0.7, street_width/100.0, 0.1])
                        streets.append(actor_name)

        for i in range(blocks + 1):
            street_x = location[0] + (i - blocks/2) * block_size
            for j in range(blocks):
                street_y = location[1] + (j - blocks/2 + 0.5) * block_size
                actor_name = f"{name_prefix}_Street_V_{i}_{j}"
                params = {
                    "name": actor_name,
                    "type": "StaticMeshActor",
                    "location": [street_x, street_y, location[2] - 5],
                    "scale": [street_width/100.0, block_size/100.0 * 0.7, 0.1],
                }
                if _spawn(sink, unreal, params, tags=["infrastructure", "street"]):
                    streets.append(actor_name)
                elif unreal is not None:
                    resp = safe_spawn_actor(unreal, {"name": actor_name, "type": "StaticMeshActor", "location": [street_x, street_y, location[2] - 5]})
                    if resp and is_success_response(resp):
                        set_actor_transform(actor_name, scale=[street_width/100.0, block_size/100.0 * 0.7, 0.1])
                        streets.append(actor_name)

        return {"success": True, "actors": streets}

    except Exception as e:
        logger.error(f"_create_street_grid error: {e}")
        return {"success": False, "actors": []}


def _create_street_lights(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create street lights throughout the town."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        lights: List[Dict[str, Any]] = []

        for i in range(blocks + 1):
            for j in range(blocks + 1):
                if random.random() > 0.7:
                    continue
                light_x = location[0] + (i - blocks/2) * block_size
                light_y = location[1] + (j - blocks/2) * block_size

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_LightPole_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [light_x, light_y, location[2] + 200],
                    "scale": [0.2, 0.2, 4.0],
                }, tags=["infrastructure", "light"]):
                    lights.append(f"{name_prefix}_LightPole_{i}_{j}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_Light_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [light_x, light_y, location[2] + 380],
                    "scale": [0.3, 0.3, 0.3],
                }, tags=["infrastructure", "light"]):
                    lights.append(f"{name_prefix}_Light_{i}_{j}")

        return {"success": True, "actors": lights}

    except Exception as e:
        logger.error(f"_create_street_lights error: {e}")
        return {"success": False, "actors": []}


def _create_town_vehicles(
    blocks: int, block_size: float, street_width: float,
    location: List[float], name_prefix: str, vehicle_count: int,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create vehicles throughout the town."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        vehicles: List[Dict[str, Any]] = []

        for i in range(vehicle_count):
            street_x = location[0] + random.uniform(-blocks*block_size/2, blocks*block_size/2)
            street_y = location[1] + random.uniform(-blocks*block_size/2, blocks*block_size/2)

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_Car_{i}",
                "type": "StaticMeshActor",
                "location": [street_x, street_y, location[2] + 50],
                "scale": [4.0, 2.0, 1.5],
            }, tags=["infrastructure", "vehicle"]):
                vehicles.append(f"{name_prefix}_Car_{i}")

        return {"success": True, "actors": vehicles}

    except Exception as e:
        logger.error(f"_create_town_vehicles error: {e}")
        return {"success": False, "actors": []}


def _create_town_decorations(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create parks, trees, and other decorative elements."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        decorations: List[Dict[str, Any]] = []

        num_parks = max(1, blocks // 3)
        for park_id in range(num_parks):
            park_x = location[0] + random.uniform(-blocks*block_size/3, blocks*block_size/3)
            park_y = location[1] + random.uniform(-blocks*block_size/3, blocks*block_size/3)

            trees_per_park = random.randint(3, 8)
            for tree_id in range(trees_per_park):
                tree_x = park_x + random.uniform(-200, 200)
                tree_y = park_y + random.uniform(-200, 200)

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_TreeTrunk_{park_id}_{tree_id}",
                    "type": "StaticMeshActor",
                    "location": [tree_x, tree_y, location[2] + 150],
                    "scale": [0.5, 0.5, 3.0],
                }, tags=["infrastructure", "tree"]):
                    decorations.append(f"{name_prefix}_TreeTrunk_{park_id}_{tree_id}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_TreeLeaves_{park_id}_{tree_id}",
                    "type": "StaticMeshActor",
                    "location": [tree_x, tree_y, location[2] + 350],
                    "scale": [2.0, 2.0, 2.0],
                }, tags=["infrastructure", "tree"]):
                    decorations.append(f"{name_prefix}_TreeLeaves_{park_id}_{tree_id}")

        return {"success": True, "actors": decorations}

    except Exception as e:
        logger.error(f"_create_town_decorations error: {e}")
        return {"success": False, "actors": []}


def _create_traffic_lights(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create traffic lights at major intersections."""
    try:
        import math as _math

        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        traffic_lights: List[Dict[str, Any]] = []

        for i in range(1, blocks, 2):
            for j in range(1, blocks, 2):
                intersection_x = location[0] + (i - blocks/2) * block_size
                intersection_y = location[1] + (j - blocks/2) * block_size

                for corner in range(4):
                    angle = corner * _math.pi / 2
                    offset = 150
                    pole_x = intersection_x + offset * _math.cos(angle)
                    pole_y = intersection_y + offset * _math.sin(angle)

                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_TrafficPole_{i}_{j}_{corner}",
                        "type": "StaticMeshActor",
                        "location": [pole_x, pole_y, location[2] + 150],
                        "scale": [0.15, 0.15, 3.0],
                        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                    }, tags=["infrastructure", "traffic"]):
                        traffic_lights.append(f"{name_prefix}_TrafficPole_{i}_{j}_{corner}")

                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_TrafficLight_{i}_{j}_{corner}",
                        "type": "StaticMeshActor",
                        "location": [pole_x, pole_y, location[2] + 280],
                        "scale": [0.3, 0.2, 0.8],
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, tags=["infrastructure", "traffic"]):
                        traffic_lights.append(f"{name_prefix}_TrafficLight_{i}_{j}_{corner}")

        return {"success": True, "actors": traffic_lights}

    except Exception as e:
        logger.error(f"_create_traffic_lights error: {e}")
        return {"success": False, "actors": []}


def _create_street_signage(
    blocks: int, block_size: float, location: List[float],
    name_prefix: str, town_size: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create street signs and billboards."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        signage: List[Dict[str, Any]] = []

        for i in range(0, blocks + 1, 2):
            for j in range(0, blocks + 1, 2):
                if random.random() > 0.5:
                    continue
                sign_x = location[0] + (i - blocks/2) * block_size + 100
                sign_y = location[1] + (j - blocks/2) * block_size + 100

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_SignPole_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sign_x, sign_y, location[2] + 100],
                    "scale": [0.1, 0.1, 2.0],
                    "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                }, tags=["infrastructure", "signage"]):
                    signage.append(f"{name_prefix}_SignPole_{i}_{j}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_StreetSign_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sign_x, sign_y, location[2] + 180],
                    "scale": [1.5, 0.05, 0.3],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "signage"]):
                    signage.append(f"{name_prefix}_StreetSign_{i}_{j}")

        if town_size in ["large", "metropolis"]:
            num_billboards = random.randint(3, 8)
            for b in range(num_billboards):
                billboard_x = location[0] + random.uniform(-blocks*block_size/3, blocks*block_size/3)
                billboard_y = location[1] + random.uniform(-blocks*block_size/3, blocks*block_size/3)

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_Billboard_{b}",
                    "type": "StaticMeshActor",
                    "location": [billboard_x, billboard_y, location[2] + 400],
                    "scale": [3.0, 0.1, 2.0],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "signage"]):
                    signage.append(f"{name_prefix}_Billboard_{b}")

                for support_offset in [-100, 100]:
                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_BillboardSupport_{b}_{support_offset}",
                        "type": "StaticMeshActor",
                        "location": [billboard_x + support_offset, billboard_y, location[2] + 200],
                        "scale": [0.2, 0.2, 4.0],
                        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                    }, tags=["infrastructure", "signage"]):
                        signage.append(f"{name_prefix}_BillboardSupport_{b}_{support_offset}")

        return {"success": True, "actors": signage}

    except Exception as e:
        logger.error(f"_create_street_signage error: {e}")
        return {"success": False, "actors": []}


def _create_sidewalks_crosswalks(
    blocks: int, block_size: float, street_width: float,
    location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create sidewalks and crosswalks."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        sidewalks: List[Dict[str, Any]] = []
        sidewalk_width = 150.0

        for i in range(blocks):
            for j in range(blocks + 1):
                sidewalk_y = location[1] + (j - blocks/2) * block_size
                sidewalk_x = location[0] + (i - blocks/2 + 0.5) * block_size

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_SidewalkH_North_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sidewalk_x, sidewalk_y - street_width/2 + sidewalk_width/2, location[2]],
                    "scale": [block_size/100.0 * 0.7, sidewalk_width/100.0, 0.05],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "sidewalk"]):
                    sidewalks.append(f"{name_prefix}_SidewalkH_North_{i}_{j}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_SidewalkH_South_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sidewalk_x, sidewalk_y + street_width/2 - sidewalk_width/2, location[2]],
                    "scale": [block_size/100.0 * 0.7, sidewalk_width/100.0, 0.05],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "sidewalk"]):
                    sidewalks.append(f"{name_prefix}_SidewalkH_South_{i}_{j}")

        for i in range(blocks + 1):
            for j in range(blocks):
                sidewalk_x = location[0] + (i - blocks/2) * block_size
                sidewalk_y = location[1] + (j - blocks/2 + 0.5) * block_size

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_SidewalkV_East_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sidewalk_x - street_width/2 + sidewalk_width/2, sidewalk_y, location[2]],
                    "scale": [sidewalk_width/100.0, block_size/100.0 * 0.7, 0.05],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "sidewalk"]):
                    sidewalks.append(f"{name_prefix}_SidewalkV_East_{i}_{j}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_SidewalkV_West_{i}_{j}",
                    "type": "StaticMeshActor",
                    "location": [sidewalk_x + street_width/2 - sidewalk_width/2, sidewalk_y, location[2]],
                    "scale": [sidewalk_width/100.0, block_size/100.0 * 0.7, 0.05],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "sidewalk"]):
                    sidewalks.append(f"{name_prefix}_SidewalkV_West_{i}_{j}")

        crosswalk_width = 200.0
        for i in range(blocks + 1):
            for j in range(blocks + 1):
                intersection_x = location[0] + (i - blocks/2) * block_size
                intersection_y = location[1] + (j - blocks/2) * block_size

                for stripe in range(5):
                    stripe_offset = (stripe - 2) * 40

                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_CrosswalkNS_{i}_{j}_{stripe}",
                        "type": "StaticMeshActor",
                        "location": [intersection_x + stripe_offset, intersection_y, location[2] + 1],
                        "scale": [0.3, crosswalk_width/100.0, 0.02],
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, tags=["infrastructure", "crosswalk"]):
                        sidewalks.append(f"{name_prefix}_CrosswalkNS_{i}_{j}_{stripe}")

                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_CrosswalkEW_{i}_{j}_{stripe}",
                        "type": "StaticMeshActor",
                        "location": [intersection_x, intersection_y + stripe_offset, location[2] + 1],
                        "scale": [crosswalk_width/100.0, 0.3, 0.02],
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, tags=["infrastructure", "crosswalk"]):
                        sidewalks.append(f"{name_prefix}_CrosswalkEW_{i}_{j}_{stripe}")

        return {"success": True, "actors": sidewalks}

    except Exception as e:
        logger.error(f"_create_sidewalks_crosswalks error: {e}")
        return {"success": False, "actors": []}


def _create_urban_furniture(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create benches, trash cans, and bus stops."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        furniture: List[Dict[str, Any]] = []
        num_furniture_items = blocks * blocks // 2

        for f in range(num_furniture_items):
            street_x = location[0] + random.uniform(-blocks*block_size/2, blocks*block_size/2)
            street_y = location[1] + random.uniform(-blocks*block_size/2, blocks*block_size/2)
            sidewalk_offset = random.choice([-200, 200])
            if random.random() > 0.5:
                furniture_x = street_x + sidewalk_offset
                furniture_y = street_y
            else:
                furniture_x = street_x
                furniture_y = street_y + sidewalk_offset

            furniture_type = random.choice(["bench", "trash", "bus_stop"])

            if furniture_type == "bench":
                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_Bench_{f}",
                    "type": "StaticMeshActor",
                    "location": [furniture_x, furniture_y, location[2] + 30],
                    "scale": [1.5, 0.5, 0.6],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "furniture"]):
                    furniture.append(f"{name_prefix}_Bench_{f}")

                for support_offset in [-50, 50]:
                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_BenchSupport_{f}_{support_offset}",
                        "type": "StaticMeshActor",
                        "location": [furniture_x + support_offset, furniture_y, location[2] + 15],
                        "scale": [0.1, 0.5, 0.3],
                        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                    }, tags=["infrastructure", "furniture"]):
                        furniture.append(f"{name_prefix}_BenchSupport_{f}_{support_offset}")

            elif furniture_type == "trash":
                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_TrashCan_{f}",
                    "type": "StaticMeshActor",
                    "location": [furniture_x, furniture_y, location[2] + 40],
                    "scale": [0.4, 0.4, 0.8],
                    "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                }, tags=["infrastructure", "furniture"]):
                    furniture.append(f"{name_prefix}_TrashCan_{f}")

            else:
                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_BusStop_{f}",
                    "type": "StaticMeshActor",
                    "location": [furniture_x, furniture_y, location[2] + 120],
                    "scale": [2.0, 1.0, 0.1],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "furniture"]):
                    furniture.append(f"{name_prefix}_BusStop_{f}")

                for post_x in [-80, 80]:
                    if _spawn(sink, unreal, {
                        "name": f"{name_prefix}_BusStopPost_{f}_{post_x}",
                        "type": "StaticMeshActor",
                        "location": [furniture_x + post_x, furniture_y, location[2] + 60],
                        "scale": [0.1, 0.1, 1.2],
                        "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
                    }, tags=["infrastructure", "furniture"]):
                        furniture.append(f"{name_prefix}_BusStopPost_{f}_{post_x}")

                if _spawn(sink, unreal, {
                    "name": f"{name_prefix}_BusStopBench_{f}",
                    "type": "StaticMeshActor",
                    "location": [furniture_x, furniture_y + 30, location[2] + 25],
                    "scale": [1.8, 0.4, 0.5],
                    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
                }, tags=["infrastructure", "furniture"]):
                    furniture.append(f"{name_prefix}_BusStopBench_{f}")

        return {"success": True, "actors": furniture}

    except Exception as e:
        logger.error(f"_create_urban_furniture error: {e}")
        return {"success": False, "actors": []}


def _create_street_utilities(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create parking meters and fire hydrants."""
    try:
        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        utilities: List[Dict[str, Any]] = []

        num_meters = blocks * 4
        for m in range(num_meters):
            meter_x = location[0] + random.uniform(-blocks*block_size/3, blocks*block_size/3)
            meter_y = location[1] + random.uniform(-blocks*block_size/3, blocks*block_size/3)
            sidewalk_offset = random.choice([-180, 180])
            if random.random() > 0.5:
                meter_x += sidewalk_offset
            else:
                meter_y += sidewalk_offset

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_ParkingMeter_{m}",
                "type": "StaticMeshActor",
                "location": [meter_x, meter_y, location[2] + 50],
                "scale": [0.15, 0.15, 1.0],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
            }, tags=["infrastructure", "utility"]):
                utilities.append(f"{name_prefix}_ParkingMeter_{m}")

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_MeterHead_{m}",
                "type": "StaticMeshActor",
                "location": [meter_x, meter_y, location[2] + 100],
                "scale": [0.25, 0.15, 0.3],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, tags=["infrastructure", "utility"]):
                utilities.append(f"{name_prefix}_MeterHead_{m}")

        num_hydrants = blocks + 2
        for h in range(num_hydrants):
            hydrant_x = location[0] + random.uniform(-blocks*block_size/2, blocks*block_size/2)
            hydrant_y = location[1] + random.uniform(-blocks*block_size/2, blocks*block_size/2)

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_Hydrant_{h}",
                "type": "StaticMeshActor",
                "location": [hydrant_x, hydrant_y, location[2] + 40],
                "scale": [0.3, 0.3, 0.8],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
            }, tags=["infrastructure", "utility"]):
                utilities.append(f"{name_prefix}_Hydrant_{h}")

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_HydrantCap_{h}",
                "type": "StaticMeshActor",
                "location": [hydrant_x, hydrant_y, location[2] + 75],
                "scale": [0.35, 0.35, 0.1],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
            }, tags=["infrastructure", "utility"]):
                utilities.append(f"{name_prefix}_HydrantCap_{h}")

        return {"success": True, "actors": utilities}

    except Exception as e:
        logger.error(f"_create_street_utilities error: {e}")
        return {"success": False, "actors": []}


def _create_central_plaza(
    blocks: int, block_size: float, location: List[float], name_prefix: str,
    all_actors: List[Dict[str, Any]],
    sink: Optional["ActorSink"] = None
) -> Dict[str, Any]:
    """Create a central plaza with fountain and monuments."""
    try:
        import math as _math

        if sink is None:
            import unreal_mcp_server_advanced as server
            unreal = server.get_unreal_connection()
            if not unreal:
                return {"success": False, "actors": []}
        else:
            unreal = None

        plaza: List[Dict[str, Any]] = []
        plaza_size = block_size * 0.8

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_PlazaFloor",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + 2],
            "scale": [plaza_size/100.0, plaza_size/100.0, 0.05],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, tags=["infrastructure", "plaza"]):
            plaza.append(f"{name_prefix}_PlazaFloor")

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainBase",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + 10],
            "scale": [3.0, 3.0, 0.2],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        }, tags=["infrastructure", "plaza", "fountain"]):
            plaza.append(f"{name_prefix}_FountainBase")

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainCenter",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + 50],
            "scale": [0.5, 0.5, 0.8],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        }, tags=["infrastructure", "plaza", "fountain"]):
            plaza.append(f"{name_prefix}_FountainCenter")

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_FountainTop",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + 80],
            "scale": [1.5, 1.5, 0.1],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        }, tags=["infrastructure", "plaza", "fountain"]):
            plaza.append(f"{name_prefix}_FountainTop")

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_Monument",
            "type": "StaticMeshActor",
            "location": [location[0] + plaza_size/3, location[1], location[2] + 100],
            "scale": [1.0, 1.0, 2.0],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
        }, tags=["infrastructure", "plaza", "monument"]):
            plaza.append(f"{name_prefix}_Monument")

        if _spawn(sink, unreal, {
            "name": f"{name_prefix}_MonumentBase",
            "type": "StaticMeshActor",
            "location": [location[0] + plaza_size/3, location[1], location[2] + 30],
            "scale": [2.0, 2.0, 0.6],
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        }, tags=["infrastructure", "plaza", "monument"]):
            plaza.append(f"{name_prefix}_MonumentBase")

        num_benches = 8
        for i in range(num_benches):
            angle = (2 * _math.pi * i) / num_benches
            bench_x = location[0] + plaza_size/3 * _math.cos(angle)
            bench_y = location[1] + plaza_size/3 * _math.sin(angle)
            bench_rotation = [0, 0, angle * 180/_math.pi]
            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_PlazaBench_{i}",
                "type": "StaticMeshActor",
                "location": [bench_x, bench_y, location[2] + 30],
                "rotation": bench_rotation,
                "scale": [1.5, 0.5, 0.6],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            }, tags=["infrastructure", "plaza", "bench"]):
                plaza.append(f"{name_prefix}_PlazaBench_{i}")

        num_lights = 12
        for i in range(num_lights):
            angle = (2 * _math.pi * i) / num_lights
            light_x = location[0] + plaza_size/2 * _math.cos(angle)
            light_y = location[1] + plaza_size/2 * _math.sin(angle)
            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_PlazaLightPost_{i}",
                "type": "StaticMeshActor",
                "location": [light_x, light_y, location[2] + 100],
                "scale": [0.15, 0.15, 2.0],
                "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder",
            }, tags=["infrastructure", "plaza", "light"]):
                plaza.append(f"{name_prefix}_PlazaLightPost_{i}")

            if _spawn(sink, unreal, {
                "name": f"{name_prefix}_PlazaLight_{i}",
                "type": "StaticMeshActor",
                "location": [light_x, light_y, location[2] + 180],
                "scale": [0.4, 0.4, 0.3],
                "static_mesh": "/Engine/BasicShapes/Sphere.Sphere",
            }, tags=["infrastructure", "plaza", "light"]):
                plaza.append(f"{name_prefix}_PlazaLight_{i}")

        return {"success": True, "actors": plaza}

    except Exception as e:
        logger.error(f"_create_central_plaza error: {e}")
        return {"success": False, "actors": []}