"""Live E2E: build a visible cave in Unreal, apply scene_edit, then preview it."""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "Python"
sys.path.insert(0, str(PYTHON_DIR))
os.chdir(PYTHON_DIR)

from server.core import UnrealConnection  # noqa: E402


SCENE_ID = "cave_test"
INTENT = "洞窟を不気味にして"
CUBE_MESH = "/Engine/BasicShapes/Cube.Cube"


CAVE_PARTS = [
    {
        "name": "Cave_Floor",
        "mcp_id": "cave_floor",
        "kind": "floor",
        "type": "StaticMeshActor",
        "location": [0, 0, 0],
        "scale": [20, 20, 0.3],
        "tags": ["cave", "stone", "floor"],
    },
    {
        "name": "Cave_Wall_N",
        "mcp_id": "cave_wall_n",
        "kind": "wall",
        "type": "StaticMeshActor",
        "location": [0, 1000, 200],
        "scale": [20, 0.3, 4],
        "tags": ["cave", "stone", "wall"],
    },
    {
        "name": "Cave_Wall_S_L",
        "mcp_id": "cave_wall_s_l",
        "kind": "wall",
        "type": "StaticMeshActor",
        "location": [-650, -1000, 200],
        "scale": [7, 0.3, 4],
        "tags": ["cave", "stone", "wall", "entrance"],
    },
    {
        "name": "Cave_Wall_S_R",
        "mcp_id": "cave_wall_s_r",
        "kind": "wall",
        "type": "StaticMeshActor",
        "location": [650, -1000, 200],
        "scale": [7, 0.3, 4],
        "tags": ["cave", "stone", "wall"],
    },
    {
        "name": "Cave_Wall_E",
        "mcp_id": "cave_wall_e",
        "kind": "wall",
        "type": "StaticMeshActor",
        "location": [1000, 0, 200],
        "scale": [0.3, 20, 4],
        "tags": ["cave", "stone", "wall"],
    },
    {
        "name": "Cave_Wall_W",
        "mcp_id": "cave_wall_w",
        "kind": "wall",
        "type": "StaticMeshActor",
        "location": [-1000, 0, 200],
        "scale": [0.3, 20, 4],
        "tags": ["cave", "stone", "wall"],
    },
    {
        "name": "Cave_Ceiling",
        "mcp_id": "cave_ceiling",
        "kind": "ceiling",
        "type": "StaticMeshActor",
        "location": [0, 0, 400],
        "scale": [20, 20, 0.3],
        "tags": ["cave", "stone", "wall", "ceiling"],
    },
    {
        "name": "Cave_Fog",
        "mcp_id": "cave_fog",
        "kind": "fog",
        "type": "ExponentialHeightFog",
        "location": [0, 0, 120],
        "scale": [1, 1, 1],
        "tags": ["cave", "fog", "atmosphere"],
    },
]


def make_torch_parts() -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = []
    for i in range(4):
        angle = i * 90
        x = 700 * math.cos(math.radians(angle))
        y = 700 * math.sin(math.radians(angle))
        parts.append(
            {
                "name": f"Torch_{i:02d}",
                "mcp_id": f"torch_{i:02d}",
                "kind": "light",
                "type": "PointLight",
                "location": [x, y, 250],
                "scale": [1, 1, 1],
                "tags": ["cave", "torch", "light"],
            }
        )
        parts.append(
            {
                "name": f"TorchHolder_{i:02d}",
                "mcp_id": f"torchholder_{i:02d}",
                "kind": "wall",
                "type": "StaticMeshActor",
                "location": [x, y, 180],
                "scale": [0.3, 0.3, 1.0],
                "tags": ["cave", "torch", "stone", "wall"],
            }
        )
    return parts


def transform_dict(part: Dict[str, Any]) -> Dict[str, Any]:
    loc = part.get("location", [0, 0, 0])
    scale = part.get("scale", [1, 1, 1])
    return {
        "location": {"x": float(loc[0]), "y": float(loc[1]), "z": float(loc[2])},
        "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
        "scale": {"x": float(scale[0]), "y": float(scale[1]), "z": float(scale[2])},
    }


def post_scene_syncd(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        f"http://127.0.0.1:8787{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ue(
    conn: UnrealConnection,
    cmd: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    warn: bool = True,
) -> Dict[str, Any]:
    result = conn.send_command(cmd, params or {})
    if result and result.get("success") is not False and result.get("status") != "error":
        return result
    if warn:
        print(f"  WARN {cmd}: {json.dumps(result, ensure_ascii=False, default=str)[:300]}")
    return result or {"success": False, "error": "no response"}


def delete_existing_demo_actors(conn: UnrealConnection, parts: Iterable[Dict[str, Any]]) -> None:
    print("[2/6] Removing old demo actors with the same names...")
    actual_names: List[str] = []
    for pattern in ("Cave_", "Torch"):
        found = ue(conn, "find_actors_by_name", {"pattern": pattern})
        for actor in found.get("actors", []) if isinstance(found, dict) else []:
            name = actor.get("name")
            if not isinstance(name, str):
                continue
            if name.startswith("Cave_") or name.startswith("Torch_") or name.startswith("TorchHolder_"):
                actual_names.append(name)
    for name in sorted(set(actual_names)):
        ue(conn, "delete_actor", {"name": name})


