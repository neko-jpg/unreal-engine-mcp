"""Common helpers and shared imports for scene tool modules."""

import logging
from typing import Any, Dict, List, Optional

from server.core import mcp, get_unreal_connection
from server.scene_client import call_scene_syncd, call_scene_syncd_get
from server.actor_sink import ActorSpec, SceneDbActorSink
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception, sanitize_mcp_id, normalize_scene_id
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


def _scene_syncd_error_response(result: Dict[str, Any], operation: str) -> Dict[str, Any]:
    """Convert a scene-syncd error response to a consistent error format."""
    if result.get("success") is False and result.get("error"):
        err = result["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return make_error_response(f"scene-syncd {operation} failed: {msg}")
    return result


def _scene_syncd_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the scene-syncd data envelope when present."""
    data = result.get("data")
    return data if isinstance(data, dict) else result


def _extract_layout_kind(obj: Dict[str, Any]) -> str:
    visual = obj.get("visual") or {}
    draft = visual.get("draft") if isinstance(visual, dict) else None
    if isinstance(draft, dict) and draft.get("proxy_group"):
        return str(draft["proxy_group"])
    for tag in obj.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("layout_kind:"):
            return tag.split(":", 1)[1]
    return "layout"


def _object_to_draft_instance(obj: Dict[str, Any]) -> Dict[str, Any]:
    transform = obj.get("transform") or {}
    instance = {
        "location": transform.get("location") or {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": transform.get("rotation") or {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
        "scale": transform.get("scale") or {"x": 1.0, "y": 1.0, "z": 1.0},
    }
    visual = obj.get("visual") or {}
    draft = visual.get("draft") if isinstance(visual, dict) else None
    if isinstance(draft, dict) and draft.get("color") is not None:
        instance["color"] = draft["color"]
    return instance


def _send_draft_proxy_replace(
    conn: Any,
    proxy_name: str,
    mesh_path: str,
    material_path: Optional[str],
    instances: List[Dict[str, Any]],
    use_dither: bool,
) -> Dict[str, Any]:
    create_params: Dict[str, Any] = {
        "proxy_name": proxy_name,
        "mesh_path": mesh_path,
        "instances": instances,
        "use_dither": use_dither,
    }
    if material_path:
        create_params["material_path"] = material_path

    result = conn.send_command("create_draft_proxy", create_params)
    if result.get("success", False):
        return result

    error = str(result.get("error", ""))
    if "already exists" not in error:
        return result

    update_params: Dict[str, Any] = {
        "proxy_name": proxy_name,
        "instances": instances,
        "use_dither": use_dither,
    }
    if material_path:
        update_params["material_path"] = material_path
    return conn.send_command("update_draft_proxy", update_params)


def _unreal_envelope(name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("success", False):
        error = result.get("error", "unknown error")
        return make_error_response(f"Unreal command '{name}' failed: {error}")
    return {"success": True, "unreal_result": result}
