"""MetaSound / Audio extensions (Sub-batch Y, issue #50) MCP tools (auto-generated scaffold).

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
def edit_sound_cue_graph(sound_cue_path: str, node_type: str, node_name: str = "NewNode") -> Dict[str, Any]:
    """edit_sound_cue_graph -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(sound_cue_path, "sound_cue_path")
        validate_string(node_type, "node_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_sound_cue_graph", {"sound_cue_path": sound_cue_path, "node_type": node_type, "node_name": node_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_sound_cue_graph': {e}")
    return _envelope("edit_sound_cue_graph", r)


@mcp.tool()
def create_metasound_source(asset_path: str = "/Game/Audio", asset_name: str = "MS_New") -> Dict[str, Any]:
    """create_metasound_source -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_metasound_source", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_metasound_source': {e}")
    return _envelope("create_metasound_source", r)


@mcp.tool()
def create_metasound_patch(asset_path: str = "/Game/Audio", asset_name: str = "MSP_New") -> Dict[str, Any]:
    """create_metasound_patch -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_metasound_patch", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_metasound_patch': {e}")
    return _envelope("create_metasound_patch", r)


@mcp.tool()
def add_metasound_graph_node(asset_path: str, node_type: str) -> Dict[str, Any]:
    """add_metasound_graph_node -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(asset_path, "asset_path")
        validate_string(node_type, "node_type")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_metasound_graph_node", {"asset_path": asset_path, "node_type": node_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_metasound_graph_node': {e}")
    return _envelope("add_metasound_graph_node", r)


@mcp.tool()
def set_metasound_parameter(actor_name: str, parameter_name: str, value: float = 0.0) -> Dict[str, Any]:
    """set_metasound_parameter -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
        validate_string(parameter_name, "parameter_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_metasound_parameter", {"actor_name": actor_name, "parameter_name": parameter_name, "value": float(value)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_metasound_parameter': {e}")
    return _envelope("set_metasound_parameter", r)


@mcp.tool()
def bind_footstep_audio(anim_sequence_path: str, sound_cue_path: str) -> Dict[str, Any]:
    """bind_footstep_audio -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(anim_sequence_path, "anim_sequence_path")
        validate_string(sound_cue_path, "sound_cue_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("bind_footstep_audio", {"anim_sequence_path": anim_sequence_path, "sound_cue_path": sound_cue_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'bind_footstep_audio': {e}")
    return _envelope("bind_footstep_audio", r)


@mcp.tool()
def configure_ui_sound(widget_class: str, sound_cue_path: str) -> Dict[str, Any]:
    """configure_ui_sound -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(widget_class, "widget_class")
        validate_string(sound_cue_path, "sound_cue_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ui_sound", {"widget_class": widget_class, "sound_cue_path": sound_cue_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ui_sound': {e}")
    return _envelope("configure_ui_sound", r)
