"""Sequencer / Cinematics extensions (Sub-batch Z, issue #52) MCP tools (auto-generated scaffold).

Each tool wraps a single C++ handler. The C++ side returns a queued
envelope when the underlying plugin is missing; the wrappers surface that
to the caller via an actionable error envelope.
"""

from typing import Any, Dict

from server.core import mcp, get_unreal_connection
from server.validation import (
    validate_string,
    ValidationError,
    make_validation_error_response_from_exception,
)
from utils.responses import make_error_response


def _envelope(name: str, result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return make_error_response(f"Unexpected Unreal response for '{name}'")
    if not result.get("success", False):
        err = result.get("error", "unknown error")
        hint = result.get("hint")
        return make_error_response(f"{name}: {err}" + (f" (hint: {hint})" if hint else ""))
    return result


@mcp.tool()
def spawn_camera_rail(actor_name: str = "CameraRail", rail_spline_points: list = []) -> Dict[str, Any]:
    """spawn_camera_rail -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_camera_rail", {"actor_name": actor_name, "rail_spline_points": rail_spline_points})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_camera_rail': {e}")
    return _envelope("spawn_camera_rail", r)


@mcp.tool()
def spawn_camera_crane(actor_name: str = "CameraCrane", height: float = 300.0) -> Dict[str, Any]:
    """spawn_camera_crane -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_camera_crane", {"actor_name": actor_name, "height": float(height)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_camera_crane': {e}")
    return _envelope("spawn_camera_crane", r)


@mcp.tool()
def sequencer_render_preview(level_sequence_path: str) -> Dict[str, Any]:
    """sequencer_render_preview -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(level_sequence_path, "level_sequence_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("sequencer_render_preview", {"level_sequence_path": level_sequence_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'sequencer_render_preview': {e}")
    return _envelope("sequencer_render_preview", r)


@mcp.tool()
def register_take_recorder_source(source_class: str = "ActorRecorder", target_actor: str = "") -> Dict[str, Any]:
    """register_take_recorder_source -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("register_take_recorder_source", {"source_class": source_class, "target_actor": target_actor})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'register_take_recorder_source': {e}")
    return _envelope("register_take_recorder_source", r)


@mcp.tool()
def add_control_rig_track(level_sequence_path: str, binding_id: str, control_rig_path: str) -> Dict[str, Any]:
    """add_control_rig_track -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(level_sequence_path, "level_sequence_path")
        validate_string(binding_id, "binding_id")
        validate_string(control_rig_path, "control_rig_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_control_rig_track", {"level_sequence_path": level_sequence_path, "binding_id": binding_id, "control_rig_path": control_rig_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_control_rig_track': {e}")
    return _envelope("add_control_rig_track", r)


@mcp.tool()
def spawn_level_sequence_actor(level_sequence_path: str, actor_name: str = "LevelSequenceActor") -> Dict[str, Any]:
    """spawn_level_sequence_actor -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(level_sequence_path, "level_sequence_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_level_sequence_actor", {"level_sequence_path": level_sequence_path, "actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_level_sequence_actor': {e}")
    return _envelope("spawn_level_sequence_actor", r)
