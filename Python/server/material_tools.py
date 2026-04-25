"""Material-related tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from utils.responses import make_error_response, is_success_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def get_available_materials(
    search_path: str = "/Game/",
    include_engine_materials: bool = True
) -> Dict[str, Any]:
    """Get a list of available materials in the project that can be applied to objects."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "search_path": search_path,
            "include_engine_materials": include_engine_materials
        }
        response = unreal.send_command("get_available_materials", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"get_available_materials error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def apply_material_to_actor(
    actor_name: str,
    material_path: str,
    material_slot: int = 0
) -> Dict[str, Any]:
    """Apply a specific material to an actor in the level."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "actor_name": actor_name,
            "material_path": material_path,
            "material_slot": material_slot
        }
        response = unreal.send_command("apply_material_to_actor", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"apply_material_to_actor error: {e}")
        return make_error_response(str(e))


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
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "material_path": material_path,
            "material_slot": material_slot
        }
        response = unreal.send_command("apply_material_to_blueprint", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"apply_material_to_blueprint error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def get_actor_material_info(
    actor_name: str
) -> Dict[str, Any]:
    """Get information about the materials currently applied to an actor."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"actor_name": actor_name}
        response = unreal.send_command("get_actor_material_info", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"get_actor_material_info error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def get_blueprint_material_info(
    blueprint_name: str,
    component_name: str
) -> Dict[str, Any]:
    """Get information about the materials currently applied to a Blueprint component."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "blueprint_name": blueprint_name,
            "component_name": component_name
        }
        response = unreal.send_command("get_blueprint_material_info", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"get_blueprint_material_info error: {e}")
        return make_error_response(str(e))


# Deprecated alias for backwards compatibility; prefer the decorated tool above.
# get_blueprint_material_info is the canonical MCP tool.
_get_blueprint_material_info_alias = get_blueprint_material_info


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
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        if not isinstance(color, list) or len(color) != 4:
            return make_error_response("Invalid color format. Must be a list of 4 float values [R, G, B, A].")

        validated_color = [float(min(1.0, max(0.0, val))) for val in color]

        params_primary = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "color": validated_color,
            "material_path": material_path,
            "parameter_name": parameter_name,
            "material_slot": material_slot
        }
        response_primary = unreal.send_command("set_mesh_material_color", params_primary)

        if response_primary and is_success_response(response_primary):
            return {
                "success": True,
                "message": f"Color applied via parameter '{parameter_name}' on slot {material_slot}: {validated_color}",
                "result": response_primary,
                "material_slot": material_slot
            }

        fallback_names = []
        if parameter_name != "BaseColor":
            fallback_names.append("BaseColor")
        if parameter_name != "Color":
            fallback_names.append("Color")

        fallback_results = []
        for fallback_name in fallback_names:
            params_fb = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "color": validated_color,
                "material_path": material_path,
                "parameter_name": fallback_name,
                "material_slot": material_slot
            }
            response_fb = unreal.send_command("set_mesh_material_color", params_fb)
            fallback_results.append((fallback_name, response_fb))
            if response_fb and is_success_response(response_fb):
                return {
                    "success": True,
                    "message": f"Color applied via fallback parameter '{fallback_name}' on slot {material_slot}: {validated_color}",
                    "result": response_fb,
                    "material_slot": material_slot,
                    "fallback_used": fallback_name
                }

        return make_error_response(
            f"Failed to set color on slot {material_slot}. "
            f"Primary parameter '{parameter_name}' and all fallbacks failed.",
            primary_result=response_primary,
            fallback_results=fallback_results,
        )

    except Exception as e:
        logger.error(f"set_mesh_material_color error: {e}")
        return make_error_response(str(e))