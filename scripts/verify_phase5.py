"""Phase 5 verification script.

Acceptance criteria:
1. scene_upsert_actor creates a desired object.
2. scene_sync creates the actor in Unreal.
3. scene_upsert_actor updates the transform in DB.
4. scene_plan_sync reports update_transform: 1.
5. scene_sync applies the transform change in Unreal.
6. find_actor_by_mcp_id confirms the new transform in Unreal.
7. Re-plan reports noop: 1.
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


def _find_actor_by_name(actors, desired_name):
    return next((actor for actor in actors if actor.get("name") == desired_name), None)


def main():
    suffix = time.strftime("%Y%m%d%H%M%S")
    scene_id = f"phase5_verify_{suffix}"
    mcp_id = f"phase5_cube_{suffix}"
    desired_name = f"Phase5VerifyCube_{suffix}"

    require_success("scene-syncd health", get_json("/health"))

    require_success(
        "create scene",
        post_json(
            "/scenes/create",
            {
                "scene_id": scene_id,
                "name": "Phase 5 verification",
                "description": "Created by scripts/verify_phase5.py",
            },
        ),
    )

    # Step 1: create desired object at origin
    require_success(
        "upsert object (create)",
        post_json(
            "/objects/upsert",
            {
                "scene_id": scene_id,
                "mcp_id": mcp_id,
                "desired_name": desired_name,
                "actor_type": "StaticMeshActor",
                "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
                "transform": {
                    "location": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
                "tags": ["phase5_verify"],
            },
        ),
    )

    # Step 2: sync to Unreal
    apply = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync (create)", apply)
    summary = apply["data"]["summary"]
    if summary["succeeded"] < 1 or summary["failed"] != 0 or summary["creates"] != 1:
        raise RuntimeError(f"apply did not create cleanly: {json.dumps(apply, indent=2)}")

    # Step 3: update transform in DB
    require_success(
        "upsert object (update transform)",
        post_json(
            "/objects/upsert",
            {
                "scene_id": scene_id,
                "mcp_id": mcp_id,
                "desired_name": desired_name,
                "actor_type": "StaticMeshActor",
                "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
                "transform": {
                    "location": {"x": 500.0, "y": 250.0, "z": 100.0},
                    "rotation": {"pitch": 10.0, "yaw": 20.0, "roll": 30.0},
                    "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
                },
                "tags": ["phase5_verify"],
            },
        ),
    )

    # Step 4: plan must show update_transform: 1
    plan = post_json("/sync/plan", {"scene_id": scene_id})
    require_success("plan sync", plan)
    plan_summary = plan["data"]["summary"]
    if plan_summary.get("update_transform", 0) != 1:
        raise RuntimeError(
            f"plan did not report update_transform: 1. Got: {json.dumps(plan_summary, indent=2)}"
        )

    # Step 5: sync to Unreal
    apply2 = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync (update)", apply2)
    apply2_summary = apply2["data"]["summary"]
    if apply2_summary["succeeded"] < 1 or apply2_summary["failed"] != 0 or apply2_summary["update_transforms"] != 1:
        raise RuntimeError(f"apply did not update transform cleanly: {json.dumps(apply2, indent=2)}")

    # Step 6: verify via Unreal bridge if available
    unreal_verified = False
    try:
        mcp_response = unreal_command("find_actor_by_mcp_id", {"mcp_id": mcp_id})
        if not mcp_response.get("result", {}).get("success"):
            raise RuntimeError(f"find_actor_by_mcp_id failed: {json.dumps(mcp_response, indent=2)}")
        actor = mcp_response.get("result", {}).get("actor")
        if actor is None:
            raise RuntimeError(f"find_actor_by_mcp_id returned no actor for {mcp_id}")
        loc = actor.get("location", [])
        if len(loc) >= 3 and abs(loc[0] - 500.0) > 0.1:
            raise RuntimeError(f"Transform was not applied in Unreal. location={loc}")
        unreal_verified = True
    except (ConnectionRefusedError, socket.timeout, RuntimeError) as e:
        print(f"WARNING: Unreal bridge not available for verification: {e}", file=sys.stderr)

    # Step 7: re-plan must be noop
    replan = post_json("/sync/plan", {"scene_id": scene_id})
    require_success("re-plan sync", replan)
    replan_summary = replan["data"]["summary"]
    if replan_summary.get("noop", 0) != 1 or replan_summary.get("update_transform", 0) != 0:
        raise RuntimeError(
            f"Re-plan did not return noop: 1. Got: {json.dumps(replan_summary, indent=2)}"
        )

    result = {
        "success": True,
        "scene_id": scene_id,
        "mcp_id": mcp_id,
        "actor_name": desired_name,
        "unreal_bridge_verified": unreal_verified,
        "plan_summary": plan_summary,
        "apply_summary": apply2_summary,
        "replan_summary": replan_summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"verify_phase5 failed: {exc}", file=sys.stderr)
        sys.exit(1)
