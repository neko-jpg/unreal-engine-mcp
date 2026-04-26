#!/usr/bin/env python3
"""Minimal 1-cube E2E test for Scene Sync lifecycle.

Prerequisites:
    1. SurrealDB running on ws://127.0.0.1:8000
    2. Rust scene-syncd running on http://127.0.0.1:8787
    3. (Optional) Unreal Editor with MCP Bridge for full apply tests

Usage:
    python scripts/verify_scene_sync_e2e.py [--skip-unreal]

This exercises the full desired-state sync lifecycle:
    upsert -> plan create -> [apply create] -> plan noop -> update transform ->
    [apply transform] -> tombstone -> [delete skip/execute] -> snapshot create/restore

If --skip-unreal is passed, apply steps are skipped and only DB-side logic is tested.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8787"


def api_call(method: str, path: str, payload: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {body}")
    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")


def assert_success(response: dict, context: str):
    if not response.get("success"):
        raise AssertionError(f"{context} failed: {response.get('error', response)}")
    return response.get("data", {})


def main():
    parser = argparse.ArgumentParser(description="Scene Sync E2E Test")
    parser.add_argument("--skip-unreal", action="store_true", help="Skip apply steps that require Unreal Editor")
    args = parser.parse_args()

    print("=== Scene Sync 1-Cube E2E Test ===")
    if args.skip_unreal:
        print("(Unreal apply steps SKIPPED - testing DB + planner only)\n")
    else:
        print("(Full test including Unreal apply)\n")

    # Step 1: Health check
    print("[1/11] Health check...")
    health = api_call("GET", "/health")
    assert_success(health, "health check")
    print("    OK\n")

    # Step 2: Upsert a cube
    print("[2/11] Upsert cube 'e2e_cube_01'...")
    upsert_resp = api_call("POST", "/objects/upsert", {
        "scene_id": "main",
        "mcp_id": "e2e_cube_01",
        "desired_name": "E2E Test Cube",
        "actor_type": "StaticMeshActor",
        "transform": {
            "location": {"x": 100.0, "y": 200.0, "z": 300.0},
            "rotation": {"pitch": 0.0, "yaw": 45.0, "roll": 0.0},
            "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
        },
        "tags": ["e2e_test"],
    })
    assert_success(upsert_resp, "upsert")
    print("    OK\n")

    # Step 3: Plan sync (should show CREATE since no actual actor in Unreal)
    print("[3/11] Plan sync (expect CREATE)...")
    plan_resp = api_call("POST", "/sync/plan", {"scene_id": "main"})
    plan_data = assert_success(plan_resp, "plan sync")
    ops = plan_data.get("operations", [])
    create_ops = [op for op in ops if op.get("action") == "create"]
    assert len(create_ops) >= 1, f"Expected at least 1 CREATE, got: {json.dumps(ops, indent=2)}"
    print(f"    OK - {len(create_ops)} CREATE operation(s)\n")

    if not args.skip_unreal:
        # Step 4: Apply sync (allow_delete=false)
        print("[4/11] Apply sync (allow_delete=false)...")
        apply_resp = api_call("POST", "/sync/apply", {
            "scene_id": "main",
            "mode": "apply_safe",
            "allow_delete": False,
        })
        apply_data = assert_success(apply_resp, "apply sync")
        print(f"    OK - summary: {json.dumps(apply_data.get('summary', {}), indent=2)}\n")

        # Step 5: Mark object as synced (simulating Unreal actor creation)
        print("[5/11] Mark object synced...")
        mark_resp = api_call("POST", "/objects/mark-synced", {
            "scene_id": "main",
            "mcp_id": "e2e_cube_01",
            "applied_hash": plan_data.get("operations", [{}])[0].get("desired_hash", "hash_v1"),
            "unreal_actor_name": "E2E_Test_Cube",
        })
        assert_success(mark_resp, "mark synced")
        print("    OK\n")
    else:
        # Simulate sync by marking object synced directly
        print("[4-5/11] Skip apply/mark-synced (no Unreal)...")
        print("    SKIPPED\n")

    # Step 6: Plan again (should show NOOP if synced, otherwise CREATE again)
    print("[6/11] Plan sync again (expect NOOP if synced)...")
    plan2_resp = api_call("POST", "/sync/plan", {"scene_id": "main"})
    plan2_data = assert_success(plan2_resp, "second plan")
    ops2 = plan2_data.get("operations", [])
    if args.skip_unreal:
        # Without Unreal, object is not synced, so expect CREATE again
        create_ops2 = [op for op in ops2 if op.get("action") == "create"]
        assert len(create_ops2) >= 1, f"Expected CREATE (unsynced), got: {json.dumps(ops2, indent=2)}"
        print(f"    OK - {len(create_ops2)} CREATE (not yet synced)\n")
    else:
        noop_ops = [op for op in ops2 if op.get("action") == "noop"]
        assert len(noop_ops) >= 1, f"Expected NOOP, got: {json.dumps(ops2, indent=2)}"
        print(f"    OK - {len(noop_ops)} NOOP operation(s)\n")

    # Step 7: Update transform
    print("[7/11] Update transform...")
    update_resp = api_call("POST", "/objects/upsert", {
        "scene_id": "main",
        "mcp_id": "e2e_cube_01",
        "transform": {
            "location": {"x": 500.0, "y": 600.0, "z": 700.0},
            "rotation": {"pitch": 0.0, "yaw": 90.0, "roll": 0.0},
            "scale": {"x": 3.0, "y": 3.0, "z": 3.0},
        },
    })
    assert_success(update_resp, "update transform")
    print("    OK\n")

    # Step 8: Plan again (should show UPDATE if synced, otherwise CREATE)
    print("[8/11] Plan sync again (expect UPDATE if synced)...")
    plan3_resp = api_call("POST", "/sync/plan", {"scene_id": "main"})
    plan3_data = assert_success(plan3_resp, "third plan")
    ops3 = plan3_data.get("operations", [])
    if args.skip_unreal:
        create_ops3 = [op for op in ops3 if op.get("action") == "create"]
        assert len(create_ops3) >= 1, f"Expected CREATE (unsynced), got: {json.dumps(ops3, indent=2)}"
        print(f"    OK - {len(create_ops3)} CREATE (not yet synced)\n")
    else:
        update_ops = [op for op in ops3 if op.get("action") in ("update_transform", "update_visual")]
        assert len(update_ops) >= 1, f"Expected UPDATE, got: {json.dumps(ops3, indent=2)}"
        print(f"    OK - {len(update_ops)} UPDATE operation(s)\n")

    # Step 9: Tombstone (mark deleted)
    print("[9/11] Tombstone object...")
    del_resp = api_call("POST", "/objects/delete", {
        "scene_id": "main",
        "mcp_id": "e2e_cube_01",
    })
    assert_success(del_resp, "tombstone")
    print("    OK\n")

    if not args.skip_unreal:
        # Step 10: Apply with allow_delete=false (delete should be skipped)
        print("[10/11] Apply with allow_delete=false (delete should be skipped)...")
        apply2_resp = api_call("POST", "/sync/apply", {
            "scene_id": "main",
            "mode": "apply_safe",
            "allow_delete": False,
        })
        apply2_data = assert_success(apply2_resp, "apply with no-delete")
        summary2 = apply2_data.get("summary", {})
        assert summary2.get("delete", 0) == 0, f"Expected 0 deletes, got: {summary2}"
        print(f"    OK - deletes: {summary2.get('delete', 0)}\n")

        # Step 11: Apply with allow_delete=true (delete should execute)
        print("[11/11] Apply with allow_delete=true (delete should execute)...")
        apply3_resp = api_call("POST", "/sync/apply", {
            "scene_id": "main",
            "mode": "apply_safe",
            "allow_delete": True,
        })
        apply3_data = assert_success(apply3_resp, "apply with delete")
        summary3 = apply3_data.get("summary", {})
        print(f"    OK - summary: {json.dumps(summary3, indent=2)}\n")
    else:
        print("[10-11/11] Skip delete apply tests (no Unreal)...")
        print("    SKIPPED\n")

    # Step 12: Snapshot create/restore
    print("[12/12] Snapshot create/restore...")
    snap_resp = api_call("POST", "/snapshots/create", {
        "scene_id": "main",
        "name": "e2e_test_snapshot",
        "description": "Created during E2E test",
    })
    snap_data = assert_success(snap_resp, "snapshot create")
    snap_id = snap_data.get("snapshot_id")
    assert snap_id, f"Snapshot ID missing in response: {json.dumps(snap_data, indent=2)}"
    print(f"    Snapshot created: {snap_id}")

    restore_resp = api_call("POST", "/snapshots/restore", {
        "snapshot_id": snap_id,
        "restore_mode": "replace_desired",
    })
    restore_data = assert_success(restore_resp, "snapshot restore")
    print(f"    Restore summary: {json.dumps(restore_data.get('summary', {}), indent=2)}")
    print("    OK\n")

    print("=== All E2E steps passed! ===")
    if args.skip_unreal:
        print("(Run without --skip-unreal when Unreal Editor is open for full apply tests)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"ASSERTION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
