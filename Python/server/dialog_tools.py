"""React for UE v3.0 dialog tools.

User-facing tool entry points: scene_edit, scene_refine, scene_preview,
scene_describe, scene_explain_plan, scene_snapshot_restore_by_name,
scene_snapshot_create, scene_list_snapshots.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import threading
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from server.core import mcp
from server.experts.expert_router import default_router
from server.intent.intent_resolver import resolve_intent
from server.intent.scene_summarizer import SceneSummarizer, estimate_tokens
from server.intent.target_resolver import resolve_target
from server.planning.design_patch import (
    AssetPatch,
    ComponentPatch,
    DesignPatch,
    DirectCommandPatch,
    EntityPatch,
    ObjectPatch,
    PatchSafetyReport,
    new_patch_id,
)
from server.planning.safety import SafetyChecker, explain_plan_markdown

logger = logging.getLogger("UnrealMCP_Advanced")


# ---------------------------------------------------------------------------
# Patch store - keeps DesignPatch objects in process memory so subsequent
# scene_explain_plan / scene_edit(apply_safe) calls can refer to them by id.
# ---------------------------------------------------------------------------
class _PatchStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._patches: Dict[str, DesignPatch] = {}
        # FIFO bound to prevent unbounded memory growth.
        self._order: List[str] = []
        self.max_size = 256

    def put(self, patch: DesignPatch) -> None:
        with self._lock:
            self._patches[patch.patch_id] = patch
            self._order.append(patch.patch_id)
            while len(self._order) > self.max_size:
                old_id = self._order.pop(0)
                self._patches.pop(old_id, None)

    def get(self, patch_id: str) -> Optional[DesignPatch]:
        with self._lock:
            return self._patches.get(patch_id)

    def last_for_scene(self, scene_id: str) -> Optional[DesignPatch]:
        with self._lock:
            for pid in reversed(self._order):
                p = self._patches.get(pid)
                if p and p.scene_id == scene_id:
                    return p
        return None


_PATCH_STORE = _PatchStore()


def get_patch_store() -> _PatchStore:
    """Test hook to inspect stored patches."""
    return _PATCH_STORE


class _SceneSyncdClientWrapper:
    """Lightweight wrapper so SceneSummarizer can call scene-syncd directly."""

    @staticmethod
    def call_scene_syncd(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        from server.scene_client import call_scene_syncd
        return call_scene_syncd(path, payload)


def _summarizer_client():
    """Indirection point so tests can monkeypatch the scene-syncd transport.

    Returns a client wrapper if scene-syncd is reachable, otherwise None
    (SceneSummarizer falls back to lazy-importing the default client).
    """
    # Check connectivity without side-effects using a lightweight endpoint.
    try:
        from server.scene_client import call_scene_syncd, SCENE_SYNCD_URL
        import requests

        resp = requests.get(f"{SCENE_SYNCD_URL}/health", timeout=2)
        if resp.status_code == 200:
            return _SceneSyncdClientWrapper()
    except Exception:
        pass
    return None


def _build_design_patch(
    raw_intent: str,
    scene_id: str,
    *,
    target: Optional[str],
    style_profile: Optional[str],
    max_operations: int,
) -> DesignPatch:
    summarizer = SceneSummarizer(client=_summarizer_client())
    context = summarizer.build(scene_id)
    intent_res = resolve_intent(
        raw_intent,
        scene_id=scene_id,
        target=target,
        style_profile=style_profile,
    )
    target_phrase = target
    if not target_phrase and intent_res.intent.target_selector:
        target_phrase = intent_res.intent.target_selector.get("text")
    target_res = resolve_target(target_phrase, context)
    intent = intent_res.intent
    intent.target_selector = target_res.to_dict()

    router = default_router()
    patches = router.propose_all(intent, context)

    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id=scene_id,
        intent=intent,
        summary=f"{intent.action} for mood {intent.mood or 'default'} ({len(patches)} ops)",
        max_operations=max_operations,
        warnings=list(intent_res.warnings),
    )
    for p in patches:
        if isinstance(p, ComponentPatch):
            dp.component_patches.append(p)
        elif isinstance(p, AssetPatch):
            dp.asset_patches.append(p)
        elif isinstance(p, ObjectPatch):
            dp.object_patches.append(p)
        elif isinstance(p, EntityPatch):
            dp.entity_patches.append(p)
        elif isinstance(p, DirectCommandPatch):
            dp.direct_commands.append(p)
    if target_res.ambiguous:
        dp.warnings.append(f"target ambiguous: {target_res.reason}")
        # Per plan: ambiguous target => bump risk to review + require approval
        if dp.risk_level == "safe":
            dp.risk_level = "review"
    dp.fill_component_hashes()
    dp.safety_report = SafetyChecker().check(dp)
    if target_res.ambiguous:
        dp.safety_report.requires_approval = True
    dp.risk_level = dp.safety_report.risk_level
    return dp


@mcp.tool()
def scene_describe(
    scene_id: str = "main",
    detail: str = "compact",
) -> Dict[str, Any]:
    """Return a compact SceneContextPack-style description of a scene."""
    try:
        pack = SceneSummarizer(client=_summarizer_client()).build(scene_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("scene_describe failed")
        return {"success": False, "error": {"code": "scene_describe_failed", "message": str(exc)}}
    payload = pack.to_dict()
    response: Dict[str, Any] = {
        "success": True,
        "scene_id": scene_id,
        "detail": detail,
        "context": payload,
    }
    if detail == "compact":
        response["estimated_tokens"] = estimate_tokens(payload)
    return response


@mcp.tool()
def scene_edit(
    intent: str,
    scene_id: str = "main",
    mode: str = "dry_run",
    create_snapshot: bool = True,
    max_operations: int = 100,
    target: Optional[str] = None,
    style_profile: Optional[str] = None,
    approve: bool = False,
) -> Dict[str, Any]:
    """Plan (and optionally apply) a natural-language scene edit.

    mode:
      - ``dry_run``   : build a DesignPatch and return it. Default.
      - ``apply_safe``: apply patches with risk<=review via PatchExecutor.
      - ``apply_all`` : apply all patches including destructive (needs approve=True).
      - ``agent``     : route intent through the Agent System (MasterOrchestrator).
    """
    try:
        dp = _build_design_patch(
            intent,
            scene_id,
            target=target,
            style_profile=style_profile,
            max_operations=max_operations,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("scene_edit planning failed")
        return {"success": False, "error": {"code": "scene_edit_failed", "message": str(exc)}}
    _PATCH_STORE.put(dp)

    safety = dp.safety_report or SafetyChecker().check(dp)
    response: Dict[str, Any] = {
        "success": True,
        "mode": mode,
        "patch_id": dp.patch_id,
        "summary": dp.summary,
        "risk_level": safety.risk_level,
        "operation_count": safety.operation_count,
        "requires_approval": safety.requires_approval,
        "snapshot_id": None,
        "plan": {
            "object_patches": len(dp.object_patches),
            "entity_patches": len(dp.entity_patches),
            "component_patches": len(dp.component_patches),
            "asset_patches": len(dp.asset_patches),
            "direct_commands": len(dp.direct_commands),
            "validation_probes": len(dp.validation_probes),
        },
        "warnings": list(dp.warnings) + list(safety.warnings),
        "errors": list(safety.errors),
    }

    if mode != "dry_run":
        if mode == "apply_safe":
            from server.planning.patch_executor import apply_patch_safe  # type: ignore
            return apply_patch_safe(
                dp,
                create_snapshot=create_snapshot,
                approve=approve,
                response=response,
            )
        if mode == "apply_all":
            from server.planning.patch_executor import apply_patch_all  # type: ignore
            return apply_patch_all(
                dp,
                create_snapshot=create_snapshot,
                approve=approve,
                response=response,
            )
        if mode == "agent":
            # Natural language intent -> Agent System -> MCP tool execution
            from server.agents import execute_intent

            try:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Already inside a running event loop - run in a thread
                        import concurrent.futures

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                lambda: asyncio.run(
                                    execute_intent(
                                        intent=intent,
                                        scene_id=scene_id,
                                        target=target,
                                        style_profile=style_profile,
                                    )
                                )
                            )
                            agent_result = future.result()
                    else:
                        agent_result = loop.run_until_complete(
                            execute_intent(
                                intent=intent,
                                scene_id=scene_id,
                                target=target,
                                style_profile=style_profile,
                            )
                        )
                except RuntimeError:
                    # No event loop - create one
                    agent_result = asyncio.run(
                        execute_intent(
                            intent=intent,
                            scene_id=scene_id,
                            target=target,
                            style_profile=style_profile,
                        )
                    )

                response["agent_result"] = agent_result.to_dict()
                response["mode"] = "agent"
                if not agent_result.success:
                    response["warnings"].append(
                        f"agent execution warning: {agent_result.error}"
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("agent execution failed")
                response["warnings"].append(f"agent execution failed: {exc}")
            return response
        response["warnings"].append(f"unsupported mode {mode}, treated as dry_run")

    return response


@mcp.tool()
def scene_explain_plan(patch_id: str) -> Dict[str, Any]:
    """Return human and machine readable explanations of a previously planned patch."""
    dp = _PATCH_STORE.get(patch_id)
    if dp is None:
        return {"success": False, "error": {"code": "patch_not_found", "message": patch_id}}
    return {
        "success": True,
        "patch_id": patch_id,
        "markdown": explain_plan_markdown(dp),
        "json": dp.to_dict(),
    }



@mcp.tool()
def scene_snapshot_restore_by_name(
    scene_id: str = "main",
    name: str = "",
    restore_mode: str = "replace_desired",
) -> Dict[str, Any]:
    """Restore a snapshot by name (latest created_at wins when multiple match)."""
    from server.scene_client import call_scene_syncd

    if not name:
        return {"success": False, "error": {"code": "invalid_name", "message": "name is required"}}
    payload = {"scene_id": scene_id, "name": name, "restore_mode": restore_mode}
    raw = call_scene_syncd("/snapshots/restore_by_name", payload)
    return raw



# ---------------------------------------------------------------------------
# PR8: scene_preview + scene_refine
# ---------------------------------------------------------------------------


Vector3 = Tuple[float, float, float]


def _as_vector3(value: Any) -> Optional[Vector3]:
    if isinstance(value, dict):
        try:
            return (
                float(value.get("x", value.get("X", 0.0))),
                float(value.get("y", value.get("Y", 0.0))),
                float(value.get("z", value.get("Z", 0.0))),
            )
        except (TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            return None
    return None


def _extract_object_location(obj: Dict[str, Any]) -> Optional[Vector3]:
    for key in ("location", "position"):
        vec = _as_vector3(obj.get(key))
        if vec is not None:
            return vec
    transform = obj.get("transform")
    if isinstance(transform, dict):
        for key in ("location", "position", "translation"):
            vec = _as_vector3(transform.get(key))
            if vec is not None:
                return vec
    return None


def _extract_object_bounds(obj: Dict[str, Any]) -> List[Vector3]:
    bounds = obj.get("bounds")
    if not isinstance(bounds, dict):
        return []
    points: List[Vector3] = []
    for key in ("min", "max"):
        vec = _as_vector3(bounds.get(key))
        if vec is not None:
            points.append(vec)
    center = _as_vector3(bounds.get("center"))
    size = _as_vector3(bounds.get("size"))
    if center is not None and size is not None:
        half = (abs(size[0]) / 2.0, abs(size[1]) / 2.0, abs(size[2]) / 2.0)
        points.extend([
            (center[0] - half[0], center[1] - half[1], center[2] - half[2]),
            (center[0] + half[0], center[1] + half[1], center[2] + half[2]),
        ])
    return points


def _fetch_preview_objects(scene_id: str) -> List[Dict[str, Any]]:
    client = _summarizer_client()
    if client is not None:
        raw = client.call_scene_syncd("/objects/list", {"scene_id": scene_id})
    else:
        from server.scene_client import call_scene_syncd

        raw = call_scene_syncd("/objects/list", {"scene_id": scene_id})
    data = raw.get("data", raw) if isinstance(raw, dict) else {}
    objects = data.get("objects") if isinstance(data, dict) else None
    return objects if isinstance(objects, list) else []


def _matches_preview_target(obj: Dict[str, Any], target: str) -> bool:
    needle = target.lower()
    for key in ("mcp_id", "name", "id"):
        value = obj.get(key)
        if isinstance(value, str) and value.lower() == needle:
            return True
    tags = obj.get("tags") or []
    return any(isinstance(tag, str) and tag.lower() == needle for tag in tags)


def _scene_focus_from_objects(
    objects: Iterable[Dict[str, Any]],
    *,
    target: Optional[str],
) -> Tuple[Vector3, float, List[str]]:
    warnings: List[str] = []
    candidates = list(objects)
    if target:
        matched = [obj for obj in candidates if _matches_preview_target(obj, target)]
        if matched:
            candidates = matched
        else:
            warnings.append(f"preview target not found in scene metadata: {target}")

    points: List[Vector3] = []
    for obj in candidates:
        points.extend(_extract_object_bounds(obj))
        loc = _extract_object_location(obj)
        if loc is not None:
            points.append(loc)

    if not points:
        return (0.0, 0.0, 0.0), 500.0, warnings

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(
        math.dist(center, p) for p in points
    )
    return center, max(radius, 250.0), warnings


def _look_at_rotation(location: Sequence[float], target: Sequence[float]) -> Vector3:
    dx = float(target[0]) - float(location[0])
    dy = float(target[1]) - float(location[1])
    dz = float(target[2]) - float(location[2])
    yaw = math.degrees(math.atan2(dy, dx))
    horizontal = math.hypot(dx, dy)
    pitch = math.degrees(math.atan2(dz, horizontal))
    return (pitch, yaw, 0.0)


def _preview_camera_views(
    batch: str,
    *,
    center: Vector3,
    radius: float,
    target: Optional[str],
) -> List[Dict[str, Any]]:
    if batch == "single":
        distance = max(radius * 2.4, 650.0)
        z_lift = max(min(radius * 0.18, 260.0), 160.0)
        cx, cy, cz = center
        if target and target.lower() in {"cave", "洞窟"}:
            interior_offset = min(max(radius * 0.18, 250.0), 350.0)
            location = (cx, cy - interior_offset, cz + 10.0)
            look_at = (cx, cy + min(radius * 0.56, 800.0), cz - 10.0)
        else:
            location = (cx - distance, cy - distance * 0.75, cz + z_lift)
            look_at = center
        return [{
            "label": "single",
            "camera_location": location,
            "camera_rotation": _look_at_rotation(location, look_at),
            "camera_look_at": look_at,
        }]

    distance = max(radius * 2.6, 650.0)
    z_lift = max(radius * 0.45, 120.0)
    cx, cy, cz = center

    if batch == "surround":
        specs = [
            ("front", (cx - distance, cy, cz + z_lift)),
            ("back", (cx + distance, cy, cz + z_lift)),
            ("left", (cx, cy - distance, cz + z_lift)),
            ("right", (cx, cy + distance, cz + z_lift)),
            ("top", (cx, cy, cz + distance)),
            ("bird_eye", (cx - distance, cy - distance, cz + distance * 0.75)),
        ]
    elif batch == "orbit" and target:
        specs = []
        for index in range(8):
            angle = (math.tau * index) / 8.0
            specs.append((
                f"orbit_{index}",
                (
                    cx + math.cos(angle) * distance,
                    cy + math.sin(angle) * distance,
                    cz + z_lift,
                ),
            ))
    else:
        return [{"label": "single"}]

    views: List[Dict[str, Any]] = []
    for label, location in specs:
        views.append({
            "label": label,
            "camera_location": location,
            "camera_rotation": _look_at_rotation(location, center),
            "camera_look_at": center,
        })
    return views


@mcp.tool()
def scene_preview(
    scene_id: str = "main",
    target: Optional[str] = None,
    batch: str = "single",  # "single" | "surround" | "orbit"
) -> Dict[str, Any]:
    """Take screenshot(s) and return scene summary + visual metrics.

    Returns images as MCP ImageContent (base64 PNG) so the calling
    multimodal LLM agent can evaluate them directly.  No VLM API is
    called inside the server.

    batch modes:
      - "single": one screenshot (default)
      - "surround": 6 views (front/back/left/right/top/bird_eye)
      - "orbit": 8 views around the target actor
    """
    from server.vision.screenshot import ScreenshotRequest, take_via_focus
    from server.vision.visual_metrics import compute_metrics_for_path
    import base64 as _b64

    try:
        pack = SceneSummarizer(client=_summarizer_client()).build(scene_id)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": {"code": "scene_preview_summary_failed", "message": str(exc)}}

    images: List[Dict[str, Any]] = []
    per_image_metrics: List[Dict[str, Any]] = []
    warnings: List[str] = []

    try:
        objects = _fetch_preview_objects(scene_id)
    except Exception as exc:  # noqa: BLE001
        objects = []
        warnings.append(f"preview object metadata unavailable: {exc}")
    center, radius, focus_warnings = _scene_focus_from_objects(objects, target=target)
    warnings.extend(focus_warnings)
    views = _preview_camera_views(batch, center=center, radius=radius, target=target)

    for view in views:
        pos_label = str(view["label"])
        try:
            shot = take_via_focus(ScreenshotRequest(
                scene_id=scene_id,
                target_actor=target,
                camera_location=view.get("camera_location"),
                camera_rotation=view.get("camera_rotation"),
                camera_look_at=view.get("camera_look_at"),
                label=pos_label,
            ))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"screenshot failed ({pos_label}): {exc}")
            continue
        warnings.extend(getattr(shot, "warnings", []))

        if not shot.success or not shot.path:
            warnings.append(f"screenshot unsuccessful ({pos_label})")
            continue

        # Read PNG bytes and encode as MCP ImageContent.
        try:
            from pathlib import Path as _Path
            img_bytes = _Path(shot.path).read_bytes()
            b64_str = _b64.b64encode(img_bytes).decode("ascii")
            images.append({
                "type": "image",
                "data": b64_str,
                "mime_type": "image/png",
                "label": pos_label,
            })
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"image read failed ({pos_label}): {exc}")
            continue

        # Deterministic metrics (no LLM call).
        try:
            m = compute_metrics_for_path(shot.path)
            per_image_metrics.append(m.to_dict())
        except Exception:  # noqa: BLE001
            pass

    cave_metrics = None
    should_compute_cave = bool(target and target.lower() in {"cave", "cavern", "dungeon", "洞窟"})
    if not should_compute_cave:
        for obj in objects:
            obj_text = " ".join(
                str(v)
                for v in [
                    obj.get("mcp_id"),
                    obj.get("name"),
                    obj.get("desired_name"),
                    obj.get("kind"),
                    " ".join(obj.get("tags") or []) if isinstance(obj.get("tags"), list) else "",
                ]
                if v
            ).lower()
            if any(term in obj_text for term in ("cave", "cavern", "dungeon", "洞窟")):
                should_compute_cave = True
                break
    if should_compute_cave:
        try:
            from server.cave_metrics import compute_cave_metrics

            cave_metrics = compute_cave_metrics(objects, per_image_metrics)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"cave metrics unavailable: {exc}")

    response = {
        "success": True,
        "scene_id": scene_id,
        "context": pack.to_dict(),
        "images": images,
        "per_image_metrics": per_image_metrics,
        "camera_views": views,
        "vlm_status": "delegated_to_agent",
        "warnings": warnings,
    }
    if cave_metrics is not None:
        response["cave_metrics"] = cave_metrics
    return response


@mcp.tool()
def scene_object_info(
    scene_id: str = "main",
    mcp_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    kind: Optional[str] = None,
) -> Dict[str, Any]:
    """Return detailed spatial info for objects in the scene.

    Includes transform (location/rotation/scale), bounds (AABB), direction
    vectors, and attached components.  Data comes from scene-syncd metadata
    supplemented by live UE queries when available.

    Use ``mcp_id`` for a single object, or ``tags``/``kind`` to filter.
    """
    from server.core import get_unreal_connection

    # Fetch from scene-syncd.
    _client = _summarizer_client()
    if _client is not None:
        resp = _client.call_scene_syncd("/objects/list", {"scene_id": scene_id})
    else:
        from server.scene_client import call_scene_syncd
        resp = call_scene_syncd("/objects/list", {"scene_id": scene_id})
    if not resp.get("success"):
        return {"success": False, "error": resp.get("error", "scene-syncd error")}

    objects: List[Dict[str, Any]] = resp.get("data", {}).get("objects", [])

    # Apply filters.
    if mcp_id:
        objects = [o for o in objects if o.get("mcp_id") == mcp_id]
    if tags:
        tag_set = set(tags)
        objects = [o for o in objects if tag_set.issubset(set(o.get("tags", [])))]
    if kind:
        objects = [o for o in objects if o.get("kind") == kind]

    if not objects:
        return {"success": True, "objects": [], "count": 0, "warnings": ["no matching objects"]}

    # Enrich with live UE data (bounds, transform) when available.
    enriched: List[Dict[str, Any]] = []
    ue = None
    try:
        ue = get_unreal_connection()
    except Exception:
        pass

    warnings: List[str] = []
    for obj in objects:
        info: Dict[str, Any] = {
            "mcp_id": obj.get("mcp_id"),
            "name": obj.get("name"),
            "kind": obj.get("kind"),
            "tags": obj.get("tags", []),
            "transform": obj.get("transform", {}),
            "components": obj.get("components", []),
        }

        # Try to get live data from UE.
        if ue is not None:
            actor_name = obj.get("name") or obj.get("mcp_id", "")
            try:
                resp = ue.send_command("get_actor_property", {
                    "actor_name": actor_name,
                    "property": "ActorLocation",
                })
                if resp and resp.get("success") and resp.get("value"):
                    info["location"] = resp["value"]
            except Exception:
                pass

            try:
                resp = ue.send_command("get_actor_property", {
                    "actor_name": actor_name,
                    "property": "ActorRotation",
                })
                if resp and resp.get("success") and resp.get("value"):
                    info["rotation"] = resp["value"]
            except Exception:
                pass

            # Bounds from UE (requires get_actor_bounds C++ handler).
            try:
                bounds_resp = ue.send_command("get_actor_bounds", {
                    "actor_name": actor_name,
                })
                if bounds_resp and bounds_resp.get("success"):
                    info["bounds"] = {
                        "center": bounds_resp.get("center", [0, 0, 0]),
                        "size": bounds_resp.get("size", [0, 0, 0]),
                        "min": bounds_resp.get("min", [0, 0, 0]),
                        "max": bounds_resp.get("max", [0, 0, 0]),
                    }
            except Exception:
                info["bounds"] = None  # Not available yet

            # Direction vectors from UE.
            try:
                vectors = {}
                for prop in ["ActorForwardVector", "ActorRightVector", "ActorUpVector"]:
                    resp = ue.send_command("get_actor_property", {
                        "actor_name": actor_name,
                        "property": prop,
                    })
                    if resp and resp.get("success") and resp.get("value"):
                        key = prop.replace("Actor", "").replace("Vector", "").lower()
                        vectors[key] = resp["value"]
                if vectors:
                    info["direction_vectors"] = vectors
            except Exception:
                pass

        enriched.append(info)

    return {
        "success": True,
        "scene_id": scene_id,
        "objects": enriched,
        "count": len(enriched),
        "warnings": warnings,
    }


@mcp.tool()
def scene_spatial_query(
    scene_id: str = "main",
    query_type: str = "overlap",  # "overlap" | "raycast" | "linecast" | "nearest"
    # overlap params
    center: Optional[Dict[str, float]] = None,
    radius: float = 100.0,
    # raycast/linecast params
    origin: Optional[Dict[str, float]] = None,
    direction: Optional[Dict[str, float]] = None,
    end: Optional[Dict[str, float]] = None,
    max_distance: float = 10000.0,
    # nearest params
    reference_actor: Optional[str] = None,
    # filters
    filter_tags: Optional[List[str]] = None,
    filter_kind: Optional[str] = None,
) -> Dict[str, Any]:
    """Spatial queries against the live UE scene: overlap, raycast, linecast, nearest.

    Returns a list of hits with ``mcp_id``, ``distance``, ``hit_point``,
    ``hit_normal``, and ``hit_component``.

    Requires the C++ ``get_actor_bounds`` / ``spatial_raycast`` /
    ``spatial_overlap_sphere`` handlers.
    """
    from server.core import get_unreal_connection

    try:
        ue = get_unreal_connection()
    except Exception as exc:
        return {"success": False, "error": {"code": "no_unreal_connection", "message": str(exc)}}

    if query_type == "overlap":
        if not center:
            return {"success": False, "error": {"code": "missing_param", "message": "center required for overlap"}}
        resp = ue.send_command("spatial_overlap_sphere", {
            "center": [center.get("x", 0), center.get("y", 0), center.get("z", 0)],
            "radius": radius,
            "filter_tags": filter_tags or [],
            "filter_kind": filter_kind or "",
        })
    elif query_type == "raycast":
        if not origin or not direction:
            return {"success": False, "error": {"code": "missing_param", "message": "origin+direction required for raycast"}}
        resp = ue.send_command("spatial_raycast", {
            "origin": [origin.get("x", 0), origin.get("y", 0), origin.get("z", 0)],
            "direction": [direction.get("x", 0), direction.get("y", 0), direction.get("z", 0)],
            "max_distance": max_distance,
        })
    elif query_type == "linecast":
        if not origin or not end:
            return {"success": False, "error": {"code": "missing_param", "message": "origin+end required for linecast"}}
        resp = ue.send_command("spatial_linecast", {
            "origin": [origin.get("x", 0), origin.get("y", 0), origin.get("z", 0)],
            "end": [end.get("x", 0), end.get("y", 0), end.get("z", 0)],
        })
    elif query_type == "nearest":
        if not reference_actor:
            return {"success": False, "error": {"code": "missing_param", "message": "reference_actor required for nearest"}}
        resp = ue.send_command("spatial_nearest", {
            "reference_actor": reference_actor,
            "filter_tags": filter_tags or [],
            "filter_kind": filter_kind or "",
        })
    else:
        return {"success": False, "error": {"code": "invalid_query_type", "message": f"unknown: {query_type}"}}

    if not resp:
        return {"success": False, "error": {"code": "no_response", "message": "UE did not respond"}}

    hits = resp.get("hits", [])
    return {
        "success": resp.get("success", False),
        "query_type": query_type,
        "hits": hits,
        "count": len(hits),
    }


@mcp.tool()
def scene_refine(
    intent: str,
    scene_id: str = "main",
    ref_patch_id: Optional[str] = None,
    mode: str = "dry_run",
    max_operations: int = 50,
    approve: bool = False,
) -> Dict[str, Any]:
    """Iterative refine: builds a new patch that inherits the prior target/mood."""
    prior = _PATCH_STORE.get(ref_patch_id) if ref_patch_id else _PATCH_STORE.last_for_scene(scene_id)
    target_phrase = None
    style_profile = None
    if prior is not None:
        selector = prior.intent.target_selector or {}
        target_phrase = selector.get("matched_mcp_ids") or selector.get("selector") or selector.get("text")
        if isinstance(target_phrase, list) and target_phrase:
            target_phrase = target_phrase[0]
        style_profile = prior.intent.style_profile or prior.intent.mood

    return scene_edit(
        intent=intent,
        scene_id=scene_id,
        mode=mode,
        max_operations=max_operations,
        target=str(target_phrase) if target_phrase else None,
        style_profile=style_profile,
        approve=approve,
    )



# ---------------------------------------------------------------------------
# Re-exported snapshot tools (PR9): re-expose the existing scene-syncd helpers
# under the v3.0 dialog surface so users do not have to import them separately.
# ---------------------------------------------------------------------------


@mcp.tool()
def scene_snapshot_create_v3(
    scene_id: str = "main",
    name: str = "",
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a named snapshot of the current desired scene state.

    Thin wrapper around the existing scene_snapshot_create tool exposed under
    a v3-friendly name; both tools coexist.
    """
    from server.scene_crud_tools import scene_snapshot_create as _existing

    return _existing(scene_id=scene_id, name=name, description=description)


@mcp.tool()
def scene_list_snapshots_v3(scene_id: str = "main") -> Dict[str, Any]:
    """List all snapshots for a scene (v3 dialog wrapper)."""
    from server.scene_crud_tools import scene_list_snapshots as _existing

    return _existing(scene_id=scene_id)
