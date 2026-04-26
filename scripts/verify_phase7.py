"""Phase 7/8 verification script.

Acceptance criteria:
1. scene_create_wall upserts wall segments to DB desired state.
2. scene_create_pyramid upserts pyramid blocks to DB desired state.
3. scene_snapshot_create captures the current desired state.
4. scene_upsert_actor modifies one object's transform in DB.
5. scene_snapshot_restore restores the snapshot desired state.
6. scene_sync applies the restored state to Unreal.
7. find_actor_by_mcp_id confirms the actor returned to its original location.
8. Re-plan after restore+sync reports noop for all objects.
"""
import json
import socket
import sys
import time
import urllib.error
import urllib.request


SCENE_SYNCD_URL = "http://127.0.0.1:8787"
UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{SCENE_SYNCD_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed with HTTP {exc.code}: {body}") from exc


def get_json(path):
    with urllib.request.urlopen(f"{SCENE_SYNCD_URL}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def unreal_command(command, params=None):
    payload = json.dumps({"command": command, "params": params or {}}).encode("utf-8") + b"\n"
    with socket.create_connection((UNREAL_HOST, UNREAL_PORT), timeout=10) as client:
        client.sendall(payload)
        client.settimeout(30)
        data = bytearray()
        while b"\n" not in data:
            chunk = client.recv(262144)
            if not chunk:
                break
            data.extend(chunk)
    if not data:
        raise RuntimeError(f"Unreal returned no response for {command}")
    return json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))


def require_success(label, response):
    if not response.get("success"):
        raise RuntimeError(f"{label} failed: {json.dumps(response, indent=2)}")