def spawn_part(conn: UnrealConnection, part: Dict[str, Any]) -> None:
    params: Dict[str, Any] = {
        "type": part["type"],
        "name": part["name"],
        "mcp_id": part["mcp_id"],
        "location": part.get("location", [0, 0, 0]),
        "scale": part.get("scale", [1, 1, 1]),
        "tags": part.get("tags", []),
    }
    if part["type"] == "StaticMeshActor":
        params["static_mesh"] = CUBE_MESH
    result = ue(conn, "spawn_actor", params)
    actual_name = result.get("name") if isinstance(result, dict) else None
    part["actual_name"] = actual_name if isinstance(actual_name, str) and actual_name else part["name"]


def sync_scene(parts: List[Dict[str, Any]]) -> None:
    print("[4/6] Syncing cave metadata to scene-syncd...")
    post_scene_syncd(
        "/scenes/create",
        {"scene_id": SCENE_ID, "name": "Cave Test", "description": "Visible cave scene for scene_edit demo"},
    )
    try:
        existing = post_scene_syncd("/objects/list", {"scene_id": SCENE_ID, "include_deleted": False})
        for obj in existing.get("data", {}).get("objects", []):
            mcp_id = obj.get("mcp_id", "")
            if isinstance(mcp_id, str) and (
                mcp_id.startswith("cave_") or mcp_id.startswith("torch_") or mcp_id.startswith("torchholder_")
            ):
                post_scene_syncd("/objects/delete", {"scene_id": SCENE_ID, "mcp_id": mcp_id})
    except Exception as exc:  # noqa: BLE001
        print(f"[4/6] WARN existing scene cleanup skipped: {exc}")

    objects = []
    for part in parts:
        objects.append(
            {
                "scene_id": SCENE_ID,
                "mcp_id": part["mcp_id"],
                "desired_name": part.get("actual_name", part["name"]),
                "actor_type": part["type"],
                "asset_ref": {"path": CUBE_MESH} if part["type"] == "StaticMeshActor" else {},
                "transform": transform_dict(part),
                "tags": part.get("tags", []),
                "metadata": {"kind": part["kind"], "requested_name": part["name"]},
            }
        )
    resp = post_scene_syncd("/objects/bulk-upsert", {"scene_id": SCENE_ID, "objects": objects})
    print(f"[4/6] scene-syncd upserted={resp.get('data', resp).get('upserted_count')} errors={resp.get('data', resp).get('error_count')}")


def main() -> int:
    conn = UnrealConnection()
    if not conn.connect():
        print("Cannot connect to Unreal on 55771")
        return 1
    print("[1/6] Connected to Unreal")

    parts = CAVE_PARTS + make_torch_parts()
    delete_existing_demo_actors(conn, parts)

    print("[3/6] Spawning visible cave actors...")
    for part in parts:
        spawn_part(conn, part)
    print(f"[3/6] Spawned {len(parts)} cave actors with visible cube meshes")

    sync_scene(parts)

    print(f"[5/6] Running scene_edit apply_safe: {INTENT}")
    import server.dialog_tools as dt  # noqa: E402
    from server.scene_client import call_scene_syncd  # noqa: E402

    dt._summarizer_client = lambda: type("C", (), {"call_scene_syncd": staticmethod(call_scene_syncd)})()

    dry = dt.scene_edit(INTENT, scene_id=SCENE_ID, target="cave", mode="dry_run")
    print(json.dumps(dry, indent=2, ensure_ascii=False, default=str)[:2500])
    if dry.get("success") and dry.get("patch_id"):
        explained = dt.scene_explain_plan(dry["patch_id"])
        print(explained.get("markdown", "")[:1800])

    applied = dt.scene_edit(INTENT, scene_id=SCENE_ID, target="cave", mode="apply_safe", create_snapshot=True)
    print(json.dumps({
        "success": applied.get("success"),
        "succeeded": applied.get("succeeded"),
        "failed": applied.get("failed"),
        "snapshot_id": applied.get("snapshot_id"),
        "errors": applied.get("errors", []),
    }, indent=2, ensure_ascii=False, default=str))

    print("[6/6] Taking scene_preview single screenshot...")
    preview = dt.scene_preview(scene_id=SCENE_ID, target="cave", batch="single")
    print(
        f"Preview success={preview.get('success')}, "
        f"images={len(preview.get('images', []))}, warnings={preview.get('warnings', [])}"
    )
    if preview.get("per_image_metrics"):
        print(json.dumps(preview["per_image_metrics"][0], indent=2, ensure_ascii=False, default=str)[:1200])

    # Give the editor viewport a moment to redraw after the final camera move.
    time.sleep(0.5)
    conn.disconnect()
    print("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
