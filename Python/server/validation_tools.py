"""Validation and testing tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional

from server.core import mcp, get_unreal_connection
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def compile_all_blueprints() -> Dict[str, Any]:
    """Compile all Blueprint assets in the project and report errors/warnings."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command("compile_all_blueprints", {})
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"compile_all_blueprints error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def run_map_check() -> Dict[str, Any]:
    """Run the editor's map check on the current level.

    Returns errors and warnings such as actors without root components,
    missing static meshes, etc.
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command("run_map_check", {})
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"run_map_check error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def find_broken_references() -> Dict[str, Any]:
    """Scan the current level for actors with broken references (missing mesh/material).

    Returns a list of affected actors and the specific issues found.
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command("find_broken_references", {})
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"find_broken_references error: {e}")
        return make_error_response(str(e))

# W1-B Validation / Profiling residue (UE 5.7)


@mcp.tool()
def set_auto_save_settings(
    auto_save_enable: Optional[bool] = None,
    auto_save_time_minutes: Optional[int] = None,
    auto_save_warning_in_seconds: Optional[int] = None,
    auto_save_content: Optional[bool] = None,
    auto_save_maps: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update UEditorLoadingSavingSettings auto-save fields.

    Persists via TryUpdateDefaultConfigFile() (UE 5.7 supported API).
    At least one field must be provided.
    """
    fields = {
        "auto_save_enable": auto_save_enable,
        "auto_save_time_minutes": auto_save_time_minutes,
        "auto_save_warning_in_seconds": auto_save_warning_in_seconds,
        "auto_save_content": auto_save_content,
        "auto_save_maps": auto_save_maps,
    }
    payload = {k: v for k, v in fields.items() if v is not None}
    if not payload:
        return make_error_response("Provide at least one auto-save field to update")
    if auto_save_time_minutes is not None and auto_save_time_minutes < 1:
        return make_error_response("auto_save_time_minutes must be >= 1")
    if auto_save_warning_in_seconds is not None and auto_save_warning_in_seconds < 0:
        return make_error_response("auto_save_warning_in_seconds must be >= 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("set_auto_save_settings", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_auto_save_settings error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def get_editor_stats(stat_command: Optional[str] = None) -> Dict[str, Any]:
    """Snapshot FPS / delta time / process memory and optionally exec a stat command.

    stat_command: Optional console command to issue on the editor world
                 (e.g. "stat unit", "stat GPU", "stat NetStats").
    """
    if stat_command is not None and not isinstance(stat_command, str):
        return make_error_response("stat_command must be a string")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {}
    if stat_command:
        payload["stat_command"] = stat_command
    try:
        response = unreal.send_command("get_editor_stats", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"get_editor_stats error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def start_unreal_insights_trace(
    channels: str = "default,cpu,gpu,frame,bookmark,log",
    trace_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a Trace via FTraceAuxiliary.

    channels: Comma-separated trace channels (UE 5.7 channel names)
    trace_file: Optional absolute disk path; when provided, opens a file connection
    """
    try:
        validate_string(channels, "channels")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"channels": channels}
    if trace_file:
        payload["trace_file"] = trace_file
    try:
        response = unreal.send_command("start_unreal_insights_trace", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"start_unreal_insights_trace error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def stop_unreal_insights_trace() -> Dict[str, Any]:
    """Stop an in-progress Unreal Insights trace via FTraceAuxiliary::Stop()."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("stop_unreal_insights_trace", {})
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"stop_unreal_insights_trace error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def validate_assets(content_path: str = "/Game", max_assets: int = 0) -> Dict[str, Any]:
    """Run UEditorValidatorSubsystem::ValidateAssetsWithSettings over a content path.

    content_path: Asset-registry root to validate (default "/Game")
    max_assets: Optional cap on number of assets to validate (0 = unlimited)
    """
    try:
        validate_string(content_path, "content_path")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if max_assets < 0:
        return make_error_response("max_assets must be >= 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"content_path": content_path}
    if max_assets > 0:
        payload["max_assets"] = max_assets
    try:
        response = unreal.send_command("validate_assets", payload)
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"validate_assets error: {exc}")
        return make_error_response(str(exc))

# W1-H Source Control status + Stat convenience wrappers (UE 5.7)


@mcp.tool()
def get_source_control_status() -> Dict[str, Any]:
    """Query ISourceControlModule for the active provider, availability, and status text.

    Returns a dict with `enabled`, and (when enabled) `provider_name`,
    `status_text`, `available`. When disabled, returns `available_providers`
    (list of provider names that can be activated via the Source Control UI).
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("get_source_control_status", {})
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"get_source_control_status error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def get_fps() -> Dict[str, Any]:
    """Return current editor FPS + delta seconds (UE 5.7).

    Thin wrapper around `get_editor_stats` returning only the FPS-relevant fields.
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("get_editor_stats", {})
        if not response:
            return make_error_response("No response from Unreal")
        return {
            "success": response.get("success", True),
            "fps": response.get("fps"),
            "delta_seconds": response.get("delta_seconds"),
        }
    except Exception as exc:
        logger.error(f"get_fps error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def get_stat_unit() -> Dict[str, Any]:
    """Issue `stat unit` console command on the editor world (UE 5.7).

    The stat overlay is rendered in the viewport; this returns confirmation.
    Use `get_fps` for programmatic FPS sampling.
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("get_editor_stats", {"stat_command": "stat unit"})
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"get_stat_unit error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def get_stat_gpu() -> Dict[str, Any]:
    """Issue `stat gpu` console command on the editor world (UE 5.7).

    The stat overlay is rendered in the viewport; this returns confirmation.
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        response = unreal.send_command("get_editor_stats", {"stat_command": "stat gpu"})
        return response or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"get_stat_gpu error: {exc}")
        return make_error_response(str(exc))
