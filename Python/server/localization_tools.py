"""Localization (Sub-batch V, issue #58) MCP tools (auto-generated scaffold).

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
def open_localization_dashboard() -> Dict[str, Any]:
    """open_localization_dashboard -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("open_localization_dashboard", {})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'open_localization_dashboard': {e}")
    return _envelope("open_localization_dashboard", r)


@mcp.tool()
def add_localization_culture(culture_code: str, target_name: str = "Game") -> Dict[str, Any]:
    """add_localization_culture -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(culture_code, "culture_code")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_localization_culture", {"culture_code": culture_code, "target_name": target_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_localization_culture': {e}")
    return _envelope("add_localization_culture", r)


@mcp.tool()
def run_text_gather(target_name: str = "Game") -> Dict[str, Any]:
    """run_text_gather -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_text_gather", {"target_name": target_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_text_gather': {e}")
    return _envelope("run_text_gather", r)


@mcp.tool()
def export_po_files(output_directory: str, target_name: str = "Game") -> Dict[str, Any]:
    """export_po_files -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(output_directory, "output_directory")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("export_po_files", {"output_directory": output_directory, "target_name": target_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'export_po_files': {e}")
    return _envelope("export_po_files", r)


@mcp.tool()
def import_po_files(po_directory: str, target_name: str = "Game") -> Dict[str, Any]:
    """import_po_files -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(po_directory, "po_directory")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("import_po_files", {"po_directory": po_directory, "target_name": target_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'import_po_files': {e}")
    return _envelope("import_po_files", r)


@mcp.tool()
def create_string_table(asset_path: str = "/Game/Localization", asset_name: str = "ST_New") -> Dict[str, Any]:
    """create_string_table -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_string_table", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_string_table': {e}")
    return _envelope("create_string_table", r)


@mcp.tool()
def edit_string_table(asset_path: str, entries: list) -> Dict[str, Any]:
    """edit_string_table -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("edit_string_table", {"asset_path": asset_path, "entries": entries})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'edit_string_table': {e}")
    return _envelope("edit_string_table", r)


@mcp.tool()
def localize_widget_text(widget_path: str, text_id: str, translation: str) -> Dict[str, Any]:
    """localize_widget_text -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(widget_path, "widget_path")
        validate_string(text_id, "text_id")
        validate_string(translation, "translation")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("localize_widget_text", {"widget_path": widget_path, "text_id": text_id, "translation": translation})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'localize_widget_text': {e}")
    return _envelope("localize_widget_text", r)


@mcp.tool()
def localize_dialogue_wave(dialogue_wave_path: str, culture_code: str) -> Dict[str, Any]:
    """localize_dialogue_wave -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(dialogue_wave_path, "dialogue_wave_path")
        validate_string(culture_code, "culture_code")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("localize_dialogue_wave", {"dialogue_wave_path": dialogue_wave_path, "culture_code": culture_code})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'localize_dialogue_wave': {e}")
    return _envelope("localize_dialogue_wave", r)


@mcp.tool()
def configure_font_fallback(font_path: str, fallback_fonts: list) -> Dict[str, Any]:
    """configure_font_fallback -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(font_path, "font_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_font_fallback", {"font_path": font_path, "fallback_fonts": fallback_fonts})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_font_fallback': {e}")
    return _envelope("configure_font_fallback", r)
