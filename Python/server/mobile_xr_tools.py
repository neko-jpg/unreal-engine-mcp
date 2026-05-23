"""Mobile / XR (Sub-batch T, issue #59) MCP tools (auto-generated scaffold).

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
def configure_android_settings(package_name: str = "com.company.project", min_sdk: int = 26) -> Dict[str, Any]:
    """configure_android_settings -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_android_settings", {"package_name": package_name, "min_sdk": int(min_sdk)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_android_settings': {e}")
    return _envelope("configure_android_settings", r)


@mcp.tool()
def configure_ios_settings(bundle_id: str = "com.company.project", minimum_ios: str = "15.0") -> Dict[str, Any]:
    """configure_ios_settings -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ios_settings", {"bundle_id": bundle_id, "minimum_ios": minimum_ios})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ios_settings': {e}")
    return _envelope("configure_ios_settings", r)


@mcp.tool()
def configure_mobile_rendering(feature_level: str = "ES3_1", forward_shading: bool = True) -> Dict[str, Any]:
    """configure_mobile_rendering -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_mobile_rendering", {"feature_level": feature_level, "forward_shading": bool(forward_shading)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_mobile_rendering': {e}")
    return _envelope("configure_mobile_rendering", r)


@mcp.tool()
def configure_touch_input(enable: bool = True, pinch_zoom: bool = False) -> Dict[str, Any]:
    """configure_touch_input -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_touch_input", {"enable": bool(enable), "pinch_zoom": bool(pinch_zoom)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_touch_input': {e}")
    return _envelope("configure_touch_input", r)


@mcp.tool()
def set_device_profile(profile_name: str = "Android_High") -> Dict[str, Any]:
    """set_device_profile -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_device_profile", {"profile_name": profile_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_device_profile': {e}")
    return _envelope("set_device_profile", r)


@mcp.tool()
def create_scalability_profile(profile_name: str = "High") -> Dict[str, Any]:
    """create_scalability_profile -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_scalability_profile", {"profile_name": profile_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_scalability_profile': {e}")
    return _envelope("create_scalability_profile", r)


@mcp.tool()
def enable_xr_plugin(plugin_name: str = "OpenXR") -> Dict[str, Any]:
    """enable_xr_plugin -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("enable_xr_plugin", {"plugin_name": plugin_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'enable_xr_plugin': {e}")
    return _envelope("enable_xr_plugin", r)


@mcp.tool()
def configure_openxr(session_mode: str = "Stereo") -> Dict[str, Any]:
    """configure_openxr -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_openxr", {"session_mode": session_mode})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_openxr': {e}")
    return _envelope("configure_openxr", r)


@mcp.tool()
def spawn_vr_pawn(actor_name: str = "VRPawn", asset_path: str = "") -> Dict[str, Any]:
    """spawn_vr_pawn -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_vr_pawn", {"actor_name": actor_name, "asset_path": asset_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_vr_pawn': {e}")
    return _envelope("spawn_vr_pawn", r)


@mcp.tool()
def configure_motion_controller(actor_name: str, hand: str = "Right") -> Dict[str, Any]:
    """configure_motion_controller -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_motion_controller", {"actor_name": actor_name, "hand": hand})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_motion_controller': {e}")
    return _envelope("configure_motion_controller", r)


@mcp.tool()
def configure_hmd_camera(actor_name: str) -> Dict[str, Any]:
    """configure_hmd_camera -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_hmd_camera", {"actor_name": actor_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_hmd_camera': {e}")
    return _envelope("configure_hmd_camera", r)


@mcp.tool()
def configure_ar_session(world_alignment: str = "Gravity") -> Dict[str, Any]:
    """configure_ar_session -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ar_session", {"world_alignment": world_alignment})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ar_session': {e}")
    return _envelope("configure_ar_session", r)


@mcp.tool()
def configure_ar_plane_detection(horizontal: bool = True, vertical: bool = False) -> Dict[str, Any]:
    """configure_ar_plane_detection -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("configure_ar_plane_detection", {"horizontal": bool(horizontal), "vertical": bool(vertical)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'configure_ar_plane_detection': {e}")
    return _envelope("configure_ar_plane_detection", r)


@mcp.tool()
def platform_specific_packaging(platform: str = "Android", build_configuration: str = "Shipping") -> Dict[str, Any]:
    """platform_specific_packaging -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("platform_specific_packaging", {"platform": platform, "build_configuration": build_configuration})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'platform_specific_packaging': {e}")
    return _envelope("platform_specific_packaging", r)
