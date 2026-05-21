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
    _scene_syncd_data,
    _extract_layout_kind,
    _object_to_draft_instance,
    _send_draft_proxy_replace,
)

@mcp.tool()
def scene_generate_layout_objects(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Convert Semantic Layout Graph entities into scene_objects and upsert them into the database.

    Reads all scene_entity and scene_relation records for the scene, denormalizes
    them into scene_object actors, and upserts the results. The generated objects
    can then be synced to Unreal with scene_sync.
    """
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/denormalize", {}), "scene_generate_layout_objects"
    )




@mcp.tool()
def scene_create_layout(
    scene_id: str = "main",
    theme: str = "medieval_european_castle",
    nodes: Optional[List[Dict[str, Any]]] = None,
    edges: Optional[List[Dict[str, Any]]] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a Semantic Layout Graph in the scene database.

    Nodes map to scene_entity records. Edges map to scene_relation records.
    This is the high-level planning entrypoint before preview, approval, and
    realization.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
        validate_string(theme, "theme")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    scene_result = _scene_syncd_error_response(
        _stc.call_scene_syncd(
            "/scenes/create",
            {
                "scene_id": scene_id,
                "name": name or scene_id,
                "description": f"Semantic layout graph: {theme}",
            },
        ),
        "scene_create_layout/scene",
    )
    if scene_result.get("success") is False:
        return scene_result

    result: Dict[str, Any] = {
        "success": True,
        "scene": scene_result,
        "entities": None,
        "relations": None,
    }

    if nodes:
        entity_result = _scene_syncd_error_response(
            _stc.call_scene_syncd(
                "/entities/bulk-upsert",
                {
                    "scene_id": scene_id,
                    "entities": nodes,
                },
            ),
            "scene_create_layout/entities",
        )
        if entity_result.get("success") is False:
            return entity_result
        result["entities"] = entity_result

    if edges:
        relation_result = _scene_syncd_error_response(
            _stc.call_scene_syncd(
                "/relations/bulk-upsert",
                {
                    "scene_id": scene_id,
                    "relations": edges,
                },
            ),
            "scene_create_layout/relations",
        )
        if relation_result.get("success") is False:
            return relation_result
        result["relations"] = relation_result

    return result




@mcp.tool()
def scene_create_draft_proxy(
    proxy_name: str = "draft_layout",
    mesh_path: str = "/Engine/BasicShapes/Cube.Cube",
    material_path: Optional[str] = None,
    instances: Optional[List[Dict[str, Any]]] = None,
    use_dither: bool = False,
) -> Dict[str, Any]:
    """Create a Hierarchical Instanced Static Mesh (HISM) draft proxy in Unreal.

    Lightweight visualization of many instances with a single draw call.
    Instances are translucent cubes by default (no collision, no shadows).
    """
    try:
        validate_string(proxy_name, "proxy_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    try:
        conn = _stc.get_unreal_connection()
        params: Dict[str, Any] = {
            "proxy_name": proxy_name,
            "mesh_path": mesh_path,
            "instances": instances or [],
            "use_dither": use_dither,
        }
        if material_path:
            params["material_path"] = material_path
        unreal_result = conn.send_command("create_draft_proxy", params)
    except Exception as e:
        return make_error_response(f"Failed to create draft proxy in Unreal: {e}")

    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    return {
        "success": True,
        "unreal_result": unreal_result,
    }




@mcp.tool()
def scene_update_draft_proxy(
    proxy_name: str = "draft_layout",
    material_path: Optional[str] = None,
    instances: Optional[List[Dict[str, Any]]] = None,
    use_dither: bool = False,
) -> Dict[str, Any]:
    """Update an existing HISM draft proxy in Unreal (replace all instances)."""
    try:
        validate_string(proxy_name, "proxy_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    try:
        conn = _stc.get_unreal_connection()
        params: Dict[str, Any] = {
            "proxy_name": proxy_name,
            "instances": instances or [],
            "use_dither": use_dither,
        }
        if material_path:
            params["material_path"] = material_path
        unreal_result = conn.send_command("update_draft_proxy", params)
    except Exception as e:
        return make_error_response(f"Failed to update draft proxy in Unreal: {e}")

    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    return {
        "success": True,
        "unreal_result": unreal_result,
    }




@mcp.tool()
def scene_delete_draft_proxy(
    proxy_name: str = "draft_layout",
) -> Dict[str, Any]:
    """Delete a HISM draft proxy from Unreal."""
    try:
        validate_string(proxy_name, "proxy_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    try:
        conn = _stc.get_unreal_connection()
        unreal_result = conn.send_command("delete_draft_proxy", {"proxy_name": proxy_name})
    except Exception as e:
        return make_error_response(f"Failed to delete draft proxy in Unreal: {e}")

    if not unreal_result.get("success", False):
        return make_error_response(
            f"Unreal command failed: {unreal_result.get('error', 'unknown error')}"
        )

    return {
        "success": True,
        "unreal_result": unreal_result,
    }




@mcp.tool()
def scene_show_draft_proxy(
    scene_id: str = "main",
    proxy_name: str = "draft_layout",
    mesh_path: str = "/Engine/BasicShapes/Cube.Cube",
    material_path: Optional[str] = None,
    group_by_kind: bool = True,
    use_dither: bool = True,
) -> Dict[str, Any]:
    """Preview a Semantic Layout Graph in Unreal as HISM draft proxies.

    The layout is denormalized in memory, then batched into one HISM proxy per
    semantic kind by default. Splitting proxies by kind keeps large layouts
    cheap while preserving reviewable structure: walls, towers, keeps, bridges,
    and generated detail can be toggled or deleted independently.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
        validate_string(proxy_name, "proxy_name")
        validate_string(mesh_path, "mesh_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    preview_result = _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/preview", {}),
        "scene_show_draft_proxy/preview",
    )
    if preview_result.get("success") is False:
        return preview_result

    preview_data = _scene_syncd_data(preview_result)
    objects = preview_data.get("objects") or []
    if not isinstance(objects, list):
        return make_error_response("scene-syncd preview response did not include an objects list")

    batches: Dict[str, List[Dict[str, Any]]] = {}
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        group = _extract_layout_kind(obj) if group_by_kind else "layout"
        batches.setdefault(group, []).append(_object_to_draft_instance(obj))

    try:
        conn = _stc.get_unreal_connection()
        proxy_results = []
        for group, instances in sorted(batches.items()):
            batch_proxy_name = f"{proxy_name}_{group}" if group_by_kind else proxy_name
            unreal_result = _send_draft_proxy_replace(
                conn,
                batch_proxy_name,
                mesh_path,
                material_path,
                instances,
                use_dither,
            )
            if not unreal_result.get("success", False):
                return make_error_response(
                    f"Unreal draft proxy '{batch_proxy_name}' failed: "
                    f"{unreal_result.get('error', 'unknown error')}"
                )
            proxy_results.append(
                {
                    "proxy_name": batch_proxy_name,
                    "group": group,
                    "instance_count": len(instances),
                    "unreal_result": unreal_result,
                }
            )
    except Exception as e:
        return make_error_response(f"Failed to show draft proxy in Unreal: {e}")

    return {
        "success": True,
        "scene_id": scene_id,
        "object_count": len(objects),
        "proxy_count": len(proxy_results),
        "proxies": proxy_results,
    }




