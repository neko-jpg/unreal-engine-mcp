"""Testing / Validation extensions (Sub-batch W, issue #57) MCP tools (auto-generated scaffold).

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
def create_ue_automation_test(test_name: str, category: str = "Game") -> Dict[str, Any]:
    """create_ue_automation_test -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(test_name, "test_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_ue_automation_test", {"test_name": test_name, "category": category})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_ue_automation_test': {e}")
    return _envelope("create_ue_automation_test", r)


@mcp.tool()
def spawn_functional_test_actor(actor_name: str = "FuncTest", map_path: str = "") -> Dict[str, Any]:
    """spawn_functional_test_actor -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("spawn_functional_test_actor", {"actor_name": actor_name, "map_path": map_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'spawn_functional_test_actor': {e}")
    return _envelope("spawn_functional_test_actor", r)


@mcp.tool()
def run_automation_test(test_name_filter: str = "Game") -> Dict[str, Any]:
    """run_automation_test -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_automation_test", {"test_name_filter": test_name_filter})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_automation_test': {e}")
    return _envelope("run_automation_test", r)


@mcp.tool()
def fetch_automation_test_results(run_id: str = "") -> Dict[str, Any]:
    """fetch_automation_test_results -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("fetch_automation_test_results", {"run_id": run_id})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'fetch_automation_test_results': {e}")
    return _envelope("fetch_automation_test_results", r)


@mcp.tool()
def run_collision_validation(scope: str = "Level") -> Dict[str, Any]:
    """run_collision_validation -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_collision_validation", {"scope": scope})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_collision_validation': {e}")
    return _envelope("run_collision_validation", r)


@mcp.tool()
def run_navigation_validation(scope: str = "Level") -> Dict[str, Any]:
    """run_navigation_validation -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_navigation_validation", {"scope": scope})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_navigation_validation': {e}")
    return _envelope("run_navigation_validation", r)


@mcp.tool()
def run_performance_budget_validation(max_frame_ms: float = 16.6, max_gpu_ms: float = 16.6, max_memory_mb: int = 4096) -> Dict[str, Any]:
    """run_performance_budget_validation -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_performance_budget_validation", {"max_frame_ms": float(max_frame_ms), "max_gpu_ms": float(max_gpu_ms), "max_memory_mb": int(max_memory_mb)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_performance_budget_validation': {e}")
    return _envelope("run_performance_budget_validation", r)


@mcp.tool()
def run_gameplay_screenshot_test(screenshot_id: str) -> Dict[str, Any]:
    """run_gameplay_screenshot_test -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(screenshot_id, "screenshot_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_gameplay_screenshot_test", {"screenshot_id": screenshot_id})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_gameplay_screenshot_test': {e}")
    return _envelope("run_gameplay_screenshot_test", r)


@mcp.tool()
def run_python_unit_test(test_path: str = "Python/tests/unit") -> Dict[str, Any]:
    """run_python_unit_test -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_python_unit_test", {"test_path": test_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_python_unit_test': {e}")
    return _envelope("run_python_unit_test", r)


@mcp.tool()
def run_rust_test(test_filter: str = "") -> Dict[str, Any]:
    """run_rust_test -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("run_rust_test", {"test_filter": test_filter})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'run_rust_test': {e}")
    return _envelope("run_rust_test", r)
