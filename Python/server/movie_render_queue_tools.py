"""Movie Render Queue (Sub-batch M, issue #53) MCP tools (auto-generated scaffold).

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
def create_mrq_job(job_name: str = "NewMRQJob") -> Dict[str, Any]:
    """create_mrq_job -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_mrq_job", {"job_name": job_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_mrq_job': {e}")
    return _envelope("create_mrq_job", r)


@mcp.tool()
def add_sequence_to_mrq(job_name: str, level_path: str, sequence_path: str) -> Dict[str, Any]:
    """add_sequence_to_mrq -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
        validate_string(level_path, "level_path")
        validate_string(sequence_path, "sequence_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_sequence_to_mrq", {"job_name": job_name, "level_path": level_path, "sequence_path": sequence_path})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_sequence_to_mrq': {e}")
    return _envelope("add_sequence_to_mrq", r)


@mcp.tool()
def set_mrq_output_directory(job_name: str, output_directory: str) -> Dict[str, Any]:
    """set_mrq_output_directory -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
        validate_string(output_directory, "output_directory")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_output_directory", {"job_name": job_name, "output_directory": output_directory})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_output_directory': {e}")
    return _envelope("set_mrq_output_directory", r)


@mcp.tool()
def set_mrq_resolution(job_name: str, width: int = 1920, height: int = 1080) -> Dict[str, Any]:
    """set_mrq_resolution -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_resolution", {"job_name": job_name, "width": int(width), "height": int(height)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_resolution': {e}")
    return _envelope("set_mrq_resolution", r)


@mcp.tool()
def set_mrq_frame_range(job_name: str, start_frame: int = 0, end_frame: int = 120) -> Dict[str, Any]:
    """set_mrq_frame_range -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_frame_range", {"job_name": job_name, "start_frame": int(start_frame), "end_frame": int(end_frame)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_frame_range': {e}")
    return _envelope("set_mrq_frame_range", r)


@mcp.tool()
def set_mrq_anti_aliasing(job_name: str, spatial_samples: int = 4, temporal_samples: int = 1) -> Dict[str, Any]:
    """set_mrq_anti_aliasing -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_anti_aliasing", {"job_name": job_name, "spatial_samples": int(spatial_samples), "temporal_samples": int(temporal_samples)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_anti_aliasing': {e}")
    return _envelope("set_mrq_anti_aliasing", r)


@mcp.tool()
def set_mrq_exr_output(job_name: str, bit_depth: int = 16, compression: str = "ZIP") -> Dict[str, Any]:
    """set_mrq_exr_output -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_exr_output", {"job_name": job_name, "bit_depth": int(bit_depth), "compression": compression})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_exr_output': {e}")
    return _envelope("set_mrq_exr_output", r)


@mcp.tool()
def set_mrq_png_output(job_name: str, enabled: bool = True) -> Dict[str, Any]:
    """set_mrq_png_output -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_png_output", {"job_name": job_name, "enabled": bool(enabled)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_png_output': {e}")
    return _envelope("set_mrq_png_output", r)


@mcp.tool()
def set_mrq_jpg_output(job_name: str, quality: int = 80) -> Dict[str, Any]:
    """set_mrq_jpg_output -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_jpg_output", {"job_name": job_name, "quality": int(quality)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_jpg_output': {e}")
    return _envelope("set_mrq_jpg_output", r)


@mcp.tool()
def set_mrq_video_output(job_name: str, format: str = "ProRes422") -> Dict[str, Any]:
    """set_mrq_video_output -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_video_output", {"job_name": job_name, "format": format})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_video_output': {e}")
    return _envelope("set_mrq_video_output", r)


@mcp.tool()
def set_mrq_path_tracer(job_name: str, enable: bool = True) -> Dict[str, Any]:
    """set_mrq_path_tracer -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_path_tracer", {"job_name": job_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_path_tracer': {e}")
    return _envelope("set_mrq_path_tracer", r)


@mcp.tool()
def set_mrq_console_variables(job_name: str, cvars: list = []) -> Dict[str, Any]:
    """set_mrq_console_variables -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_console_variables", {"job_name": job_name, "cvars": cvars})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_console_variables': {e}")
    return _envelope("set_mrq_console_variables", r)


@mcp.tool()
def add_mrq_render_pass(job_name: str, pass_type: str = "ObjectId") -> Dict[str, Any]:
    """add_mrq_render_pass -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("add_mrq_render_pass", {"job_name": job_name, "pass_type": pass_type})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'add_mrq_render_pass': {e}")
    return _envelope("add_mrq_render_pass", r)


@mcp.tool()
def set_mrq_object_id_pass(job_name: str, enable: bool = True) -> Dict[str, Any]:
    """set_mrq_object_id_pass -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_object_id_pass", {"job_name": job_name, "enable": bool(enable)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_object_id_pass': {e}")
    return _envelope("set_mrq_object_id_pass", r)


@mcp.tool()
def set_mrq_burn_in(job_name: str, burn_in_class: str = "") -> Dict[str, Any]:
    """set_mrq_burn_in -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_burn_in", {"job_name": job_name, "burn_in_class": burn_in_class})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_burn_in': {e}")
    return _envelope("set_mrq_burn_in", r)


@mcp.tool()
def set_mrq_warm_up(job_name: str, warm_up_frames: int = 30) -> Dict[str, Any]:
    """set_mrq_warm_up -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("set_mrq_warm_up", {"job_name": job_name, "warm_up_frames": int(warm_up_frames)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'set_mrq_warm_up': {e}")
    return _envelope("set_mrq_warm_up", r)


@mcp.tool()
def start_mrq_render(job_name: str) -> Dict[str, Any]:
    """start_mrq_render -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("start_mrq_render", {"job_name": job_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'start_mrq_render': {e}")
    return _envelope("start_mrq_render", r)


@mcp.tool()
def cancel_mrq_render(job_name: str) -> Dict[str, Any]:
    """cancel_mrq_render -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("cancel_mrq_render", {"job_name": job_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'cancel_mrq_render': {e}")
    return _envelope("cancel_mrq_render", r)


@mcp.tool()
def get_mrq_render_progress(job_name: str) -> Dict[str, Any]:
    """get_mrq_render_progress -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("get_mrq_render_progress", {"job_name": job_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'get_mrq_render_progress': {e}")
    return _envelope("get_mrq_render_progress", r)


@mcp.tool()
def verify_mrq_render_result(job_name: str, expect_frame_count: int = 120) -> Dict[str, Any]:
    """verify_mrq_render_result -- queued (see C++ handler for runtime depth)."""
    try:
        validate_string(job_name, "job_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("verify_mrq_render_result", {"job_name": job_name, "expect_frame_count": int(expect_frame_count)})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'verify_mrq_render_result': {e}")
    return _envelope("verify_mrq_render_result", r)


@mcp.tool()
def create_movie_render_graph(asset_path: str = "/Game/Cine", asset_name: str = "MRG_New") -> Dict[str, Any]:
    """create_movie_render_graph -- queued (see C++ handler for runtime depth)."""
    try:
        pass
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("create_movie_render_graph", {"asset_path": asset_path, "asset_name": asset_name})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command 'create_movie_render_graph': {e}")
    return _envelope("create_movie_render_graph", r)