@mcp.tool()
def scene_update_layout_node(
    scene_id: str = "main",
    entity_id: str = "",
    transform: Optional[Dict[str, Any]] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update a layout node's transform or properties in the scene database.

    This modifies the scene_entity record and can be followed by
    scene_preview_layout or scene_generate_layout_objects to see the result.
    """
    try:
        validate_string(scene_id, "scene_id")
        validate_string(entity_id, "entity_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    payload: Dict[str, Any] = {}
    if transform is not None:
        payload["location"] = transform.get("location")
        payload["rotation"] = transform.get("rotation")
        payload["scale"] = transform.get("scale")
    if properties is not None:
        payload["properties"] = properties

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/nodes/{entity_id}/transform", payload),
        "scene_update_layout_node",
    )




@mcp.tool()
def scene_preview_layout(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Preview the Semantic Layout Graph as scene_objects without persisting them.

    Returns the denormalized objects that would be created by
    scene_generate_layout_objects, useful for reviewing before approval.
    """
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/preview", {}), "scene_preview_layout"
    )




@mcp.tool()
def scene_approve_layout(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Approve the Semantic Layout Graph and prepare it for realization.

    Changes the scene status to 'approved_layout' and creates an auto-snapshot
    for rollback. After approval, use scene_generate_layout_objects followed
    by scene_sync to materialize the layout in Unreal.
    """
    try:
        validate_string(scene_id, "scene_id")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/approve", {}), "scene_approve_layout"
    )




@mcp.tool()
def scene_realize_layout(
    scene_id: str = "main",
    stage: str = "blockout",
    persist: bool = True,
) -> Dict[str, Any]:
    """Realize an approved layout at a given stage.

    Stages:
        blockout  - Use default Cube/Plane placeholders.
        assets    - Bind real assets from the scene_asset library.
        detail    - Apply components and decorative detail (placeholder).
        finalize  - Final production-ready objects.

    When persist=True, the resulting scene_objects are upserted into the DB
    and can then be synced to Unreal with scene_sync.
    """
    try:
        validate_string(scene_id, "scene_id")
        validate_string(stage, "stage")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/realizations/{scene_id}/realize", {
            "stage": stage,
            "persist": persist,
        }),
        "scene_realize_layout",
    )




@mcp.tool()
def scene_compile_preview(
    scene_id: str = "main",
) -> Dict[str, Any]:
    """Generate a preview compilation for a scene.

    Returns a lightweight compilation result suitable for preview
    without persisting changes. Faster than full compile_apply.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    return _scene_syncd_error_response(
        _stc.call_scene_syncd(f"/layouts/{scene_id}/compile/preview", {}), "scene_compile_preview"
    )




