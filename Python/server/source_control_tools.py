"""Source Control / Multi-User (Sub-batch U, issue #60) MCP tools (auto-generated scaffold).

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
def register_git_provider(repo_path: str, lfs_enabled: bool = True) -> Dict[str, Any]:
    """register_git_provider -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(repo_path, "repo_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("register_git_provider", {"repo_path": repo_path, "lfs_enabled": bool(lfs_enabled)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'register_git_provider': {e}")
    return _envelope("register_git_provider", r)


@mcp.tool()
def register_perforce_provider(server: str, user: str, workspace: str) -> Dict[str, Any]:
    """register_perforce_provider -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(server, "server")
        validate_string(user, "user")
        validate_string(workspace, "workspace")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("register_perforce_provider", {"server": server, "user": user, "workspace": workspace})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'register_perforce_provider': {e}")
    return _envelope("register_perforce_provider", r)


@mcp.tool()
def source_control_checkout(asset_paths: list) -> Dict[str, Any]:
    """source_control_checkout -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_checkout", {"asset_paths": asset_paths})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_checkout': {e}")
    return _envelope("source_control_checkout", r)


@mcp.tool()
def source_control_checkin(asset_paths: list, description: str = "Auto-checkin") -> Dict[str, Any]:
    """source_control_checkin -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_checkin", {"asset_paths": asset_paths, "description": description})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_checkin': {e}")
    return _envelope("source_control_checkin", r)


@mcp.tool()
def source_control_revert(asset_paths: list) -> Dict[str, Any]:
    """source_control_revert -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_revert", {"asset_paths": asset_paths})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_revert': {e}")
    return _envelope("source_control_revert", r)


@mcp.tool()
def source_control_file_lock_acquire(asset_paths: list) -> Dict[str, Any]:
    """source_control_file_lock_acquire -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_file_lock_acquire", {"asset_paths": asset_paths})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_file_lock_acquire': {e}")
    return _envelope("source_control_file_lock_acquire", r)


@mcp.tool()
def source_control_file_lock_release(asset_paths: list) -> Dict[str, Any]:
    """source_control_file_lock_release -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_file_lock_release", {"asset_paths": asset_paths})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_file_lock_release': {e}")
    return _envelope("source_control_file_lock_release", r)


@mcp.tool()
def source_control_create_changelist(description: str = "New changelist") -> Dict[str, Any]:
    """source_control_create_changelist -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_create_changelist", {"description": description})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_create_changelist': {e}")
    return _envelope("source_control_create_changelist", r)


@mcp.tool()
def source_control_asset_diff(asset_path: str, other_revision: str = "HEAD~1") -> Dict[str, Any]:
    """source_control_asset_diff -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_asset_diff", {"asset_path": asset_path, "other_revision": other_revision})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_asset_diff': {e}")
    return _envelope("source_control_asset_diff", r)


@mcp.tool()
def source_control_blueprint_diff(blueprint_path: str, other_revision: str = "HEAD~1") -> Dict[str, Any]:
    """source_control_blueprint_diff -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(blueprint_path, "blueprint_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_blueprint_diff", {"blueprint_path": blueprint_path, "other_revision": other_revision})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_blueprint_diff': {e}")
    return _envelope("source_control_blueprint_diff", r)


@mcp.tool()
def source_control_merge(asset_path: str) -> Dict[str, Any]:
    """source_control_merge -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("source_control_merge", {"asset_path": asset_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'source_control_merge': {e}")
    return _envelope("source_control_merge", r)


@mcp.tool()
def multi_user_editing_start(session_name: str = "DefaultMU") -> Dict[str, Any]:
    """multi_user_editing_start -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("multi_user_editing_start", {"session_name": session_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'multi_user_editing_start': {e}")
    return _envelope("multi_user_editing_start", r)


@mcp.tool()
def multi_user_session_join(session_url: str) -> Dict[str, Any]:
    """multi_user_session_join -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(session_url, "session_url")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("multi_user_session_join", {"session_url": session_url})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'multi_user_session_join': {e}")
    return _envelope("multi_user_session_join", r)
