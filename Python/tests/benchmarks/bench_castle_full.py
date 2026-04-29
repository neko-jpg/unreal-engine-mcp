"""Full medieval castle generation benchmark.

Measures every phase of the castle generation pipeline:
    1. DB bulk-upsert (20 objects)
    2. /sync/plan (diff desired vs actual)
    3. /sync/apply (spawn all actors in Unreal)
    4. get_actors_in_level verification
    5. P7 commands (NavMesh + Patrol + AI)
    6. Cleanup (DB deletes + apply with allow_delete)

Run:
    pytest tests/benchmarks/bench_castle_full.py -v           # Single run
    pytest tests/benchmarks/bench_castle_full.py -v --count 3  # 3 runs (median)
"""

import json
import statistics
import time

import pytest

from .conftest import (
    MetricsCollector,
    BenchmarkReport,
    build_comparison_markdown,
    load_latest_report,
    load_previous_report,
    api_post,
    api_post_simple,
    unreal_command,
    unreal_command_timed,
    assert_success,
    close_unreal_connection,
)


# --- Castle object builder (mirrors e2e test for independence) ---

def _build_castle_objects(scene_id: str, suffix: str) -> list[dict]:
    objs = []

    # Ground
    objs.append({
        "scene_id": scene_id, "mcp_id": f"castle_ground_{suffix}",
        "desired_name": f"CastleGround_{suffix}", "actor_type": "StaticMeshActor",
        "asset_ref": {"path": "/Engine/BasicShapes/Plane.Plane"},
        "transform": {"location": {"x": 0, "y": 0, "z": -50}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 100, "y": 100, "z": 1}},
        "tags": ["castle", "ground"],
    })

    # Walls
    wall_configs = [
        ("north", 0, -4500, 50, 10),
        ("south_east", 3000, 4500, 20, 10),
        ("south_west", -3000, 4500, 20, 10),
        ("east", 4500, 0, 10, 50),
        ("west", -4500, 0, 10, 50),
    ]
    for name, tx, ty, sx, sy in wall_configs:
        objs.append({
            "scene_id": scene_id, "mcp_id": f"castle_wall_{name}_{suffix}",
            "desired_name": f"CastleWall{name.replace('_', '').title()}_{suffix}",
            "actor_type": "StaticMeshActor", "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {"location": {"x": tx, "y": ty, "z": 400}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": sx, "y": sy, "z": 4}},
            "tags": ["castle", "wall"],
        })

    # Towers
    for tname, tx, ty in [("nw", -4500, -4500), ("ne", 4500, -4500), ("sw", -4500, 4500), ("se", 4500, 4500)]:
        objs.append({
            "scene_id": scene_id, "mcp_id": f"castle_tower_{tname}_{suffix}",
            "desired_name": f"CastleTower{tname.upper()}_{suffix}",
            "actor_type": "StaticMeshActor", "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {"location": {"x": tx, "y": ty, "z": 800}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 3, "y": 3, "z": 16}},
            "tags": ["castle", "tower"],
        })

    # Gate pillars
    for pname, px in [("e", 800), ("w", -800)]:
        objs.append({
            "scene_id": scene_id, "mcp_id": f"castle_gate_pillar_{pname}_{suffix}",
            "desired_name": f"CastleGatePillar{pname.upper()}_{suffix}",
            "actor_type": "StaticMeshActor", "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {"location": {"x": px, "y": 4500, "z": 400}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1.5, "y": 1.5, "z": 8}},
            "tags": ["castle", "gate"],
        })

    # Bridge
    objs.append({
        "scene_id": scene_id, "mcp_id": f"castle_bridge_{suffix}",
        "desired_name": f"CastleBridge_{suffix}", "actor_type": "StaticMeshActor",
        "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
        "transform": {"location": {"x": 0, "y": 5500, "z": 10}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 4, "y": 10, "z": 0.2}},
        "tags": ["castle", "bridge"],
    })

    # Keep
    objs.append({
        "scene_id": scene_id, "mcp_id": f"castle_keep_{suffix}",
        "desired_name": f"CastleKeep_{suffix}", "actor_type": "StaticMeshActor",
        "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
        "transform": {"location": {"x": 0, "y": 0, "z": 1000}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 8, "y": 8, "z": 20}},
        "tags": ["castle", "keep"],
    })

    # Barracks
    for i, bx in [("1", -2500), ("2", 2500)]:
        objs.append({
            "scene_id": scene_id, "mcp_id": f"castle_barracks_{i}_{suffix}",
            "desired_name": f"CastleBarracks{i}_{suffix}", "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {"location": {"x": bx, "y": -2500, "z": 300}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 6, "y": 4, "z": 6}},
            "tags": ["castle", "barracks"],
        })

    return objs


