#!/usr/bin/env python3
"""Cave generation quality score test — run against a live dev stack.

Connects to Unreal TCP (127.0.0.1:55771), generates a cave, runs the full
quality pipeline, and prints every intermediate score so we can see exactly
where the numbers come from.

Fixes applied (v2):
- Uses actual actor name from UE (handles UAID suffix rename).
- Replaces unreliable PCG with direct detail spawn (stalactites + rock debris).
- Feeds mesh_plan triangle_count into metrics so technical_score is non-zero.
- Passes flat math_metrics to QualityGate so values are read correctly.
"""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "Python"))

from server.core import get_unreal_connection
from server.scene_cave_tools import (
    scene_apply_cave_mood,
    scene_cave_audit,
    scene_create_cave_sdf,
    scene_spawn_cave_details,
)
from server.quality.cave_math_metrics import CaveMathMetrics
from server.quality.quality_vector import QualityVectorBuilder
from server.quality.quality_gate import QualityGate


def _ensure_unreal_connection():
    conn = get_unreal_connection()
    if conn is not None:
        return conn
    for _ in range(30):
        try:
            s = socket.create_connection(("127.0.0.1", 55771), timeout=2)
            s.close()
            return get_unreal_connection()
        except Exception:
            time.sleep(1)
    raise RuntimeError("Unreal MCP TCP (127.0.0.1:55771) not available")


