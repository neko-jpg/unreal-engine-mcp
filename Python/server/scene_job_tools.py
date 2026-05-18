import logging
from typing import Any, Dict, List, Optional

from server.core import mcp
from server.scene_client import call_scene_syncd_get
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")

import server.scene_tools_common as _stc

from server.scene_tools_common import (
    _scene_syncd_error_response,
    _scene_syncd_data,
)

@mcp.tool()
def scene_procedural_job_submit(
    generator: str,
    params: Dict[str, Any],
    seed: Optional[int] = None,
    limits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Submit a long-running procedural job to scene-syncd. Returns immediately.

    Use this for large WFC grids or deep L-System derivations that risk
    exceeding the synchronous bridge timeout. Returns `{job_id, status}`;
    poll with `scene_procedural_job_status` or wait via
    `scene_procedural_job_result`.

    Args:
        generator: 'wfc' or 'lsystem'.
        params: Generator-specific parameter object (matches the synchronous route shape).
        seed: Optional deterministic seed forwarded to the generator.
        limits: Optional override of safety limits, e.g. {"max_iterations": 200000, "max_execution_ms": 300000}.
    """
    try:
        validate_string(generator, "generator")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    if not isinstance(params, dict):
        return make_error_response("params must be an object")

    payload: Dict[str, Any] = {
        "generator": generator,
        "params": params,
    }
    if seed is not None:
        payload["seed"] = int(seed)
    if limits is not None:
        payload["limits"] = limits

    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/procedural/jobs/submit", payload),
        "scene_procedural_job_submit",
    )




@mcp.tool()
def scene_procedural_job_status(job_id: str) -> Dict[str, Any]:
    """Fetch a procedural job record (status, progress, message, partial result).

    The returned JSON includes:
    - `status`: queued / running / completed / failed / cancelled.
    - `progress`: float in [0,1]; 0.05 at start, 1.0 at completion.
    - `message`: coarse status message (e.g. "queued", "running", "completed").
    - `progress_message` (optional): fine-grained, human-readable progress text
      emitted by the generator itself (e.g. "WFC: collapsed 13/64 cells",
      "L-System: iteration 4/10"). May lag the `progress` fraction by ~200ms.
    - `result`: present once status is `completed`.
    - `error`: present once status is `failed`.
    """
    try:
        validate_string(job_id, "job_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        call_scene_syncd_get(f"/procedural/jobs/{job_id}"),
        "scene_procedural_job_status",
    )




@mcp.tool()
def scene_procedural_job_result(
    job_id: str,
    wait_seconds: float = 0.0,
    poll_interval_seconds: float = 0.5,
) -> Dict[str, Any]:
    """Fetch a procedural job's final result, optionally waiting for completion.

    When `wait_seconds` is 0 the call simply mirrors the latest status snapshot.
    When > 0 it polls until the job reaches a terminal state (completed/failed/
    cancelled) or the wait budget elapses.
    """
    try:
        validate_string(job_id, "job_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    deadline = _time.time() + max(0.0, float(wait_seconds))
    interval = max(0.05, float(poll_interval_seconds))

    last_record: Dict[str, Any] = {}
    while True:
        result = scene_procedural_job_status(job_id)
        if result.get("success") is False:
            return result
        record = _scene_syncd_data(result)
        last_record = record if isinstance(record, dict) else {}
        status = last_record.get("status")
        if status in ("completed", "failed", "cancelled"):
            return {"success": True, "data": last_record}
        if _time.time() >= deadline:
            return {"success": True, "data": last_record}
        _time.sleep(interval)




@mcp.tool()
def scene_procedural_job_cancel(job_id: str) -> Dict[str, Any]:
    """Request cancellation of a queued or running procedural job."""
    try:
        validate_string(job_id, "job_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/procedural/jobs/{job_id}/cancel", {}),
        "scene_procedural_job_cancel",
    )




@mcp.tool()
def scene_procedural_job_list() -> Dict[str, Any]:
    """List recent procedural jobs (queued, running, completed within TTL)."""
    return _scene_syncd_error_response(
        call_scene_syncd_get("/procedural/jobs"),
        "scene_procedural_job_list",
    )