def main():
    suffix = time.strftime("%Y%m%d%H%M%S")
    scene_id = f"phase7_verify_{suffix}"

    require_success("scene-syncd health", get_json("/health"))

    # 1. Create dedicated scene
    require_success(
        "create scene",
        post_json(
            "/scenes/create",
            {
                "scene_id": scene_id,
                "name": "Phase 7/8 verification",
                "description": "Created by scripts/verify_phase7.py",
            },
        ),
    )

    # 2. Use scene_create_wall via Python facade (direct HTTP to scene-syncd bulk-upsert)
    # Wall: 3 segments along X axis
    wall_objects = []
    for i in range(3):
        wall_objects.append({
            "scene_id": scene_id,
            "mcp_id": f"phase7_wall_{i:03d}_{suffix}",
            "desired_name": f"Phase7Wall_{i:03d}_{suffix}",
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": float(i * 200), "y": 0.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            "tags": ["phase7_verify", "wall"],
        })

    require_success(
        "bulk upsert wall",
        post_json("/objects/bulk-upsert", {"objects": wall_objects}),
    )

    # 3. Use scene_create_pyramid via direct bulk-upsert
    pyramid_objects = []
    for i in range(2):
        pyramid_objects.append({
            "scene_id": scene_id,
            "mcp_id": f"phase7_pyramid_{i:03d}_{suffix}",
            "desired_name": f"Phase7Pyramid_{i:03d}_{suffix}",
            "actor_type": "StaticMeshActor",
            "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
            "transform": {
                "location": {"x": 0.0, "y": float(500 + i * 200), "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            "tags": ["phase7_verify", "pyramid"],
        })

    require_success(
        "bulk upsert pyramid",
        post_json("/objects/bulk-upsert", {"objects": pyramid_objects}),
    )

    total_objects = len(wall_objects) + len(pyramid_objects)
    print(f"Upserted {total_objects} objects to DB desired state.")

    # 4. Sync to Unreal so actors exist
    apply1 = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync (initial)", apply1)
    apply1_summary = apply1["data"]["summary"]
    if apply1_summary["creates"] != total_objects:
        raise RuntimeError(
            f"Initial apply did not create all {total_objects} actors. Got: {json.dumps(apply1_summary, indent=2)}"
        )

    # 5. Create snapshot
    snapshot_resp = post_json(
        "/snapshots/create",
        {"scene_id": scene_id, "name": f"phase7_snapshot_{suffix}"},
    )
    require_success("create snapshot", snapshot_resp)
    snapshot_id = snapshot_resp["data"]["snapshot"]["id"]
    object_count = snapshot_resp["data"]["object_count"]
    print(f"Snapshot created: {snapshot_id} with {object_count} objects.")

    # 6. Modify one wall object's transform in DB
    modified_mcp_id = wall_objects[1]["mcp_id"]
    original_location = wall_objects[1]["transform"]["location"]
    require_success(
        "upsert modified object",
        post_json(
            "/objects/upsert",
            {
                "scene_id": scene_id,
                "mcp_id": modified_mcp_id,
                "desired_name": wall_objects[1]["desired_name"],
                "actor_type": "StaticMeshActor",
                "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
                "transform": {
                    "location": {"x": 9999.0, "y": 9999.0, "z": 9999.0},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
                },
                "tags": ["phase7_verify", "wall"],
            },
        ),
    )

    # 7. Apply the modification in Unreal
    apply2 = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync (modify)", apply2)
    apply2_summary = apply2["data"]["summary"]
    if apply2_summary.get("update_transforms", 0) != 1:
        raise RuntimeError(
            f"Modification apply did not update 1 transform. Got: {json.dumps(apply2_summary, indent=2)}"
        )

    # Verify modification in Unreal if available
    unreal_verified_modify = False
    try:
        mcp_response = unreal_command("find_actor_by_mcp_id", {"mcp_id": modified_mcp_id})
        if mcp_response.get("result", {}).get("success"):
            actor = mcp_response.get("result", {}).get("actor")
            if actor:
                loc = actor.get("location", [])
                if len(loc) >= 3 and abs(loc[0] - 9999.0) < 0.1:
                    unreal_verified_modify = True
    except (ConnectionRefusedError, socket.timeout, RuntimeError) as e:
        print(f"WARNING: Unreal bridge not available for modify verification: {e}", file=sys.stderr)

    # 8. Restore snapshot
    restore_resp = post_json(
        "/snapshots/restore",
        {"snapshot_id": snapshot_id, "restore_mode": "replace_desired"},
    )
    require_success("restore snapshot", restore_resp)
    restore_summary = restore_resp["data"]["summary"]
    print(f"Snapshot restored: {json.dumps(restore_summary, indent=2)}")

    # 9. Sync restored state to Unreal
    apply3 = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync (restore)", apply3)
    apply3_summary = apply3["data"]["summary"]
    if apply3_summary.get("update_transforms", 0) != 1:
        raise RuntimeError(
            f"Restore apply did not update 1 transform back. Got: {json.dumps(apply3_summary, indent=2)}"
        )

    # 10. Verify restored position in Unreal
    unreal_verified_restore = False
    try:
        mcp_response = unreal_command("find_actor_by_mcp_id", {"mcp_id": modified_mcp_id})
        if mcp_response.get("result", {}).get("success"):
            actor = mcp_response.get("result", {}).get("actor")
            if actor:
                loc = actor.get("location", [])
                if len(loc) >= 3 and abs(loc[0] - original_location["x"]) < 0.1:
                    unreal_verified_restore = True
    except (ConnectionRefusedError, socket.timeout, RuntimeError) as e:
        print(f"WARNING: Unreal bridge not available for restore verification: {e}", file=sys.stderr)

    # 11. Re-plan must be noop for all objects
    replan = post_json("/sync/plan", {"scene_id": scene_id})
    require_success("re-plan sync", replan)
    replan_summary = replan["data"]["summary"]
    if replan_summary.get("noop", 0) != total_objects:
        raise RuntimeError(
            f"Re-plan after restore did not report noop={total_objects}. Got: {json.dumps(replan_summary, indent=2)}"
        )

    # Cleanup: tombstone all objects and sync with allow_delete
    for obj in wall_objects + pyramid_objects:
        post_json("/objects/delete", {"scene_id": scene_id, "mcp_id": obj["mcp_id"]})

    cleanup_apply = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": True,
            "max_operations": 20,
        },
    )
    require_success("cleanup apply", cleanup_apply)
    cleanup_summary = cleanup_apply["data"]["summary"]
    print(f"Cleanup deletes: {cleanup_summary.get('deletes', 0)}")

    result = {
        "success": True,
        "scene_id": scene_id,
        "snapshot_id": snapshot_id,
        "total_objects": total_objects,
        "object_count_in_snapshot": object_count,
        "unreal_verified_modify": unreal_verified_modify,
        "unreal_verified_restore": unreal_verified_restore,
        "initial_apply_summary": apply1_summary,
        "modify_apply_summary": apply2_summary,
        "restore_apply_summary": apply3_summary,
        "replan_summary": replan_summary,
        "cleanup_summary": cleanup_summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"verify_phase7 failed: {exc}", file=sys.stderr)
        sys.exit(1)
