"""Packaging / Build / Deployment extensions (Sub-batch AA, issue #56) MCP tools.

Each tool wraps a single C++ handler on route 42.  The C++ side actually
mutates ``UProjectPackagingSettings`` via ``TryUpdateDefaultConfigFile()``
(UE 5.7 deprecates ``UpdateDefaultConfigFile()``) and writes
``[CrashReportClient]`` keys through ``GConfig``.  Live Coding is only
available on Editor + Windows builds; on other targets the handler returns
``{"available": false}`` and we forward that success envelope so the caller
can branch on it.

Tools are thin wrappers: optional fields are dropped from the payload when
the caller passes ``None`` so the C++ side can detect "unspecified" vs
"set to false / empty list" and only persist what changed.
"""

from typing import Any, Dict, List, Optional

from server.core import mcp, get_unreal_connection
from utils.responses import make_error_response


def _envelope(name: str, result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return make_error_response(f"Unexpected Unreal response for '{name}'")
    if not result.get("success", False):
        err = result.get("error", "unknown error")
        hint = result.get("hint")
        return make_error_response(f"{name}: {err}" + (f" (hint: {hint})" if hint else ""))
    return result


def _drop_none(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


@mcp.tool()
def set_live_coding_mode(enable: bool, compile_now: bool = False) -> Dict[str, Any]:
    """Toggle Live Coding (UE 5.7 Windows editor only) and optionally request
    an immediate Compile().

    Args:
        enable: Set the session-level Live Coding enabled state.
        compile_now: When True (default False), call
            ``ILiveCodingModule::Compile()`` after the toggle.  Ignored when
            Live Coding cannot be enabled for the current session (e.g. on
            non-Windows / non-Editor builds).

    Returns:
        ``{"success": True, "data": {"available": True/False, "enabled": bool,
        "was_enabled": bool, "started": bool, "compile_triggered": bool, ...}}``.
        Non-Windows / non-Editor builds surface ``available=False`` rather
        than failing so callers can branch on it.
    """
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_live_coding_mode", {
            "enable": bool(enable),
            "compile_now": bool(compile_now),
        })
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_live_coding_mode': {e}")
    return _envelope("set_live_coding_mode", r)


@mcp.tool()
def set_pak_iostore_settings(
    use_pak: Optional[bool] = None,
    use_iostore: Optional[bool] = None,
    compressed: Optional[bool] = None,
    generate_no_chunks: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update Pak / IoStore / compression flags on ``UProjectPackagingSettings``.

    Any argument left as ``None`` is dropped from the payload so the C++ side
    leaves the existing config value untouched.  After mutating the in-memory
    CDO the C++ side calls ``TryUpdateDefaultConfigFile()`` (UE 5.7 replaces
    the deprecated ``UpdateDefaultConfigFile()``).
    """
    payload = _drop_none({
        "use_pak": use_pak,
        "use_iostore": use_iostore,
        "compressed": compressed,
        "generate_no_chunks": generate_no_chunks,
    })
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_pak_iostore_settings", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_pak_iostore_settings': {e}")
    return _envelope("set_pak_iostore_settings", r)


@mcp.tool()
def set_chunk_settings(
    generate_chunks: Optional[bool] = None,
    chunk_hard_references_only: Optional[bool] = None,
    has_chunk_assignment_rules: Optional[bool] = None,
) -> Dict[str, Any]:
    """Configure chunk-generation behaviour on ``UProjectPackagingSettings``.

    ``generate_chunks`` / ``chunk_hard_references_only`` flip the corresponding
    ``UProjectPackagingSettings`` flags and persist via
    ``TryUpdateDefaultConfigFile()``.  ``has_chunk_assignment_rules`` is
    echoed back in the response together with a hint pointing the caller at
    ``UAssetManager`` PrimaryAssetType rules because UE 5.7 keeps chunk
    assignment policy on the asset-manager side rather than on the packaging
    settings object.
    """
    payload = _drop_none({
        "generate_chunks": generate_chunks,
        "chunk_hard_references_only": chunk_hard_references_only,
        "has_chunk_assignment_rules": has_chunk_assignment_rules,
    })
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_chunk_settings", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_chunk_settings': {e}")
    return _envelope("set_chunk_settings", r)


@mcp.tool()
def set_localization_cook_settings(
    cultures_to_stage: Optional[List[str]] = None,
    cook_all: Optional[bool] = None,
    localization_targets_to_chunk: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update Localization / cook scope flags on ``UProjectPackagingSettings``.

    ``cultures_to_stage`` and ``localization_targets_to_chunk`` accept lists
    of culture / target identifier strings.  Passing ``None`` leaves the
    existing list untouched; passing an empty list clears it.  The handler
    persists changes via ``TryUpdateDefaultConfigFile()``.
    """
    payload = _drop_none({
        "cultures_to_stage": cultures_to_stage,
        "cook_all": cook_all,
        "localization_targets_to_chunk": localization_targets_to_chunk,
    })
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_localization_cook_settings", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_localization_cook_settings': {e}")
    return _envelope("set_localization_cook_settings", r)


@mcp.tool()
def set_crash_reporter_settings(
    crash_report_client_email: Optional[str] = None,
    send_unattended_bug_reports: Optional[bool] = None,
    send_usage_data: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update the ``[CrashReportClient]`` section in ``DefaultEngine.ini``.

    UE 5.7 does not expose a UCLASS for client-side crash settings, so the
    handler writes through ``GConfig`` and flushes to the on-disk
    ``DefaultEngine.ini`` (the AGENTS.md ``TryUpdateDefaultConfigFile()``
    rule applies only to UCLASS-backed settings; the equivalent
    ``GConfig->Flush(false, path)`` performs the same role here).
    """
    payload = _drop_none({
        "crash_report_client_email": crash_report_client_email,
        "send_unattended_bug_reports": send_unattended_bug_reports,
        "send_usage_data": send_usage_data,
    })
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_crash_reporter_settings", payload)
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_crash_reporter_settings': {e}")
    return _envelope("set_crash_reporter_settings", r)