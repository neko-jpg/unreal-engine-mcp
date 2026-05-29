#!/usr/bin/env python3
"""Cave generation quality score test — run against a live dev stack.

Connects to Unreal TCP (127.0.0.1:55771), generates a cave, runs the full
quality pipeline, and prints every intermediate score so we can see exactly
where the numbers come from.
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
    scene_apply_cave_pcg,
    scene_cave_audit,
    scene_create_cave_sdf,
)
from server.quality.cave_math_metrics import CaveMathMetrics
from server.quality.quality_vector import QualityVectorBuilder
from server.quality.quality_gate import QualityGate


def _ensure_unreal_connection():
    conn = get_unreal_connection()
    if conn is not None:
        return conn
    # Try manual TCP probe
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
    print("CAVE QUALITY SCORE TEST")
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

    # 3. Apply PCG details
    print("\n[3] Applying PCG details ...")
    pcg_result = scene_apply_cave_pcg(
        scene_id="main",
        cave_actor="Cave_SDF_Test",
        preset="wet_creepy_limestone",
        density=0.45,
        best_effort=True,
    )
    print(f"    success={pcg_result.get('success')}")
    for w in pcg_result.get("warnings", []):
        if w:
            print(f"    WARNING: {w}")

    # 4. Apply mood (lighting, fog, audio, post-process)
    print("\n[4] Applying cave mood ...")
    mood_result = scene_apply_cave_mood(
        scene_id="main",
        cave_actor="Cave_SDF_Test",
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
    # Build synthetic observation from audit + scene results
    observation = {
        "metrics": {
            **cave_metrics,
            "main_mesh_exists": True,
            "triangle_count": 0,  # we don't have this yet
            "flat_surface_ratio": 0.58 if cave_metrics.get("is_box_cave") else 0.25,
            "curvature_entropy": cave_metrics.get("wall_curvature_variance", 0.3),
            "arch_score": cave_metrics.get("ceiling_height_variance", 0.5),
            "detail_density_per_m2": 0.5,  # placeholder
            "image_contrast": 0.5,
            "lighting_contrast_score": 0.5,
            "topology_score": cave_metrics.get("depth_score", 0.0),
        },
        "actors": {},
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

    # 7. Build quality vector
    print("\n[7] Building quality vector ...")
    vector = QualityVectorBuilder().build(math_metrics)
    for k, v in vector.items():
        if isinstance(v, float):
            print(f"    {k}: {v:.3f}")
        else:
            print(f"    {k}: {v}")

    # 8. Run quality gate
    print("\n[8] Running quality gate ...")
    gate = QualityGate().check(vector, observation)
    print(f"    passed={gate.passed}")
    print(f"    blockers={gate.blockers}")
    print(f"    warnings={gate.warnings}")
    print(f"    values={gate.values}")

    # 9. Persist detailed log
    print("\n[9] Persisting detailed log ...")
    log_payload = {
        "timestamp": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "test_version": "v1",
        "legacy_audit": audit,
        "math_metrics": math_metrics,
        "quality_vector": vector,
        "gate_result": gate.to_dict(),
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
