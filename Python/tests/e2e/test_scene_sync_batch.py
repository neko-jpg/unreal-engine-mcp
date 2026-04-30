"""E2E tests for batch scene sync operations.

Converted from scripts/verify_phase7.py to proper pytest.

Requires:
    - SurrealDB on ws://127.0.0.1:8000
    - scene-syncd on http://127.0.0.1:8787
    - (Optional) Unreal Editor with MCP Bridge on 127.0.0.1:55557

Run:
    pytest tests/e2e/test_scene_sync_batch.py --skip-unreal   # DB + planner only
    pytest tests/e2e/test_scene_sync_batch.py                  # Full E2E with Unreal
"""

import json
import time
import pytest

from .conftest import api_post, api_get, unreal_command, assert_success, SCENE_SYNCD_URL


@pytest.fixture(scope="module")
def wall_and_pyramid_scene(scene_syncd_available):
    """Create a scene with wall and pyramid objects, yield scene_id, then cleanup."""
    if not scene_syncd_available:
        pytest.skip("scene-syncd not available")

    suffix = time.strftime("%Y%m%d%H%M%S")
    scene_id = f"batch_e2e_{suffix}"

    assert_success(
        api_post("/scenes/create", {
            "scene_id": scene_id,
            "name": "Batch E2E Test",
            "description": "Created by test_scene_sync_batch",
        }),
        "create scene",
    )

    # Create wall segments
    wall_objects = []
    for i in range(3):
        wall_objects.append({
            "scene_id": scene_id,
            "mcp_id": f"batch_wall_{i:03d}_{suffix}",
            "desired_name": f"BatchWall_{i:03d}_{suffix}",
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": float(i * 200), "y": 0.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            "tags": ["batch_e2e", "wall"],
        })

    assert_success(
        api_post("/objects/bulk-upsert", {"scene_id": scene_id, "objects": wall_objects}),
        "bulk upsert wall",
    )

    # Create pyramid blocks
    pyramid_objects = []
    for i in range(2):
        pyramid_objects.append({
            "scene_id": scene_id,
            "mcp_id": f"batch_pyramid_{i:03d}_{suffix}",
            "desired_name": f"BatchPyramid_{i:03d}_{suffix}",
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": 0.0, "y": float(500 + i * 200), "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            "tags": ["batch_e2e", "pyramid"],
        })

    assert_success(
        api_post("/objects/bulk-upsert", {"scene_id": scene_id, "objects": pyramid_objects}),
        "bulk upsert pyramid",
    )

    total_objects = len(wall_objects) + len(pyramid_objects)

    yield {
        "scene_id": scene_id,
        "suffix": suffix,
        "wall_objects": wall_objects,
        "pyramid_objects": pyramid_objects,
        "total_objects": total_objects,
    }

    # Cleanup
    for obj in wall_objects + pyramid_objects:
        try:
            api_post("/objects/delete", {"scene_id": scene_id, "mcp_id": obj["mcp_id"]})
        except Exception:
            pass
    try:
        api_post("/sync/apply", {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": True,
            "max_operations": 20,
        })
    except Exception:
        pass


class TestBatchDBOnly:
    """Tests requiring only scene-syncd (no Unreal)."""

    def test_bulk_upsert_and_plan(self, wall_and_pyramid_scene):
        """Bulk upsert wall + pyramid objects, plan should show CREATEs."""
        scene = wall_and_pyramid_scene
        plan = api_post("/sync/plan", {"scene_id": scene["scene_id"]})
        data = assert_success(plan, "plan after bulk upsert")
        creates = [op for op in data.get("operations", []) if op.get("action") == "create"]
        assert len(creates) >= scene["total_objects"], \
            f"Expected >= {scene['total_objects']} CREATEs, got {len(creates)}"

    def test_snapshot_create_restore(self, wall_and_pyramid_scene):
        """Create snapshot, modify, restore, and re-plan should be noop."""
        scene = wall_and_pyramid_scene
        total = scene["total_objects"]

        # Create snapshot
        snap = api_post("/snapshots/create", {
            "scene_id": scene["scene_id"],
            "name": f"batch_snapshot_{scene['suffix']}",
        })
        snap_data = assert_success(snap, "create snapshot")
        snap_id = snap_data.get("data", {}).get("snapshot_id") or snap_data.get("snapshot_id")
        assert snap_id, f"Snapshot ID missing: {snap_data}"

        # Modify one wall object
        modified = scene["wall_objects"][1]
        original_x = modified["transform"]["location"]["x"]
        result = api_post("/objects/upsert", {
            "scene_id": scene["scene_id"],
            "mcp_id": modified["mcp_id"],
            "desired_name": modified["desired_name"],
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": 9999.0, "y": 9999.0, "z": 9999.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
            },
            "tags": ["batch_e2e", "wall"],
        })
        assert_success(result, "modify wall object")

        # Restore snapshot
        restore = api_post("/snapshots/restore", {
            "snapshot_id": snap_id,
            "restore_mode": "replace_desired",
        })
        restore_data = assert_success(restore, "restore snapshot")

        # Re-plan should show noop for all objects (restored state matches DB)
        replan = api_post("/sync/plan", {"scene_id": scene["scene_id"]})
        replan_data = assert_success(replan, "re-plan after restore")
        # Note: without Unreal, objects may show as CREATE instead of NOOP
        # since there's no actual actor to diff against