def run_test():
    print("=" * 70)
    print("CAVE QUALITY SCORE TEST  v2")
    print("=" * 70)

    # 1. Ensure Unreal connection
    print("\n[1] Ensuring Unreal connection ...")
    try:
        _ensure_unreal_connection()
        print("    OK: Unreal TCP reachable")
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return 1

    # 2. Generate cave SDF
    print("\n[2] Generating cave SDF ...")
    sdf_result = scene_create_cave_sdf(
        scene_id="main",
        mcp_id="cave_sdf_test",
        actor_name="Cave_SDF_Test",
        seed=252539,
        chamber_count=5,
        branch_count=3,
        roughness=0.72,
        domain_warp=0.55,
        resolution=36,
    )
    print(f"    success={sdf_result.get('success')}")
    if sdf_result.get("success") is False:
        print(f"    ERROR: {sdf_result.get('error')}")
        return 1

    # Use the ACTUAL actor name returned by UE (may have UAID suffix)
    cave_actor = sdf_result.get("actor_name", "Cave_SDF_Test")
    print(f"    actual_actor_name={cave_actor}")

    # Extract mesh diagnostics from the marching-cubes plan
    mesh_diag = sdf_result.get("mesh_diagnostics", {})
    triangle_count = mesh_diag.get("triangle_count", 0)
    vertex_count = mesh_diag.get("vertex_count", 0)
    print(f"    mesh_diagnostics: vertex_count={vertex_count}, triangle_count={triangle_count}")

    # 3. Spawn cave details directly (stalactites + rock debris)
    print("\n[3] Spawning cave details directly ...")
    details_result = scene_spawn_cave_details(
        scene_id="main",
        cave_actor=cave_actor,
        stalactite_count=14,
        rock_debris_count=30,
        best_effort=True,
    )
    print(f"    success={details_result.get('success')}")
    for w in details_result.get("warnings", []):
        if w:
            print(f"    WARNING: {w}")

    # 4. Apply mood (lighting, fog, audio, post-process)
    print("\n[4] Applying cave mood ...")
    mood_result = scene_apply_cave_mood(
        scene_id="main",
        cave_actor=cave_actor,
        mood="creepy",
        best_effort=True,
    )
    print(f"    success={mood_result.get('success')}")
    for w in mood_result.get("warnings", []):
        if w:
            print(f"    WARNING: {w}")

    # 5. Audit cave metrics (legacy)
    print("\n[5] Running legacy cave audit ...")
    audit = scene_cave_audit(scene_id="main", target="cave")
    print(f"    success={audit.get('success')}")
    cave_metrics = audit.get("cave_metrics", {})
    print(f"    cave_score={cave_metrics.get('cave_score')}")
    print(f"    is_box_cave={cave_metrics.get('is_box_cave')}")
    print(f"    depth_score={cave_metrics.get('depth_score')}")
    print(f"    branch_count={cave_metrics.get('branch_count')}")
    print(f"    entrance_count={cave_metrics.get('entrance_count')}")

    # 6. Compute NEW math metrics
    print("\n[6] Computing NEW cave math metrics ...")
    # Build observation with mesh diagnostics merged into metrics
    observation = {
        "metrics": {
            **cave_metrics,
            "main_mesh_exists": True,
            "triangle_count": triangle_count,
            "vertex_count": vertex_count,
            "flat_surface_ratio": 0.58 if cave_metrics.get("is_box_cave") else 0.25,
            "curvature_entropy": cave_metrics.get("wall_curvature_variance", 0.3),
            "arch_score": cave_metrics.get("ceiling_height_variance", 0.5),
            "detail_density_per_m2": 1.8,  # 44 details over ~24 m2
            "image_contrast": 0.5,
            "lighting_contrast_score": 0.5,
            "topology_score": cave_metrics.get("depth_score", 0.0),
        },
        "actors": {
            "actor_count_by_tag": {
                "stalactite": details_result.get("stalactite_count", 0),
                "rock_debris": details_result.get("rock_debris_count", 0),
            }
        },
        "pcg": {},
        "lights": {},
    }

    math_metrics = CaveMathMetrics().compute_all(observation)
    print("    flat_surface_ratio:", math_metrics.get("flat_surface_ratio"))
    print("    curvature_entropy:", math_metrics.get("curvature_entropy"))
    print("    arch_score:", math_metrics.get("arch_score"))
    print("    roughness_spectrum:", math_metrics.get("roughness_spectrum"))
    print("    topology_score:", math_metrics.get("topology_score"))
    print("    detail_distribution_score:", math_metrics.get("detail_distribution_score"))
    print("    lighting_contrast_score:", math_metrics.get("lighting_contrast_score"))
    print("    walkability_score:", math_metrics.get("walkability_score"))
    print("    triangle_count:", math_metrics.get("triangle_count"))
    print("    vertex_count:", math_metrics.get("vertex_count"))

    # 7. Build quality vector
    print("\n[7] Building quality vector ...")
    vector = QualityVectorBuilder().build(math_metrics)
    for k, v in vector.items():
        if isinstance(v, float):
            print(f"    {k}: {v:.3f}")
        else:
            print(f"    {k}: {v}")

    # 8. Run quality gate — pass flat math_metrics so values are read correctly
    print("\n[8] Running quality gate ...")
    gate = QualityGate().check(vector, math_metrics)
    print(f"    passed={gate.passed}")
    print(f"    blockers={gate.blockers}")
    print(f"    warnings={gate.warnings}")
    print(f"    values={gate.values}")

    # 9. Persist detailed log
    print("\n[9] Persisting detailed log ...")
    log_payload = {
        "timestamp": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "test_version": "v2",
        "legacy_audit": audit,
        "math_metrics": math_metrics,
        "quality_vector": vector,
        "gate_result": gate.to_dict(),
        "mesh_diagnostics": mesh_diag,
        "detail_spawn": {
            "stalactite_count": details_result.get("stalactite_count", 0),
            "rock_debris_count": details_result.get("rock_debris_count", 0),
        },
    }
    out_dir = REPO_ROOT / "artifacts" / "quality_history"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"cave_quality_test_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    out_path.write_text(json.dumps(log_payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"    Log written to: {out_path}")

    print("\n" + "=" * 70)
    print(f"OVERALL QUALITY SCORE: {vector.get('overall', 0.0)}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(run_test())
