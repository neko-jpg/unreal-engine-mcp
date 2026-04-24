"""Material-related tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def get_available_materials(
    search_path: str = "/Game/",
    include_engine_materials: bool = True
) -> Dict[str, Any]:
    """Get a list of available materials in the project that can be applied to objects."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {
            "search_path": search_path,
            "include_engine_materials": include_engine_materials
        }
        response = unreal.send_command("get_available_materials", params)
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"get_available_materials error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def apply_material_to_actor(
    actor_name: str,
    material_path: str,
    material_slot: int = 0
) -> Dict[str, Any]:
    """Apply a specific material to an actor in the level."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {
            "actor_name": actor_name,
            "material_path": material_path,
            "material_slot": material_slot
        }
        response = unreal.send_command("apply_material_to_actor", params)
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"apply_material_to_actor error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def apply_material_to_blueprint(
    blueprint_name: str,
    component_name: str,
    material_path: str,
    material_slot: int = 0
) -> Dict[str, Any]:
    """Apply a specific material to a component in a Blueprint."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "material_path": material_path,
            "material_slot": material_slot
        }
        response = unreal.send_command("apply_material_to_blueprint", params)
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"apply_material_to_blueprint error: {e}")
        return {"success": False, "message": str(e)}


@mcp.tool()
def get_actor_material_info(
    actor_name: str
) -> Dict[str, Any]:
    """Get information about the materials currently applied to an actor."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        params = {"actor_name": actor_name}
        response = unreal.send_command("get_actor_material_info", params)
        return response or {"success": False, "message": "No response from Unreal"}
    except Exception as e:
        logger.error(f"get_actor_material_info error: {e}")
        return {"success": False, "message": str(e)}


get_blueprint_material_info = get_actor_material_info


@mcp.tool()
def set_mesh_material_color(
    blueprint_name: str,
    component_name: str,
    color: List[float],
    material_path: str = "/Engine/BasicShapes/BasicShapeMaterial",
    parameter_name: str = "BaseColor",
    material_slot: int = 0
) -> Dict[str, Any]:
    """Set material color on a mesh component using the proven color system."""
    unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Failed to connect to Unreal Engine"}

    try:
        # Validate color format
        if not isinstance(color, list) or len(color) != 4:
            return {"success": False, "message": "Invalid color format. Must be a list of 4 float values [R, G, B, A]."}

        # Ensure all color values are floats between 0 and 1
        color = [float(min(1.0, max(0.0, val))) for val in color]

        # Set BaseColor parameter first
        params_base = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "color": color,
            "material_path": material_path,
            "parameter_name": "BaseColor",
            "material_slot": material_slot
        }
        response_base = unreal.send_command("set_mesh_material_color", params_base)

        # Set Color parameter second (for maximum compatibility)
        params_color = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "color": color,
            "material_path": material_path,
            "parameter_name": "Color",
            "material_slot": material_slot
        }
        response_color = unreal.send_command("set_mesh_material_color", params_color)

        # Return success if either parameter setting worked
        if (response_base and response_base.get("status") == "success") or (response_color and response_color.get("status") == "success"):
            return {
                "success": True,
                "message": f"Color applied successfully to slot {material_slot}: {color}",
                "base_color_result": response_base,
                "color_result": response_color,
                "material_slot": material_slot
            }
        else:
            return {
                "success": False,
                "message": f"Failed to set color parameters on slot {material_slot}. BaseColor: {response_base}, Color: {response_color}"
            }

    except Exception as e:
        logger.error(f"set_mesh_material_color error: {e}")
        return {"success": False, "message": str(e)}
