"""Deterministic cave-structure metrics used by scene preview and cave tools."""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, Iterable, List, Optional, Tuple

Vector3 = Tuple[float, float, float]

CAVE_TERMS = (
    "cave",
    "cavern",
    "dungeon",
    "tunnel",
    "chamber",
    "洞窟",
    "洞穴",
    "鍾乳洞",
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


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


def _object_text(obj: Dict[str, Any]) -> str:
    values: List[str] = []
    for key in ("mcp_id", "id", "name", "desired_name", "kind", "actor_type"):
        value = obj.get(key)
        if isinstance(value, str):
            values.append(value)
    asset_ref = obj.get("asset_ref")
    if isinstance(asset_ref, dict) and isinstance(asset_ref.get("path"), str):
        values.append(asset_ref["path"])
    tags = obj.get("tags") or []
    if isinstance(tags, list):
        values.extend(str(tag) for tag in tags if isinstance(tag, str))
    return " ".join(values).lower()


def _bounds_points(obj: Dict[str, Any]) -> List[Vector3]:
    bounds = obj.get("bounds")
    points: List[Vector3] = []
    if isinstance(bounds, dict):
        for key in ("min", "max"):
            vec = _as_vector3(bounds.get(key))
            if vec is not None:
                points.append(vec)
        center = _as_vector3(bounds.get("center"))
        size = _as_vector3(bounds.get("size"))
        if center is not None and size is not None:
            half = (abs(size[0]) / 2.0, abs(size[1]) / 2.0, abs(size[2]) / 2.0)
            points.extend(
                [
                    (center[0] - half[0], center[1] - half[1], center[2] - half[2]),
                    (center[0] + half[0], center[1] + half[1], center[2] + half[2]),
                ]
            )
    if points:
        return points

    transform = obj.get("transform") if isinstance(obj.get("transform"), dict) else {}
    loc = _as_vector3(transform.get("location") or transform.get("position"))
    scale = _as_vector3(transform.get("scale"))
    if loc is not None and scale is not None:
        half = (abs(scale[0]) * 50.0, abs(scale[1]) * 50.0, abs(scale[2]) * 50.0)
        return [
            (loc[0] - half[0], loc[1] - half[1], loc[2] - half[2]),
            (loc[0] + half[0], loc[1] + half[1], loc[2] + half[2]),
        ]
    if loc is not None:
        return [loc]
    return []


def _object_size(obj: Dict[str, Any]) -> Optional[Vector3]:
    points = _bounds_points(obj)
    if len(points) < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def _scene_extent(objects: Iterable[Dict[str, Any]]) -> Vector3:
    points: List[Vector3] = []
    for obj in objects:
        points.extend(_bounds_points(obj))
    if not points:
        return (0.0, 0.0, 0.0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def _has_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _mood_score(visual_metrics: Optional[List[Dict[str, Any]]]) -> float:
    if not visual_metrics:
        return 0.0
    luminance = []
    contrast = []
    cool = []
    for metric in visual_metrics:
        if not isinstance(metric, dict):
            continue
        for source, out in (
            ("luminance_mean", luminance),
            ("contrast", contrast),
            ("blue_cyan_bias", cool),
        ):
            value = metric.get(source)
            if isinstance(value, (int, float)):
                out.append(float(value))
    lum_mean = statistics.fmean(luminance) if luminance else 0.5
    contrast_mean = statistics.fmean(contrast) if contrast else 0.0
    cool_mean = statistics.fmean(cool) if cool else 0.0
    darkness = 1.0 - _clamp(lum_mean)
    return round(_clamp(darkness * 0.55 + _clamp(contrast_mean) * 0.25 + _clamp(cool_mean) * 0.20), 3)


def compute_cave_metrics(
    objects: List[Dict[str, Any]],
    visual_metrics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute cave-likeness from scene metadata and optional image metrics."""
    texts = [_object_text(obj) for obj in objects if isinstance(obj, dict)]
    cave_like = [
        obj for obj, text in zip(objects, texts)
        if _has_any(text, CAVE_TERMS) or _has_any(text, ("wall", "floor", "ceiling", "stone", "rock"))
    ]
    metric_objects = cave_like or objects
    metric_texts = [_object_text(obj) for obj in metric_objects if isinstance(obj, dict)]

    floor_count = sum(1 for text in metric_texts if "floor" in text)
    wall_count = sum(1 for text in metric_texts if "wall" in text)
    ceiling_count = sum(1 for text in metric_texts if "ceiling" in text or "roof" in text)
    cube_count = sum(1 for text in metric_texts if "basicshapes/cube" in text or "cube.cube" in text)
    has_procedural = any(
        _has_any(text, ("procedural", "sdf", "cave_mesh", "domain_warp", "capsule_tunnel"))
        for text in metric_texts
    )
    is_box_cave = (
        not has_procedural
        and floor_count >= 1
        and wall_count >= 3
        and (ceiling_count >= 1 or cube_count >= 5)
    )

    entrance_count = sum(1 for text in metric_texts if "entrance" in text or "mouth" in text or "入口" in text)
    if entrance_count == 0 and (is_box_cave or has_procedural or any(_has_any(t, CAVE_TERMS) for t in metric_texts)):
        entrance_count = 1

    # Read generation metadata first, then fall back to text heuristics.
    meta_branch_count = 0
    meta_chamber_count = 0
    for obj in metric_objects:
        generation = obj.get("generation") if isinstance(obj, dict) else None
        if isinstance(generation, dict):
            meta_branch_count = max(meta_branch_count, int(generation.get("branch_count", 0) or 0))
            meta_chamber_count = max(meta_chamber_count, int(generation.get("chamber_count", 0) or 0))

    text_branch_count = sum(1 for text in metric_texts if "branch" in text or "fork" in text or "side_tunnel" in text)
    tunnel_count = sum(1 for text in metric_texts if "tunnel" in text or "corridor" in text)
    text_chamber_count = sum(1 for text in metric_texts if "chamber" in text or "cavern" in text)
    text_branch_count = max(text_branch_count, max(0, tunnel_count + text_chamber_count - 2))

    branch_count = meta_branch_count or text_branch_count
    chamber_count = meta_chamber_count or text_chamber_count

    extent = _scene_extent(metric_objects)
    max_horizontal_extent = max(extent[0], extent[1])
    depth_score = _clamp(max_horizontal_extent / 1200.0)

    tunnel_widths: List[float] = []
    ceiling_heights: List[float] = []
    for obj in metric_objects:
        size = _object_size(obj)
        if size is None:
            continue
        text = _object_text(obj)
        if _has_any(text, ("tunnel", "cave_mesh", "sdf", "procedural")):
            tunnel_widths.append(max(0.0, min(size[0], size[1])))
        if "ceiling" in text or "cave_mesh" in text or "sdf" in text or "procedural" in text:
            ceiling_heights.append(max(0.0, size[2]))

    if not tunnel_widths and max_horizontal_extent:
        tunnel_widths = [max(0.0, min(extent[0], extent[1]))]
    min_tunnel_width = min(tunnel_widths) if tunnel_widths else 0.0
    avg_tunnel_width = statistics.fmean(tunnel_widths) if tunnel_widths else 0.0

    if len(ceiling_heights) >= 2 and statistics.fmean(ceiling_heights) > 0:
        ceiling_height_variance = _clamp(statistics.pstdev(ceiling_heights) / statistics.fmean(ceiling_heights))
    elif has_procedural:
        ceiling_height_variance = 0.55
    elif is_box_cave:
        ceiling_height_variance = 0.02
    else:
        ceiling_height_variance = 0.18

    if has_procedural:
        wall_curvature_variance = 0.74
    elif is_box_cave:
        wall_curvature_variance = 0.03
    else:
        wall_curvature_variance = _clamp(0.18 + branch_count * 0.08)

    walkable_path_success = bool(floor_count or has_procedural or min_tunnel_width >= 160.0)
    occlusion_score = 0.58 if has_procedural else (0.18 if is_box_cave else 0.32)
    darkness_gradient = _mood_score(visual_metrics)

    cave_score = (
        0.12
        + min(entrance_count, 2) * 0.08
        + depth_score * 0.24
        + min(branch_count, 4) / 4.0 * 0.14
        + wall_curvature_variance * 0.18
        + ceiling_height_variance * 0.08
        + (0.10 if walkable_path_success else 0.0)
        + (0.12 if has_procedural else 0.0)
        - (0.12 if is_box_cave else 0.0)
    )

    return {
        "cave_score": round(_clamp(cave_score), 3),
        "is_box_cave": bool(is_box_cave),
        "has_procedural_cave_mesh": bool(has_procedural),
        "entrance_count": int(entrance_count),
        "depth_score": round(depth_score, 3),
        "branch_count": int(branch_count),
        "loop_estimate": 1 if branch_count >= 3 and has_procedural else 0,
        "walkable_path_success": bool(walkable_path_success),
        "min_tunnel_width": round(min_tunnel_width, 3),
        "avg_tunnel_width": round(avg_tunnel_width, 3),
        "ceiling_height_variance": round(ceiling_height_variance, 3),
        "wall_curvature_variance": round(wall_curvature_variance, 3),
        "darkness_gradient": round(darkness_gradient, 3),
        "occlusion_score": round(occlusion_score, 3),
        "mood_score": round(darkness_gradient, 3),
    }