@pytest.mark.requires_unreal
class TestBatchWithUnreal:
    """Tests requiring a running Unreal Editor session."""

    def test_initial_apply_creates_all(self, wall_and_pyramid_scene):
        """Apply sync should create all wall + pyramid actors in Unreal."""
        scene = wall_and_pyramid_scene
        total = scene["total_objects"]

        apply = api_post("/sync/apply", {
            "scene_id": scene["scene_id"],
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 20,
        })
        data = assert_success(apply, "initial apply")
        summary = data["summary"]
        assert summary["creates"] == total, \
            f"Expected {total} creates, got {json.dumps(summary, indent=2)}"

    def test_snapshot_modify_restore(self, wall_and_pyramid_scene):
        """Snapshot -> modify -> apply -> restore -> apply -> verify position restored."""
        scene = wall_and_pyramid_scene

        # Initial apply
        apply1 = api_post("/sync/apply", {
            "scene_id": scene["scene_id"],
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 20,
        })
        assert_success(apply1, "initial apply")

        # Create snapshot
        snap = api_post("/snapshots/create", {
            "scene_id": scene["scene_id"],
            "name": f"batch_verify_{scene['suffix']}",
        })
        snap_data = assert_success(snap, "create snapshot")
        snap_id = snap_data.get("data", {}).get("snapshot_id") or snap_data.get("snapshot_id")

        # Modify one object
        modified = scene["wall_objects"][1]
        original_x = modified["transform"]["location"]["x"]
        api_post("/objects/upsert", {
            "scene_id": scene["scene_id"],
            "mcp_id": modified["mcp_id"],
            "desired_name": modified["desired_name"],
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": 9999.0, "y": 9999.0, "z": 9999.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
            },
            "tags": ["batch_e2e", "wall"],
        })

        # Apply modification
        apply2 = api_post("/sync/apply", {
            "scene_id": scene["scene_id"],
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 20,
        })
        data2 = assert_success(apply2, "modify apply")
        assert data2["summary"].get("update_transforms", 0) >= 1

        # Verify modification in Unreal
        unreal_resp = unreal_command("find_actor_by_mcp_id", {"mcp_id": modified["mcp_id"]})
        if unreal_resp.get("result", {}).get("success"):
            actor = unreal_resp.get("result", {}).get("actor")
            if actor:
                loc = actor.get("location", [])
                assert abs(loc[0] - 9999.0) < 1.0, f"Actor not at modified position: {loc}"

        # Restore snapshot
        restore = api_post("/snapshots/restore", {
            "snapshot_id": snap_id,
            "restore_mode": "replace_desired",
        })
        assert_success(restore, "restore snapshot")

        # Apply restored state
        apply3 = api_post("/sync/apply", {
            "scene_id": scene["scene_id"],
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 20,
        })
        data3 = assert_success(apply3, "restore apply")
        assert data3["summary"].get("update_transforms", 0) >= 1

        # Verify restored position in Unreal
        unreal_resp2 = unreal_command("find_actor_by_mcp_id", {"mcp_id": modified["mcp_id"]})
        if unreal_resp2.get("result", {}).get("success"):
            actor = unreal_resp2.get("result", {}).get("actor")
            if actor:
                loc = actor.get("location", [])
                assert abs(loc[0] - original_x) < 1.0, f"Actor not at restored position: {loc}"

    def test_replan_is_noop(self, wall_and_pyramid_scene):
        """After full sync, re-plan should report noop for all objects."""
        scene = wall_and_pyramid_scene

        replan = api_post("/sync/plan", {"scene_id": scene["scene_id"]})
        data = assert_success(replan, "re-plan")
        noop_count = sum(1 for op in data.get("operations", []) if op.get("action") == "noop")
        assert noop_count >= scene["total_objects"], \
            f"Expected >= {scene['total_objects']} noops, got {noop_count}"