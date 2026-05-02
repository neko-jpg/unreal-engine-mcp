"""Animation and rigging tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_string, validate_unreal_path,
    ValidationError, make_validation_error_response_from_exception
)
from utils.responses import make_error_response, is_success_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def auto_skin_mesh(
    static_mesh_path: str,
    skeleton_path: Optional[str] = None,
    destination_path: Optional[str] = None
) -> Dict[str, Any]:
    """Convert a static mesh to a skeletal mesh and apply automatic skinning weights.

    If skeleton_path is provided, it uses that skeleton (e.g., Epic Skeleton).
    Otherwise, it attempts to generate a basic rig.
    """
    try:
        validate_unreal_path(static_mesh_path, "static_mesh_path")
        if skeleton_path:
            validate_unreal_path(skeleton_path, "skeleton_path")
        if destination_path:
            validate_unreal_path(destination_path, "destination_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"static_mesh_path": static_mesh_path}
        if skeleton_path:
            params["skeleton_path"] = skeleton_path
        if destination_path:
            params["destination_path"] = destination_path

        response = unreal.send_command("auto_skin_mesh", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"auto_skin_mesh error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def generate_control_rig(
    skeletal_mesh_path: str,
    destination_path: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a Control Rig for a given skeletal mesh.

    This adapts the Control Rig to the bone hierarchy of the skeletal mesh.
    """
    try:
        validate_unreal_path(skeletal_mesh_path, "skeletal_mesh_path")
        if destination_path:
            validate_unreal_path(destination_path, "destination_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"skeletal_mesh_path": skeletal_mesh_path}
        if destination_path:
            params["destination_path"] = destination_path

        response = unreal.send_command("generate_control_rig", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"generate_control_rig error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def cleanup_animation(
    animation_path: str,
    bone_names: Optional[List[str]] = None,
    filter_type: str = "Butterworth",
    cutoff_frequency: float = 15.0
) -> Dict[str, Any]:
    """Clean up jitter or interpolation errors in an animation sequence.

    Applies a filter (like Butterworth) to smooth out high-frequency noise.
    """
    try:
        validate_unreal_path(animation_path, "animation_path")
        validate_string(filter_type, "filter_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if bone_names is not None and not isinstance(bone_names, list):
        return make_error_response("bone_names must be a list of strings")

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "animation_path": animation_path,
            "filter_type": filter_type,
            "cutoff_frequency": cutoff_frequency
        }
        if bone_names:
            params["bone_names"] = bone_names

        response = unreal.send_command("cleanup_animation", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"cleanup_animation error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def generate_procedural_anim(
    control_rig_path: str,
    start_pose: Dict[str, Any],
    end_pose: Dict[str, Any],
    duration: float,
    context_parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate procedural animation interpolation between two poses.

    Uses physics context to generate realistic curves for the Control Rig.
    """
    try:
        validate_unreal_path(control_rig_path, "control_rig_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if duration <= 0:
        return make_error_response("duration must be greater than 0")

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "control_rig_path": control_rig_path,
            "start_pose": start_pose,
            "end_pose": end_pose,
            "duration": duration,
        }
        if context_parameters:
            params["context_parameters"] = context_parameters

        response = unreal.send_command("generate_procedural_anim", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"generate_procedural_anim error: {e}")
        return make_error_response(str(e))
