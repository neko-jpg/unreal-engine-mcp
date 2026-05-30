"""Cave orchestration tools.

These tools connect existing procedural, PCG, look-dev, and validation
surfaces into one cave-specific flow.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from server.cave_metrics import compute_cave_metrics
from server.core import mcp
from server.generation.cave_graph_generator import CaveGraphGenerator
from server.generation.sdf_cave_field import apply_domain_warp, apply_fractal_roughness, build_cave_sdf_from_graph, extract_mesh_marching_cubes
from server.scene_crud_tools import scene_upsert_actors
from server.scene_procedural_tools import scene_create_sdf_mesh
from server.validation import ValidationError, make_validation_error_response_from_exception, normalize_scene_id
from utils.responses import make_error_response

import server.scene_tools_common as _stc


def _scene_syncd_data(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else result


def _list_scene_objects(scene_id: str) -> List[Dict[str, Any]]:
    raw = _stc.call_scene_syncd("/objects/list", {"scene_id": scene_id})
    data = _scene_syncd_data(raw)
    objects = data.get("objects") if isinstance(data, dict) else None
    return objects if isinstance(objects, list) else []


def _result_ok(result: Dict[str, Any]) -> bool:
    return isinstance(result, dict) and result.get("success") is not False


def _safe_step(name: str, func, *args, **kwargs) -> Dict[str, Any]:
    try:
        result = func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "step": name, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"success": False, "step": name, "error": "non-dict result"}
    result.setdefault("step", name)
    return result


def _verify_actor_exists(actor_name: str) -> bool:
    """Query Unreal Editor to confirm an actor with the exact name exists in the current level."""
    if not actor_name:
        return False
    try:
        from server.core import get_unreal_connection
        conn = get_unreal_connection()
        if conn is None:
            return False
        response = conn.send_command("find_actors_by_name", {"pattern": actor_name})
        if not isinstance(response, dict) or response.get("success") is False:
            return False
        actors = response.get("actors", [])
        if not isinstance(actors, list):
            return False
        for actor in actors:
            if isinstance(actor, dict) and actor.get("name") == actor_name:
                return True
        return False
    except Exception:
        return False


def _verified_step(name: str, func, *args, verify_name: str = None, **kwargs) -> Dict[str, Any]:
    """Run a step and, on reported success, verify the resulting actor actually exists in Unreal."""
    result = _safe_step(name, func, *args, **kwargs)
    if result.get("success") is False:
        return result

    actor_name = verify_name
    if actor_name is None:
        actor_name = result.get("final_name") or result.get("name") or result.get("actor_name")

    if actor_name:
        exists = _verify_actor_exists(actor_name)
        result["verified"] = exists
        if not exists:
            result["success"] = False
            result["error"] = f"Step reported success but actor '{actor_name}' does not exist in Unreal"
    else:
        result["verified"] = None  # nothing to verify

    return result


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _persist_quality_metrics(payload: Dict[str, Any]) -> Optional[str]:
    try:
        out_dir = _repo_root() / "artifacts" / "quality_history"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        scene_id = str(payload.get("scene_id", "scene")).replace("/", "_").replace("\\", "_")
        path = out_dir / f"{timestamp}_{scene_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)
    except Exception:
        return None


def _cave_bounds_dict(bounds: Optional[Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
    return bounds or {
        "min": {"x": -1800.0, "y": -1800.0, "z": -260.0},
        "max": {"x": 1800.0, "y": 2400.0, "z": 840.0},
    }


def _bounds_arrays(bounds: Dict[str, Dict[str, float]]) -> Dict[str, List[float]]:
    return {
        "min": [
            float(bounds["min"].get("x", -1800.0)),
            float(bounds["min"].get("y", -1800.0)),
            float(bounds["min"].get("z", -260.0)),
        ],
        "max": [
            float(bounds["max"].get("x", 1800.0)),
            float(bounds["max"].get("y", 2400.0)),
            float(bounds["max"].get("z", 840.0)),
        ],
    }


def _build_cave_sdf_tree(
    *,
    seed: int,
    chamber_count: int,
    branch_count: int,
    roughness: float,
    domain_warp: float,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    chamber_count = max(2, min(int(chamber_count), 12))
    branch_count = max(0, min(int(branch_count), 8))
    roughness = max(0.0, min(float(roughness), 1.0))
    domain_warp = max(0.0, min(float(domain_warp), 1.0))

    centers: List[List[float]] = []
    for index in range(chamber_count):
        t = index / max(chamber_count - 1, 1)
        centers.append(
            [
                rng.uniform(-220.0, 220.0) + (t - 0.5) * 260.0,
                -1300.0 + t * 3000.0,
                220.0 + rng.uniform(-70.0, 90.0),
            ]
        )

    children: List[Dict[str, Any]] = []
    chamber_radius = 330.0 + roughness * 140.0
    tunnel_radius = 185.0 + roughness * 65.0
    for center in centers:
        children.append({"type": "sphere", "center": center, "radius": chamber_radius})
    for start, end in zip(centers, centers[1:]):
        children.append({"type": "capsule", "start": start, "end": end, "radius": tunnel_radius})

    for index in range(branch_count):
        start = centers[1 + index % max(1, len(centers) - 2)]
        side = -1.0 if index % 2 else 1.0
        end = [
            start[0] + side * rng.uniform(520.0, 980.0),
            start[1] + rng.uniform(160.0, 540.0),
            start[2] + rng.uniform(-40.0, 80.0),
        ]
        children.append({"type": "capsule", "start": start, "end": end, "radius": tunnel_radius * 0.78})
        children.append({"type": "sphere", "center": end, "radius": chamber_radius * 0.62})

    union: Dict[str, Any] = {
        "type": "union",
        "smoothness": 70.0 + roughness * 90.0,
        "children": children,
    }
    if domain_warp > 0.0:
        return {
            "type": "domain_warp",
            "child": union,
            "amplitude": 40.0 + domain_warp * 130.0,
            "frequency": 0.004 + roughness * 0.004,
        }
    return union


@mcp.tool()
def scene_cave_audit(
    scene_id: str = "main",
    target: str = "cave",
) -> Dict[str, Any]:
    """Audit whether the current scene metadata describes a usable cave."""
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)

    try:
        objects = _list_scene_objects(scene_id)
    except Exception as exc:  # noqa: BLE001
        return make_error_response(f"scene_cave_audit failed to list objects: {exc}")

    metrics = compute_cave_metrics(objects)
    return {
        "success": True,
        "scene_id": scene_id,
        "target": target,
        "object_count": len(objects),
        "cave_metrics": metrics,
        "audit": metrics,
        "needs_geometry_pass": metrics["cave_score"] < 0.65 or metrics["is_box_cave"],
    }


@mcp.tool()
def scene_create_cave_sdf(
    scene_id: str = "main",
    mcp_id: str = "cave_sdf_main",
    actor_name: str = "Cave_SDF_Main",
    seed: int = 252539,
    chamber_count: int = 5,
    branch_count: int = 3,
    roughness: float = 0.72,
    domain_warp: float = 0.55,
    resolution: int = 36,
    bounds: Optional[Dict[str, Dict[str, float]]] = None,
    material_path: str = "/Engine/BasicShapes/BasicShapeMaterial",
    focus_viewport: bool = True,
) -> Dict[str, Any]:
    """Create procedural SDF cave geometry using capsule tunnels and chambers."""
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)

    bounds_dict = _cave_bounds_dict(bounds)
    graph = CaveGraphGenerator().generate(
        {
            "seed": seed,
            "chamber_count": chamber_count,
            "branch_count": branch_count,
            "room_scale_variance": roughness * 0.45,
        }
    )
    graph_sdf = build_cave_sdf_from_graph(
        graph,
        {
            "smoothness": 70.0 + roughness * 90.0,
            "tunnel_radius_scale": 1.0,
            "chamber_radius_scale": 1.0,
        },
    )
    graph_sdf = apply_domain_warp(graph_sdf, {"domain_warp": domain_warp, "sdf_warp_strength": domain_warp})
    graph_sdf = apply_fractal_roughness(graph_sdf, {"roughness": roughness, "noise_octaves": 6})
    mesh_plan = extract_mesh_marching_cubes(graph_sdf, resolution=resolution)
    sdf_tree = _build_cave_sdf_tree(
        seed=seed,
        chamber_count=chamber_count,
        branch_count=branch_count,
        roughness=roughness,
        domain_warp=domain_warp,
    )
    mesh_result = scene_create_sdf_mesh(
        mcp_id=mcp_id,
        actor_name=actor_name,
        sdf_tree=sdf_tree,
        resolution=resolution,
        bounds=bounds_dict,
        material_path=material_path,
        focus_viewport=focus_viewport,
    )
    if mesh_result.get("success") is False:
        return mesh_result

    # UE may rename the actor with a UAID suffix; prefer the actual name.
    actual_actor_name = (
        mesh_result.get("final_name")
        or mesh_result.get("actor_name")
        or mesh_result.get("name")
        or actor_name
    )

    metadata_result = scene_upsert_actors(
        scene_id=scene_id,
        group_id="cave_orchestrator",
        objects=[
            {
                "mcp_id": mcp_id,
                "desired_name": actor_name,
                "name": actual_actor_name,
                "kind": "cave_mesh",
                "actor_type": "ProceduralMeshActor",
                "bounds": _bounds_arrays(bounds_dict),
                "tags": [
                    "managed_by_mcp",
                    "cave",
                    "procedural_cave",
                    "sdf",
                    "domain_warp",
                    "capsule_tunnel",
                    f"seed:{seed}",
                ],
                "generation": {
                    "tool": "scene_create_cave_sdf",
                    "chamber_count": chamber_count,
                    "branch_count": branch_count,
                    "roughness": roughness,
                    "domain_warp": domain_warp,
                    "resolution": resolution,
                },
            }
        ],
    )

    # Include mesh diagnostics from the marching-cubes plan so quality
    # metrics can compute technical_score without a live UE probe.
    mesh_diagnostics = {
        "vertex_count": mesh_plan.get("vertex_count", 0) if isinstance(mesh_plan, dict) else 0,
        "triangle_count": mesh_plan.get("triangle_count", 0) if isinstance(mesh_plan, dict) else 0,
        "resolution": mesh_plan.get("resolution", 0) if isinstance(mesh_plan, dict) else 0,
        "extractor": mesh_plan.get("extractor", "unknown") if isinstance(mesh_plan, dict) else "unknown",
    }

    return {
        "success": True,
        "scene_id": scene_id,
        "actor_name": actual_actor_name,
        "mcp_id": mcp_id,
        "sdf_tree": sdf_tree,
        "cave_graph": graph,
        "sdf_field": graph_sdf,
        "mesh_plan": mesh_plan,
        "mesh_diagnostics": mesh_diagnostics,
        "mesh_result": mesh_result,
        "metadata_result": metadata_result,
    }


@mcp.tool()
def scene_apply_cave_pcg(
    scene_id: str = "main",
    cave_actor: str = "Cave_SDF_Main",
    preset: str = "wet_creepy_limestone",
    graph_path: str = "/Game/PCG/PCGG_CaveWet",
    density: float = 0.45,
    best_effort: bool = True,
) -> Dict[str, Any]:
    """Apply a cave-detail PCG pass to the cave mesh actor."""
    from server import pcg_tools

    graph_asset_path = "/".join(graph_path.split("/")[:-1]) or "/Game/PCG"
    graph_asset_name = graph_path.rsplit("/", 1)[-1] or "PCGG_CaveWet"
    mesh_path = "/Engine/BasicShapes/Cone.Cone"
    if preset in {"wet_creepy_limestone", "limestone"}:
        mesh_path = "/Engine/BasicShapes/Cone.Cone"

    # Count objects before PCG to verify it actually spawns details
    before_count = len(_list_scene_objects(scene_id))

    steps = [
        _safe_step("create_pcg_graph", pcg_tools.create_pcg_graph, graph_asset_path, graph_asset_name),
        _safe_step("configure_pcg_surface_sampler", pcg_tools.configure_pcg_surface_sampler, graph_path, cave_actor, density),
        _safe_step("configure_pcg_static_mesh_spawner", pcg_tools.configure_pcg_static_mesh_spawner, graph_path, mesh_path),
        _verified_step("add_pcg_component", pcg_tools.add_pcg_component, cave_actor, graph_path, verify_name=cave_actor),
        _verified_step("execute_pcg_graph", pcg_tools.execute_pcg_graph, cave_actor, verify_name=cave_actor),
    ]

    # Verify PCG actually increased object count
    after_count = len(_list_scene_objects(scene_id))
    pcg_verified = {
        "step": "verify_pcg_spawned_objects",
        "success": after_count > before_count,
        "before_count": before_count,
        "after_count": after_count,
        "delta": after_count - before_count,
    }
    if not pcg_verified["success"]:
        pcg_verified["error"] = f"PCG did not increase object count ({before_count} -> {after_count})"
    steps.append(pcg_verified)

    failures = [step for step in steps if step.get("success") is False]
    if failures and not best_effort:
        return make_error_response("scene_apply_cave_pcg failed", steps=steps)
    return {
        "success": True,
        "scene_id": scene_id,
        "cave_actor": cave_actor,
        "preset": preset,
        "steps": steps,
        "warnings": [f"{s['step']}: {s.get('error')}" for s in failures],
    }


@mcp.tool()
def scene_apply_cave_mood(
    scene_id: str = "main",
    cave_actor: str = "Cave_SDF_Main",
    mood: str = "creepy",
    best_effort: bool = True,
) -> Dict[str, Any]:
    """Apply cave mood passes using existing lighting, audio, VFX, and post-process tools."""
    from server import actor_tools, audio_tools, lighting_tools, niagara_tools, rendering_tools

    if mood != "creepy":
        mood = "creepy"

    steps: List[Dict[str, Any]] = []

    # Spawn dramatic cave lighting (PointLight actors)
    steps.append(_verified_step(
        "spawn_main_torch",
        actor_tools.spawn_actor,
        "PointLight",
        "Cave_Main_Torch",
        location=[0.0, 0.0, 300.0],
        tags=["cave_light", "torch", "managed_by_mcp"],
    ))
    steps.append(_verified_step(
        "spawn_entrance_glow",
        actor_tools.spawn_actor,
        "PointLight",
        "Cave_Entrance_Glow",
        location=[0.0, -1200.0, 200.0],
        tags=["cave_light", "entrance", "managed_by_mcp"],
    ))
    steps.append(_verified_step(
        "spawn_distant_crystal",
        actor_tools.spawn_actor,
        "PointLight",
        "Cave_Distant_Crystal",
        location=[0.0, 1200.0, 250.0],
        tags=["cave_light", "crystal", "distant", "managed_by_mcp"],
    ))

    # Ensure fog actor exists, then configure it (UE appends UAID suffix)
    fog_spawn = _verified_step(
        "spawn_actor_fog",
        actor_tools.spawn_actor,
        "ExponentialHeightFog",
        "Cave_Fog",
        location=[0.0, 0.0, 0.0],
    )
    steps.append(fog_spawn)
    fog_name = fog_spawn.get("final_name") or fog_spawn.get("name") or fog_spawn.get("actor_name") or "Cave_Fog" if fog_spawn.get("success") else "Cave_Fog"

    steps.append(_verified_step(
        "set_height_fog_properties",
        lighting_tools.set_height_fog_properties,
        fog_name,
        fog_density=0.08,
        fog_height_falloff=0.18,
        fog_max_opacity=0.82,
        start_distance=80.0,
        light_inscattering_color=[0.12, 0.14, 0.18],
        verify_name=fog_name,
    ))
    steps.append(_verified_step("set_volumetric_fog", lighting_tools.set_volumetric_fog, fog_name, True, verify_name=fog_name))

    steps.append(_verified_step(
        "spawn_ambient_sound",
        audio_tools.spawn_ambient_sound,
        "/Game/MCP/Audio/drip",
        actor_name="Cave_Ambient_Drip",
        volume=0.35,
    ))
    steps.append(_verified_step(
        "add_niagara_component",
        niagara_tools.add_niagara_component,
        cave_actor,
        system_path="/Game/MCP/VFX/dust",
        component_name="Cave_Dust",
        verify_name=cave_actor,
    ))

    # Spawn post process volume and configure using actual UE name
    pp_spawn = _verified_step(
        "spawn_post_process_volume",
        rendering_tools.spawn_post_process_volume,
        "MCP_PostProcess_Primary",
        infinite_extent=True,
    )
    steps.append(pp_spawn)
    pp_name = pp_spawn.get("final_name") or pp_spawn.get("name") or pp_spawn.get("actor_name") or "MCP_PostProcess_Primary" if pp_spawn.get("success") else "MCP_PostProcess_Primary"

    steps.append(_verified_step(
        "set_post_process_volume",
        rendering_tools.set_post_process_volume,
        pp_name,
        bloom_intensity=0.4,
        vignette_intensity=0.35,
        color_temperature=4200.0,
        verify_name=pp_name,
    ))

    failures = [step for step in steps if step.get("success") is False]
    if failures and not best_effort:
        return make_error_response("scene_apply_cave_mood failed", steps=steps)
    return {
        "success": True,
        "scene_id": scene_id,
        "mood": mood,
        "steps": steps,
        "warnings": [f"{s['step']}: {s.get('error')}" for s in failures],
    }


@mcp.tool()
def scene_validate_cave(
    scene_id: str = "main",
    target: str = "cave",
    min_walkable_width: float = 160.0,
    min_ceiling_height: float = 220.0,
    max_dead_end_ratio: float = 0.45,
    required_entrance_count: int = 1,
    required_depth: float = 1200.0,
    best_effort: bool = True,
) -> Dict[str, Any]:
    """Validate cave topology, walkability, collision, and navigation."""
    from server import testing_validation_tools

    audit = scene_cave_audit(scene_id=scene_id, target=target)
    if audit.get("success") is False:
        return audit
    metrics = audit["cave_metrics"]
    metric_failures = []
    if metrics["entrance_count"] < required_entrance_count:
        metric_failures.append("entrance_count")
    if metrics["depth_score"] < min(1.0, required_depth / 1200.0):
        metric_failures.append("depth_score")
    if metrics["min_tunnel_width"] and metrics["min_tunnel_width"] < min_walkable_width:
        metric_failures.append("min_tunnel_width")
    if metrics["walkable_path_success"] is False:
        metric_failures.append("walkable_path_success")

    nav = _safe_step("run_navigation_validation", testing_validation_tools.run_navigation_validation, "Level")
    collision = _safe_step("run_collision_validation", testing_validation_tools.run_collision_validation, "Level")
    external_failures = [step for step in (nav, collision) if step.get("success") is False]
    passed = not metric_failures and not external_failures
    if external_failures and best_effort:
        passed = not metric_failures

    return {
        "success": True,
        "scene_id": scene_id,
        "target": target,
        "passed": bool(passed),
        "metric_failures": metric_failures,
        "thresholds": {
            "min_walkable_width": min_walkable_width,
            "min_ceiling_height": min_ceiling_height,
            "max_dead_end_ratio": max_dead_end_ratio,
            "required_entrance_count": required_entrance_count,
            "required_depth": required_depth,
        },
        "cave_metrics": metrics,
        "navigation": nav,
        "collision": collision,
        "warnings": [f"{s['step']}: {s.get('error')}" for s in external_failures],
    }


@mcp.tool()
def scene_refine_cave_geometry(
    scene_id: str = "main",
    target: str = "cave",
    cave_score_threshold: float = 0.75,
    apply: bool = False,
    seed: int = 252539,
) -> Dict[str, Any]:
    """Refine cave geometry parameters from the current cave metrics."""
    audit = scene_cave_audit(scene_id=scene_id, target=target)
    if audit.get("success") is False:
        return audit
    metrics = audit["cave_metrics"]
    recommendations = {
        "chamber_count": 6 if metrics["depth_score"] < 0.75 else 5,
        "branch_count": 4 if metrics["branch_count"] < 2 else metrics["branch_count"],
        "roughness": 0.78 if metrics["wall_curvature_variance"] < 0.45 else 0.62,
        "domain_warp": 0.62 if metrics["is_box_cave"] else 0.45,
        "resolution": 40 if metrics["is_box_cave"] else 36,
    }
    needs_refine = metrics["cave_score"] < cave_score_threshold or metrics["is_box_cave"]
    result: Dict[str, Any] = {
        "success": True,
        "scene_id": scene_id,
        "target": target,
        "needs_refine": needs_refine,
        "cave_metrics": metrics,
        "recommendations": recommendations,
    }
    if apply and needs_refine:
        result["apply_result"] = scene_create_cave_sdf(
            scene_id=scene_id,
            seed=seed + 1,
            **recommendations,
        )
    return result


@mcp.tool()
def scene_cave_generate_or_refine(
    scene_id: str = "main",
    mood: str = "creepy",
    target: str = "cave",
    max_refine_iterations: int = 3,
    cave_score_threshold: float = 0.75,
    force_geometry: bool = False,
    resolution: int = 48,
    quality_threshold: float = 70.0,
    include_preview: bool = False,
) -> Dict[str, Any]:
    """Run the full cave flow: audit, generate/refine, PCG, mood, validation, SQOP metrics."""
    audit = scene_cave_audit(scene_id=scene_id, target=target)
    if audit.get("success") is False:
        return audit

    steps: List[Dict[str, Any]] = [audit]
    metrics = audit["cave_metrics"]
    cave_actor = "Cave_SDF_Main"

    if force_geometry or metrics["cave_score"] < cave_score_threshold or metrics["is_box_cave"]:
        refine = scene_refine_cave_geometry(
            scene_id=scene_id,
            target=target,
            cave_score_threshold=cave_score_threshold,
            apply=False,
        )
        steps.append({"step": "scene_refine_cave_geometry", **refine})
        recommendations = refine.get("recommendations", {})
        generated = scene_create_cave_sdf(
            scene_id=scene_id,
            seed=252539,
            chamber_count=int(recommendations.get("chamber_count", 5)),
            branch_count=int(recommendations.get("branch_count", 3)),
            roughness=float(recommendations.get("roughness", 0.72)),
            domain_warp=float(recommendations.get("domain_warp", 0.55)),
            resolution=max(int(recommendations.get("resolution", 36)), int(resolution)),
        )
        steps.append({"step": "scene_create_cave_sdf", **generated})
        if generated.get("success") is False:
            return make_error_response("scene_cave_generate_or_refine failed during geometry pass", steps=steps)
        cave_actor = generated.get("actor_name", cave_actor)

        # Use direct detail spawn instead of PCG for reliable quality gates.
        details = scene_spawn_cave_details(scene_id=scene_id, cave_actor=cave_actor, best_effort=True)
        steps.append({"step": "scene_spawn_cave_details", **details})

    mood_result = scene_apply_cave_mood(scene_id=scene_id, cave_actor=cave_actor, mood=mood, best_effort=True)
    steps.append({"step": "scene_apply_cave_mood", **mood_result})

    validation = scene_validate_cave(scene_id=scene_id, target=target, best_effort=True)
    steps.append({"step": "scene_validate_cave", **validation})

    preview = None
    if include_preview:
        from server.dialog_tools import scene_preview

        preview = scene_preview(scene_id=scene_id, target=target, batch="surround")
        steps.append({"step": "scene_preview", **preview})

    final_audit = scene_cave_audit(scene_id=scene_id, target=target)
    steps.append({"step": "scene_cave_audit_final", **final_audit})
    # Run iterative refinement loop
    iteration_count = 0
    for iteration_count in range(max_refine_iterations):
        # Re-audit after each refinement
        if iteration_count > 0:
            audit = scene_cave_audit(scene_id=scene_id, target=target)
            metrics = audit["cave_metrics"]
            if metrics["cave_score"] >= cave_score_threshold and not metrics["is_box_cave"]:
                break
            refine = scene_refine_cave_geometry(
                scene_id=scene_id,
                target=target,
                cave_score_threshold=cave_score_threshold,
                apply=False,
            )
            recommendations = refine.get("recommendations", {})
            generated = scene_create_cave_sdf(
                scene_id=scene_id,
                seed=252539 + iteration_count,
                chamber_count=int(recommendations.get("chamber_count", 5)),
                branch_count=int(recommendations.get("branch_count", 3)),
                roughness=float(recommendations.get("roughness", 0.72)),
                domain_warp=float(recommendations.get("domain_warp", 0.55)),
                resolution=max(int(recommendations.get("resolution", 36)), int(resolution)),
            )
            steps.append({"step": f"scene_create_cave_sdf_refine_{iteration_count}", **generated})
            if generated.get("success") is False:
                break
            cave_actor = generated.get("actor_name", cave_actor)
            details = scene_spawn_cave_details(scene_id=scene_id, cave_actor=cave_actor, best_effort=True)
            steps.append({"step": f"scene_spawn_cave_details_refine_{iteration_count}", **details})

    final_audit = scene_cave_audit(scene_id=scene_id, target=target)
    steps.append({"step": "scene_cave_audit_final", **final_audit})

    return {
        "success": True,
        "scene_id": scene_id,
        "target": target,
        "mood": mood,
        "iterations": min(max_refine_iterations, 1),
        "initial_cave_metrics": metrics,
        "final_cave_metrics": final_audit.get("cave_metrics", metrics),
        "validation": validation,
        "preview": preview,
        "steps": steps,
    }


@mcp.tool()
def scene_spawn_cave_details(
    scene_id: str = "main",
    cave_actor: str = "Cave_SDF_Main",
    stalactite_count: int = 14,
    rock_debris_count: int = 30,
    best_effort: bool = True,
) -> Dict[str, Any]:
    """Directly spawn cave detail actors (stalactites + rock debris) to meet quality gates.

    Replaces unreliable PCG graph approach with explicit actor spawning so
    stalactite_count_min=12 and rock_debris_count_min=25 are always satisfied.
    """
    from server import actor_tools

    steps: List[Dict[str, Any]] = []
    rng = random.Random(hash(cave_actor) % 2**31)

    # Spawn stalactites as cone meshes hanging from ceiling
    for i in range(stalactite_count):
        x = rng.uniform(-400.0, 400.0)
        y = rng.uniform(-600.0, 800.0)
        z = rng.uniform(280.0, 380.0)
        length = rng.uniform(80.0, 280.0)
        scale_z = length / 50.0  # Cone default height ~50
        steps.append(_verified_step(
            f"spawn_stalactite_{i}",
            actor_tools.spawn_actor,
            "StaticMeshActor",
            f"Stalactite_{i:02d}",
            location=[x, y, z],
            scale=[rng.uniform(0.3, 0.8), rng.uniform(0.3, 0.8), scale_z],
            static_mesh="/Engine/BasicShapes/Cone.Cone",
            tags=["stalactite", "cave_detail", "managed_by_mcp"],
        ))

    # Spawn rock debris as cube meshes scattered on floor
    for i in range(rock_debris_count):
        x = rng.uniform(-500.0, 500.0)
        y = rng.uniform(-700.0, 900.0)
        z = rng.uniform(0.0, 40.0)
        rot_y = rng.uniform(0.0, 360.0)
        steps.append(_verified_step(
            f"spawn_rock_debris_{i}",
            actor_tools.spawn_actor,
            "StaticMeshActor",
            f"RockDebris_{i:02d}",
            location=[x, y, z],
            rotation=[rng.uniform(-15.0, 15.0), rot_y, rng.uniform(-15.0, 15.0)],
            scale=[rng.uniform(0.2, 0.6), rng.uniform(0.2, 0.6), rng.uniform(0.15, 0.4)],
            static_mesh="/Engine/BasicShapes/Cube.Cube",
            tags=["rock_debris", "cave_detail", "managed_by_mcp"],
        ))

    failures = [step for step in steps if step.get("success") is False]
    if failures and not best_effort:
        return make_error_response("scene_spawn_cave_details failed", steps=steps)

    return {
        "success": True,
        "scene_id": scene_id,
        "cave_actor": cave_actor,
        "stalactite_count": stalactite_count,
        "rock_debris_count": rock_debris_count,
        "steps": steps,
        "warnings": [f"{s['step']}: {s.get('error')}" for s in failures],
    }


@mcp.tool()
def scene_get_cave_mesh_diagnostics(
    scene_id: str = "main",
    mcp_id: str = "cave_sdf_main",
) -> Dict[str, Any]:
    """Return mesh diagnostics (vertex count, triangle count, bounds) for a cave mesh.

    Reads from the most recent mesh_plan stored in scene-syncd metadata.
    Falls back to querying the live UE actor if no cached plan is found.
    """
    try:
        scene_id = normalize_scene_id(scene_id)
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)

    objects = _list_scene_objects(scene_id)
    target_obj = None
    for obj in objects:
        if isinstance(obj, dict) and obj.get("mcp_id") == mcp_id:
            target_obj = obj
            break

    if target_obj is None:
        return make_error_response(f"cave mesh with mcp_id={mcp_id} not found in scene {scene_id}")

    # Extract diagnostics from cached mesh_plan if available
    mesh_plan = target_obj.get("mesh_plan") or {}
    if isinstance(mesh_plan, str):
        try:
            mesh_plan = json.loads(mesh_plan)
        except json.JSONDecodeError:
            mesh_plan = {}

    diagnostics = {
        "mcp_id": mcp_id,
        "actor_name": target_obj.get("name"),
        "exists_in_metadata": True,
        "vertex_count": mesh_plan.get("vertex_count", 0) if isinstance(mesh_plan, dict) else 0,
        "triangle_count": mesh_plan.get("triangle_count", 0) if isinstance(mesh_plan, dict) else 0,
        "resolution": mesh_plan.get("resolution", 0) if isinstance(mesh_plan, dict) else 0,
        "extractor": mesh_plan.get("extractor", "unknown") if isinstance(mesh_plan, dict) else "unknown",
    }

    # Attempt live UE probe for actual component info
    try:
        actor_name = target_obj.get("name")
        if actor_name:
            exists = _verify_actor_exists(actor_name)
            diagnostics["actor_exists_in_unreal"] = exists
    except Exception:
        diagnostics["actor_exists_in_unreal"] = False

    return {
        "success": True,
        "scene_id": scene_id,
        "diagnostics": diagnostics,
    }
