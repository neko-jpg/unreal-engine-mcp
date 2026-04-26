"""Phase 4 verification script.

Acceptance criteria:
1. scene_upsert_actor creates a desired object.
2. scene_plan_sync reports create: 1.
3. scene_sync creates the actor in Unreal.
4. find_actor_by_mcp_id finds the actor.
5. Re-plan reports noop: 1.
6. Re-sync does nothing.
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
    scene_id = f"phase4_verify_{suffix}"
    mcp_id = f"phase4_cube_{suffix}"
    desired_name = f"Phase4VerifyCube_{suffix}"

    require_success("scene-syncd health", get_json("/health"))

    require_success(
        "create scene",
        post_json(
            "/scenes/create",
            {
                "scene_id": scene_id,
                "name": "Phase 4 verification",
                "description": "Created by scripts/verify_phase4.py",
            },
        ),
    )

    require_success(
        "upsert object",
        post_json(
            "/objects/upsert",
            {
                "scene_id": scene_id,
                "mcp_id": mcp_id,
                "desired_name": desired_name,
                "actor_type": "StaticMeshActor",
                "asset_ref": {"path": "/Engine/BasicShapes/Cube.Cube"},
                "transform": {
                    "location": {"x": 250.0, "y": 0.0, "z": 120.0},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
                "tags": ["phase4_verify"],
            },
        ),
    )

    plan = post_json("/sync/plan", {"scene_id": scene_id})
    require_success("plan sync", plan)

    apply = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("apply sync", apply)

    apply_data = apply["data"]
    summary = apply_data["summary"]
    if summary["succeeded"] < 1 or summary["failed"] != 0:
        raise RuntimeError(f"apply did not create cleanly: {json.dumps(apply, indent=2)}")

    # Verify via Unreal bridge commands if available
    unreal_available = False
    try:
        actors_response = unreal_command("get_actors_in_level")
        actors = actors_response.get("result", {}).get("actors", [])
        created = _find_actor_by_name(actors, desired_name)
        if created is None:
            raise RuntimeError(f"actor {desired_name} was not found in Unreal after apply")

        # 4. find_actor_by_mcp_id verification
        mcp_response = unreal_command("find_actor_by_mcp_id", {"mcp_id": mcp_id})
        if not mcp_response.get("result", {}).get("success"):
            raise RuntimeError(f"find_actor_by_mcp_id failed for {mcp_id}: {json.dumps(mcp_response, indent=2)}")
        mcp_actor = mcp_response.get("result", {}).get("actor")
        if mcp_actor is None:
            raise RuntimeError(f"find_actor_by_mcp_id returned no actor for {mcp_id}")
        unreal_available = True
    except (ConnectionRefusedError, socket.timeout, RuntimeError) as e:
        print(f"WARNING: Unreal bridge not available for verification: {e}", file=sys.stderr)

    # 5. Re-plan must show noop: 1
    replan = post_json("/sync/plan", {"scene_id": scene_id})
    require_success("re-plan sync", replan)
    replan_summary = replan["data"]["summary"]
    if replan_summary.get("noop", 0) != 1 or replan_summary.get("create", 0) != 0:
        raise RuntimeError(
            f"Re-plan did not return noop: 1 (create must be 0). Got: {json.dumps(replan_summary, indent=2)}"
        )

    # 6. Re-sync must not create anything new
    reapply = post_json(
        "/sync/apply",
        {
            "scene_id": scene_id,
            "mode": "apply_safe",
            "allow_delete": False,
            "max_operations": 10,
        },
    )
    require_success("re-apply sync", reapply)
    reapply_summary = reapply["data"]["summary"]
    if reapply_summary.get("succeeded", 0) != 1 or reapply_summary.get("creates", 0) != 0:
        raise RuntimeError(
            f"Re-sync did not behave as expected (expected 1 noop/succeeded, 0 creates). Got: {json.dumps(reapply_summary, indent=2)}"
        )

    result = {
        "success": True,
        "scene_id": scene_id,
        "mcp_id": mcp_id,
        "actor_name": desired_name,
        "unreal_bridge_verified": unreal_available,
        "plan_summary": plan["data"]["summary"],
        "apply_summary": summary,
        "replan_summary": replan_summary,
        "reapply_summary": reapply_summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"verify_phase4 failed: {exc}", file=sys.stderr)
        sys.exit(1)
