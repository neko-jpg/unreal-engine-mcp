"""
House Construction Helper Functions

Contains functions for building realistic houses with architectural details.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("UnrealMCP_Advanced")

# Import safe spawning functions
try:
    from .actor_name_manager import safe_spawn_actor
except ImportError:
    logger.warning("Could not import actor_name_manager, using fallback spawning")
    def safe_spawn_actor(unreal_connection, params, auto_unique_name=True):
        return unreal_connection.send_command("spawn_actor", params)

from server.actor_sink import ActorSink, _spawn_actor_via_sink_or_direct


def _spawn(sink: Optional[ActorSink], unreal, params: Dict[str, Any], tags: List[str] = None) -> bool:
    """Spawn via sink if provided, otherwise via safe_spawn_actor."""
    return _spawn_actor_via_sink_or_direct(sink, unreal, params, tags=tags)


def build_house(
    unreal_connection,
    width: int,
    depth: int,
    height: int,
    location: List[float],
    name_prefix: str,
    mesh: str,
    house_style: str,
    sink: Optional[ActorSink] = None
) -> Dict[str, Any]:
    """Build a realistic house with architectural details and multiple rooms."""
    try:
        results = []
        wall_thickness = 20.0
        floor_thickness = 30.0

        if house_style == "cottage":
            width = int(width * 0.8)
            depth = int(depth * 0.8)
            height = int(height * 0.9)

        foundation_params = {
            "name": f"{name_prefix}_Foundation",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] - floor_thickness/2],
            "scale": [(width + 200)/100.0, (depth + 200)/100.0, floor_thickness/100.0],
            "static_mesh": mesh
        }
        if _spawn(sink, unreal_connection, foundation_params, tags=["house"]):
            results.append(foundation_params["name"])

        floor_params = {
            "name": f"{name_prefix}_Floor",
            "type": "StaticMeshActor",
            "location": [location[0], location[1], location[2] + floor_thickness/2],
            "scale": [width/100.0, depth/100.0, floor_thickness/100.0],
            "static_mesh": mesh
        }
        if _spawn(sink, unreal_connection, floor_params, tags=["house"]):
            results.append(floor_params["name"])

        base_z = location[2] + floor_thickness

        _build_house_walls(unreal_connection, name_prefix, location, width, depth, height, base_z, wall_thickness, mesh, results, sink)
        _build_house_roof(unreal_connection, name_prefix, location, width, depth, height, base_z, mesh, house_style, results, sink)
        _add_house_features(unreal_connection, name_prefix, location, width, depth, height, base_z, wall_thickness, mesh, house_style, results, sink)

        if sink is not None:
            return {"success": True, "house_style": house_style, "dimensions": {"width": width, "depth": depth, "height": height}, "features": _get_house_features(house_style)}

        return {
            "success": True,
            "actors": results,
            "house_style": house_style,
            "dimensions": {"width": width, "depth": depth, "height": height},
            "features": _get_house_features(house_style),
            "total_actors": len(results)
        }

    except Exception as e:
        logger.error(f"build_house error: {e}")
        return {"success": False, "message": str(e)}

def _build_house_walls(unreal_connection, name_prefix, location, width, depth, height, base_z, wall_thickness, mesh, results, sink=None):
    """Build the main walls of the house with door and window openings."""
    door_width = 120.0
    door_height = 240.0

    front_left_width = (width/2 - door_width/2)
    front_left_params = {
        "name": f"{name_prefix}_FrontWall_Left",
        "type": "StaticMeshActor",
        "location": [location[0] - width/4 - door_width/4, location[1] - depth/2, base_z + height/2],
        "scale": [front_left_width/100.0, wall_thickness/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, front_left_params, tags=["house", "wall"]):
        results.append(front_left_params["name"])

    front_right_params = {
        "name": f"{name_prefix}_FrontWall_Right",
        "type": "StaticMeshActor",
        "location": [location[0] + width/4 + door_width/4, location[1] - depth/2, base_z + height/2],
        "scale": [front_left_width/100.0, wall_thickness/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, front_right_params, tags=["house", "wall"]):
        results.append(front_right_params["name"])

    front_top_params = {
        "name": f"{name_prefix}_FrontWall_Top",
        "type": "StaticMeshActor",
        "location": [location[0], location[1] - depth/2, base_z + door_height + (height - door_height)/2],
        "scale": [door_width/100.0, wall_thickness/100.0, (height - door_height)/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, front_top_params, tags=["house", "wall"]):
        results.append(front_top_params["name"])

    window_width = 150.0
    window_height = 150.0
    window_y = base_z + height/2

    back_left_params = {
        "name": f"{name_prefix}_BackWall_Left",
        "type": "StaticMeshActor",
        "location": [location[0] - width/3, location[1] + depth/2, base_z + height/2],
        "scale": [width/3/100.0, wall_thickness/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, back_left_params, tags=["house", "wall"]):
        results.append(back_left_params["name"])

    back_center_bottom_params = {
        "name": f"{name_prefix}_BackWall_Center_Bottom",
        "type": "StaticMeshActor",
        "location": [location[0], location[1] + depth/2, base_z + (window_y - window_height/2 - base_z)/2],
        "scale": [width/3/100.0, wall_thickness/100.0, (window_y - window_height/2 - base_z)/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, back_center_bottom_params, tags=["house", "wall"]):
        results.append(back_center_bottom_params["name"])

    back_center_top_params = {
        "name": f"{name_prefix}_BackWall_Center_Top",
        "type": "StaticMeshActor",
        "location": [location[0], location[1] + depth/2, window_y + window_height/2 + (base_z + height - window_y - window_height/2)/2],
        "scale": [width/3/100.0, wall_thickness/100.0, (base_z + height - window_y - window_height/2)/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, back_center_top_params, tags=["house", "wall"]):
        results.append(back_center_top_params["name"])

    back_right_params = {
        "name": f"{name_prefix}_BackWall_Right",
        "type": "StaticMeshActor",
        "location": [location[0] + width/3, location[1] + depth/2, base_z + height/2],
        "scale": [width/3/100.0, wall_thickness/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, back_right_params, tags=["house", "wall"]):
        results.append(back_right_params["name"])

    left_wall_params = {
        "name": f"{name_prefix}_LeftWall",
        "type": "StaticMeshActor",
        "location": [location[0] - width/2, location[1], base_z + height/2],
        "scale": [wall_thickness/100.0, depth/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, left_wall_params, tags=["house", "wall"]):
        results.append(left_wall_params["name"])

    right_wall_params = {
        "name": f"{name_prefix}_RightWall",
        "type": "StaticMeshActor",
        "location": [location[0] + width/2, location[1], base_z + height/2],
        "scale": [wall_thickness/100.0, depth/100.0, height/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, right_wall_params, tags=["house", "wall"]):
        results.append(right_wall_params["name"])

def _build_house_roof(unreal_connection, name_prefix, location, width, depth, height, base_z, mesh, house_style, results, sink=None):
    """Build the roof of the house."""
    roof_thickness = 30.0
    roof_overhang = 100.0

    flat_roof_params = {
        "name": f"{name_prefix}_Roof",
        "type": "StaticMeshActor",
        "location": [location[0], location[1], base_z + height + roof_thickness/2],
        "rotation": [0, 0, 0],
        "scale": [(width + roof_overhang*2)/100.0, (depth + roof_overhang*2)/100.0, roof_thickness/100.0],
        "static_mesh": mesh
    }
    if _spawn(sink, unreal_connection, flat_roof_params, tags=["house", "roof"]):
        results.append(flat_roof_params["name"])

    if house_style == "cottage":
        chimney_params = {
            "name": f"{name_prefix}_Chimney",
            "type": "StaticMeshActor",
            "location": [location[0] + width/3, location[1] + depth/3, base_z + height + roof_thickness + 150],
            "scale": [1.0, 1.0, 2.5],
            "static_mesh": "/Engine/BasicShapes/Cylinder.Cylinder"
        }
        if _spawn(sink, unreal_connection, chimney_params, tags=["house", "chimney"]):
            results.append(chimney_params["name"])

def _add_house_features(unreal_connection, name_prefix, location, width, depth, height, base_z, wall_thickness, mesh, house_style, results, sink=None):
    """Add style-specific features to the house."""
    if house_style == "modern":
        garage_params = {
            "name": f"{name_prefix}_Garage_Door",
            "type": "StaticMeshActor",
            "location": [location[0] - width/3, location[1] - depth/2 + wall_thickness/2, base_z + 150],
            "scale": [2.5, 0.1, 2.5],
            "static_mesh": mesh
        }
        if _spawn(sink, unreal_connection, garage_params, tags=["house", "garage"]):
            results.append(garage_params["name"])

def _get_house_features(house_style: str) -> List[str]:
    """Get the list of features for a house style."""
    base_features = ["foundation", "floor", "walls", "windows", "door", "flat_roof"]
    if house_style == "cottage":
        base_features.append("chimney")
    if house_style == "modern":
        base_features.append("garage")
    return base_features