# --- Helpers ---

def _missing_castle_mcp_ids(objects: list[dict]) -> list[str]:
    level_result = unreal_command("get_actors_in_level", {})
    actors = level_result.get("result", {}).get("actors", [])
    actual_mcp_ids = {
        tag.removeprefix("mcp_id:")
        for actor in actors
        for tag in actor.get("tags", [])
        if tag.startswith("mcp_id:")
    }
    return [obj["mcp_id"] for obj in objects if obj["mcp_id"] not in actual_mcp_ids]


def _delete_all_managed_actors() -> None:
    """Delete all actors tagged with managed_by_mcp from Unreal (setup/teardown, not measured)."""
    try:
        level_result = unreal_command("get_actors_in_level", {})
        actors = level_result.get("result", {}).get("actors", [])
        for actor in actors:
            tags = actor.get("tags", [])
            if "managed_by_mcp" not in tags:
                continue
            mcp_id = None
            for tag in tags:
                if tag.startswith("mcp_id:"):
                    mcp_id = tag.removeprefix("mcp_id:")
                    break
            if mcp_id:
                try:
                    unreal_command("delete_actor_by_mcp_id", {"mcp_id": mcp_id})
                except Exception:
                    pass
    except Exception:
        pass


# --- Test class ---

@pytest.mark.requires_unreal
class TestCastleBenchmark:
    """Benchmark that must run with all three services online."""

    def test_full_castle_generation(
        self, all_services_available, metrics: MetricsCollector, benchmark_dir
    ):
        """Measure full castle generation end-to-end."""
        available, issues = all_services_available
        if not available:
            pytest.skip(f"Services unavailable: {'; '.join(issues)}")

        # --- Pre-benchmark: clean up any existing managed actors (not measured) ---
        _delete_all_managed_actors()
        time.sleep(0.5)

        suffix = time.strftime("%Y%m%d%H%M%S")
        scene_id = f"bench_castle_{suffix}"

        # --- Setup: create scene ---
        api_post_simple("/scenes/create", {
            "scene_id": scene_id,
            "name": f"Benchmark Castle {suffix}",
            "description": "Castle generation benchmark",
        })

        objects = _build_castle_objects(scene_id, suffix)
        expected_ids = [o["mcp_id"] for o in objects]

        try:
            # --- Phase 1: DB bulk-upsert ---
            metrics.start_phase("db_bulk_upsert")
            res = api_post(metrics, "/objects/bulk-upsert", {"scene_id": scene_id, "objects": objects})
            metrics.record_actors(len(objects), len(objects))
            metrics.end_phase("db_bulk_upsert")
            assert_success(res, "bulk upsert castle objects")

            # --- Phase 2: Sync plan ---
            metrics.start_phase("sync_plan")
            plan_res = api_post(metrics, "/sync/plan", {"scene_id": scene_id})
            plan_data = assert_success(plan_res, "plan castle")
            creates = [op for op in plan_data.get("operations", []) if op.get("action") == "create"]
            assert len(creates) >= len(objects), f"Expected >= {len(objects)} CREATEs, got {len(creates)}"
            metrics.set_extra("plan_create_count", len(creates))
            metrics.end_phase("sync_plan")

            # --- Phase 3: Apply to Unreal ---
            metrics.start_phase("sync_apply")
            apply_res = api_post(metrics, "/sync/apply", {
                "scene_id": scene_id, "mode": "apply_safe",
                "allow_delete": False, "max_operations": 200,
            })
            apply_data = assert_success(apply_res, "apply castle")
            summary = apply_data.get("summary", {})
            actual_creates = summary.get("creates", 0)
            metrics.record_actors(actual_creates, len(objects))
            metrics.set_extra("apply_result_summary", summary)
            metrics.end_phase("sync_apply")
            assert actual_creates >= len(objects), \
                f"Expected >= {len(objects)} creates, got {json.dumps(summary, indent=2)}"

            # --- Phase 4: Verify via get_actors_in_level ---
            metrics.start_phase("get_actors_verify")
            missing = _missing_castle_mcp_ids(objects)
            if missing:
                # Re-apply + retry up to 5 times
                api_post(metrics, "/sync/apply", {
                    "scene_id": scene_id, "mode": "apply_safe",
                    "allow_delete": False, "max_operations": 200,
                })
                for _ in range(5):
                    missing = _missing_castle_mcp_ids(objects)
                    if not missing:
                        break
                    time.sleep(0.5)
            metrics.record_actors(len(objects) - len(missing), len(objects))
            metrics.set_extra("missing_actors_after_retry", missing)
            metrics.end_phase("get_actors_verify")
            assert not missing, f"Castle actors missing in Unreal: {missing}"

            # --- Phase 5: P7 commands ---
            metrics.start_phase("p7_commands")

            # NavMesh
            nav = unreal_command_timed(metrics, "create_nav_mesh_volume", {
                "volume_name": f"BenchNavMesh_{suffix}",
                "location": [0, 0, 0], "extent": [4500, 4500, 500],
            })
            nav_inner = nav.get("result", {})
            assert nav_inner.get("success") is not False, f"NavMesh failed: {nav}"

            # Patrol
            patrol = unreal_command_timed(metrics, "create_patrol_route", {
                "patrol_route_name": f"BenchWallPatrol_{suffix}",
                "points": [
                    {"x": -4000, "y": -4000, "z": 800}, {"x": 4000, "y": -4000, "z": 800},
                    {"x": 4000, "y": 4000, "z": 800}, {"x": -4000, "y": 4000, "z": 800},
                ],
                "closed_loop": True,
            })
            patrol_inner = patrol.get("result", {})
            assert patrol_inner.get("success") is not False, f"Patrol failed: {patrol}"

            # AI behavior
            ai = unreal_command_timed(metrics, "set_ai_behavior", {
                "actor_name": f"CastleTowerNW_{suffix}",
                "faction": "hostile",
                "behavior_tree_path": "/Game/AI/BT_CastleGuard.BT_CastleGuard",
                "perception_radius": 2000,
            })
            ai_inner = ai.get("result", {})
            assert "Actor not found" not in str(ai_inner.get("error", "")), f"AI setup failed: {ai}"

            metrics.end_phase("p7_commands")

            # --- Phase 6: Cleanup ---
            metrics.start_phase("cleanup")

            # Delete all objects from DB
            obj_list_data = api_post(metrics, "/objects/list", {"scene_id": scene_id})
            obj_list = obj_list_data.get("data", {}).get("objects", [])
            for obj in obj_list:
                api_post(None, "/objects/delete", {"scene_id": scene_id, "mcp_id": obj.get("mcp_id", "")})

            # Apply with allow_delete to remove from Unreal
            api_post(metrics, "/sync/apply", {
                "scene_id": scene_id, "mode": "apply_safe",
                "allow_delete": True, "max_operations": 200,
            })

            metrics.end_phase("cleanup")

        finally:
            # Best-effort cleanup (swallow errors)
            try:
                obj_list_data = api_post_simple("/objects/list", {"scene_id": scene_id})
                objs = obj_list_data.get("data", {}).get("objects", [])
                for obj in objs:
                    try:
                        api_post_simple("/objects/delete", {"scene_id": scene_id, "mcp_id": obj.get("mcp_id", "")})
                    except Exception:
                        pass
                api_post_simple("/sync/apply", {
                    "scene_id": scene_id, "mode": "apply_safe",
                    "allow_delete": True, "max_operations": 200,
                })
            except Exception:
                pass
            close_unreal_connection()

    def test_compare_with_baseline(self, all_services_available, metrics: MetricsCollector, benchmark_dir):
        """Run benchmark and compare with the previous saved baseline."""
        available, issues = all_services_available
        if not available:
            pytest.skip(f"Services unavailable: {'; '.join(issues)}")

        # Run the benchmark
        self.test_full_castle_generation(all_services_available, metrics, benchmark_dir)

        # Load previous baseline (the run we just performed was saved to results/)
        before = load_previous_report(exclude_run_id=metrics.run_id)
        if before is None:
            pytest.skip("No previous baseline to compare against (run at least twice)")

        after = metrics.summary()
        comp_md = build_comparison_markdown(before, after, benchmark_dir)
        print(f"\n\n{comp_md}")
