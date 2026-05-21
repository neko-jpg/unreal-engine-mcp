import logging
from typing import Any, Dict, List, Optional

from server.core import mcp
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")

import server.scene_tools_common as _stc

from server.scene_tools_common import (
    _scene_syncd_error_response,
)

@mcp.tool()
def scene_validate(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Validate a scene for errors, warnings, and optimization opportunities.

    Runs the Rust compiler pipeline in validate-only mode against the scene.
    Returns diagnostics (errors, warnings, infos) and a summary.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/validate", {}), "scene_validate"
    )




@mcp.tool()
def scene_compile_plan(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Generate a compilation plan showing what changes would be applied to Unreal.

    Fetches the actual state from Unreal and diffs it against the desired scene state.
    Returns create/update/delete/noop counts and operation details without modifying Unreal.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/compile/plan", {}), "scene_compile_plan"
    )




@mcp.tool()
def scene_compile_apply(
    scene_id: str = "main",
    allow_delete: bool = False,
) -> Dict[str, Any]:
    """Apply the compilation plan to Unreal.

    Compiles the scene and pushes changes into Unreal. By default deletes are
    disabled for safety. Set allow_delete=True to permit actor removal.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {"scene_id": scene_id, "allow_delete": allow_delete}
    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/compile/apply", payload), "scene_compile_apply"
    )




@mcp.tool()
def scene_run_pie_test(
    scene_id: str = "main",
    mode: str = "smoke",
    timeout_secs: int = 60,
) -> Dict[str, Any]:
    """Run a Play-In-Editor (PIE) test on the scene.

    mode: "smoke" | "full" | "performance"
    timeout_secs: max seconds to wait before force-stopping PIE (capped at 120)
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "mode": mode,
        "timeout_secs": min(max(timeout_secs, 1), 120),
    }
    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/unreal/pie/run", payload), "scene_run_pie_test"
    )




@mcp.tool()
def scene_generate_fix_plan(
    scene_id: str = "main",
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate an automated fix plan from scene diagnostics.

    Accepts a list of diagnostic objects (e.g. from scene_validate or PIE logs)
    and returns a confidence-scored plan of operations to resolve them.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {
        "scene_id": scene_id,
        "diagnostics": diagnostics or [],
    }
    return _scene_syncd_error_response(
        _stc.call_scene_syncd("/unreal/fix-plan", payload), "scene_generate_fix_plan"
    )



# ===================================================================
# Issue #26: Remaining procedural realization commands
# ===================================================================
# Thin wrappers around the C++ EditorCommands handlers added in
# Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPEditorCommands.cpp.
# All four execute on the editor GameThread and return the standard
# {success, data, error?, hint?} envelope. They are intentionally Unreal-only:
# scene-syncd / SurrealDB are NOT touched. To persist generated actors, call
# `scene_upsert_actors` (or pass through `scene_compile_apply`) afterwards.



