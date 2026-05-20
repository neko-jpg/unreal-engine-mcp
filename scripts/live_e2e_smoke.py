"""Live E2E smoke runner for the 13 commands in priority A-2.

Requires (any subset works; missing services degrade gracefully):
  - Unreal Editor with UnrealMCP plugin bridge on 127.0.0.1:55557
  - scene-syncd on 127.0.0.1:8787  (for /sync/* and /procedural/* endpoints)
  - SurrealDB on 127.0.0.1:8000    (backing store for scene_create etc.)

Each case is independent; failures are reported but do not stop the run.
Output is human-readable + a JSON report written to artifacts/live_e2e_<utc>.json.

Usage:
    python scripts\live_e2e_smoke.py
    python scripts\live_e2e_smoke.py --case ping spawn_actor
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557
SCENE_SYNCD = "http://127.0.0.1:8787"


# ----- Transport helpers -----------------------------------------------------

def _unreal_send(command: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
    """Send one command using the UnrealMCP line-delimited TCP protocol."""
    payload = json.dumps({"command": command, "params": params or {}}).encode("utf-8") + b"\n"
    with socket.create_connection((UNREAL_HOST, UNREAL_PORT), timeout=10) as s:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(timeout)
        s.sendall(payload)
        data = bytearray()
        while b"\n" not in data:
            chunk = s.recv(262144)
            if not chunk:
                raise ConnectionError("Unreal connection closed before newline-delimited response")
            data.extend(chunk)
        parsed = json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))
        result = parsed.get("result") if isinstance(parsed, dict) else None
        if isinstance(result, dict):
            for key, value in result.items():
                parsed.setdefault(key, value)
        return parsed

def _http_post(path: str, payload: Dict[str, Any], timeout: float = 60.0) -> Dict[str, Any]:
    req = urllib.request.Request(f"{SCENE_SYNCD}{path}",
                                 data=json.dumps(payload).encode("utf-8"),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _service_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ----- Case definitions ------------------------------------------------------

def case_ping() -> Dict[str, Any]:
    out = _unreal_send("ping")
    assert out.get("success") is True or out.get("status") == "success" or out.get("type") == "pong", out
    return {"unreal_result": out}


def case_spawn_actor(state: Dict[str, Any]) -> Dict[str, Any]:
    mcp_id = state["mcp_id"] = f"smoke_{uuid.uuid4().hex[:8]}"
    out = _unreal_send("spawn_actor", {
        "name": mcp_id,
        "type": "StaticMeshActor",
        "location": [0.0, 0.0, 100.0],
        "mcp_id": mcp_id,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"mcp_id": mcp_id, "unreal_result": out}


def case_set_actor_transform_by_mcp_id(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("set_actor_transform_by_mcp_id", {
        "mcp_id": state["mcp_id"],
        "location": [200.0, 0.0, 100.0],
        "rotation": [0.0, 45.0, 0.0],
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_delete_actor_by_mcp_id(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("delete_actor_by_mcp_id", {"mcp_id": state["mcp_id"]})
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_scene_create(state: Dict[str, Any]) -> Dict[str, Any]:
    scene_id = state["scene_id"] = f"smoke_scene_{uuid.uuid4().hex[:6]}"
    out = _http_post("/scenes/create", {"scene_id": scene_id, "name": "live smoke"})
    assert out.get("success") is True or out.get("status") == "success", out
    return {"scene_id": scene_id, "scene_syncd_result": out}


def case_scene_upsert_actor(state: Dict[str, Any]) -> Dict[str, Any]:
    scene_id = state["scene_id"]
    obj_id = state["obj_id"] = f"smoke_obj_{uuid.uuid4().hex[:6]}"
    out = _http_post("/objects/upsert", {
        "scene_id": scene_id,
        "mcp_id": obj_id,
        "actor_type": "StaticMeshActor",
        "transform": {"location": {"x": 0, "y": 0, "z": 100}},
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"obj_id": obj_id, "scene_syncd_result": out}


def case_scene_plan_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _http_post("/sync/plan", {"scene_id": state["scene_id"], "mode": "plan_only"})
    assert out.get("success") is True or out.get("status") == "success", out
    return {"scene_syncd_result": out}


def case_scene_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _http_post("/sync/apply", {"scene_id": state["scene_id"], "mode": "apply", "max_ops": 25})
    assert out.get("success") is True or out.get("status") == "success", out
    return {"scene_syncd_result": out}


def case_create_draft_proxy(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("create_draft_proxy", {
        "proxy_name": f"smoke_proxy_{uuid.uuid4().hex[:6]}",
        "mesh_path": "/Engine/BasicShapes/Cube.Cube",
        "instances": [
            {"location": {"x": 0, "y": 0, "z": 200},
             "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
             "scale": {"x": 1, "y": 1, "z": 1}}
        ],
        "use_dither": False,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_spawn_instance_set(state: Dict[str, Any]) -> Dict[str, Any]:
    set_id = state["set_id"] = f"smoke_set_{uuid.uuid4().hex[:6]}"
    out = _unreal_send("spawn_instance_set", {
        "set_id": set_id,
        "mesh_path": "/Engine/BasicShapes/Cube.Cube",
        "instances": [
            {"location": {"x": i * 150.0, "y": 0, "z": 100},
             "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
             "scale": {"x": 1, "y": 1, "z": 1}}
            for i in range(4)
        ],
        "use_hism": True,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"set_id": set_id, "unreal_result": out}


def case_scene_create_wfc_grid_unreal(state: Dict[str, Any]) -> Dict[str, Any]:
    tiles = [{"id": "A", "weight": 1.0}, {"id": "B", "weight": 1.0}]
    out = _http_post("/procedural/wfc-grid", {
        "width": 4, "height": 4,
        "tileset": {
            "tiles": tiles,
            "constraints": [
                {"left": "A", "right": "B", "direction": "east"},
                {"left": "B", "right": "A", "direction": "east"},
                {"left": "A", "right": "A", "direction": "south"},
                {"left": "B", "right": "B", "direction": "south"},
            ],
        },
        "seed": 42,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"scene_syncd_result": out}


def case_compile_all_blueprints(state: Dict[str, Any]) -> Dict[str, Any]:
    # Cesium for Unreal ships ~17 Blueprint assets that cold-compile on first
    # run; 30s default is too tight. Allow up to 5 minutes for the first call.
    out = _unreal_send("compile_all_blueprints", {"max_compiles": 200}, timeout=300.0)
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_run_map_check(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("run_map_check", {})
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


# ----- B-4 Cesium live cases (require Cesium for Unreal v2.18+ + token) ------

def case_cesium_check_plugin(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("cesium_check_plugin", {})
    assert out.get("success") is True or out.get("status") == "success", out
    data = (out.get("data") or {}) if isinstance(out.get("data"), dict) else {}
    assert data.get("available") is True or data.get("installed") is True, out
    return {"unreal_result": out}


def case_cesium_setup_georeference(state: Dict[str, Any]) -> Dict[str, Any]:
    out = _unreal_send("cesium_setup_georeference", {
        "origin_latitude": 35.6586, "origin_longitude": 139.7454, "origin_height": 0,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_cesium_add_tileset(state: Dict[str, Any]) -> Dict[str, Any]:
    token = os.environ.get("CESIUM_ION_TOKEN", "")
    assert token, "set CESIUM_ION_TOKEN"
    out = _unreal_send("cesium_add_tileset", {
        "actor_name": "CesiumWorldTerrain_Smoke",
        "ion_asset_id": 96188,
        "ion_access_token": token,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out}


def case_cesium_place_actor_at_geolocation(state: Dict[str, Any]) -> Dict[str, Any]:
    mcp_id = f"cesium_pin_{uuid.uuid4().hex[:6]}"
    spawn = _unreal_send("spawn_actor", {
        "name": mcp_id,
        "type": "StaticMeshActor",
        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        "mcp_id": mcp_id,
    })
    assert spawn.get("success") is True or spawn.get("status") == "success", spawn
    out = _unreal_send("cesium_place_actor_at_geolocation", {
        "actor_mcp_id": mcp_id,
        "latitude": 35.6586, "longitude": 139.7454, "height": 100.0,
    })
    assert out.get("success") is True or out.get("status") == "success", out
    return {"unreal_result": out, "spawn_result": spawn}


def case_create_data_layer_for_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn a tagged actor and assign it to a generated Data Layer.

    Verifies M1 wiring of FEpicUnrealMCPDataLayerHelpers (Build.cs +
    EpicUnrealMCPProceduralCommands). Accepts either method=data_layer_instance
    (full World Partition path via UDataLayerEditorSubsystem) or method=tag
    (non-WP graceful fallback); both prove the helpers are wired.
    """
    mcp_id = f"dl_pin_{uuid.uuid4().hex[:6]}"
    spawn = _unreal_send("spawn_actor", {
        "name": mcp_id,
        "type": "StaticMeshActor",
        "static_mesh": "/Engine/BasicShapes/Cube.Cube",
        "mcp_id": mcp_id,
    })
    assert spawn.get("success") is True or spawn.get("status") == "success", spawn
    layer_name = f"M1_Smoke_{uuid.uuid4().hex[:6]}"
    out = _unreal_send("create_data_layer_for_generation", {
        "data_layer_name": layer_name,
        "actor_mcp_ids": [mcp_id],
        "color_hex": "FF8800",
        "initial_state": "Activated",
    })
    assert out.get("success") is True or out.get("status") == "success", out
    data = (out.get("data") or {}) if isinstance(out.get("data"), dict) else {}
    method = data.get("method")
    assert method in ("data_layer_instance", "tag"), out
    assigned = data.get("actors_assigned_count")
    assert assigned == 1, out
    return {"unreal_result": out, "spawn_result": spawn, "method": method}

CASES: List[Tuple[str, str, Callable[..., Dict[str, Any]]]] = [
    ("ping",                          "unreal", case_ping),
    ("spawn_actor",                   "unreal", case_spawn_actor),
    ("set_actor_transform_by_mcp_id", "unreal", case_set_actor_transform_by_mcp_id),
    ("delete_actor_by_mcp_id",        "unreal", case_delete_actor_by_mcp_id),
    ("scene_create",                  "syncd",  case_scene_create),
    ("scene_upsert_actor",            "syncd",  case_scene_upsert_actor),
    ("scene_plan_sync",               "syncd",  case_scene_plan_sync),
    ("scene_sync",                    "both",   case_scene_sync),
    ("create_draft_proxy",            "unreal", case_create_draft_proxy),
    ("spawn_instance_set",            "unreal", case_spawn_instance_set),
    ("scene_create_wfc_grid_unreal",  "syncd",  case_scene_create_wfc_grid_unreal),
    ("compile_all_blueprints",        "unreal", case_compile_all_blueprints),
    ("run_map_check",                 "unreal", case_run_map_check),
    ("create_data_layer_for_generation", "unreal", case_create_data_layer_for_generation),
    # ----- B-4 Cesium live cases (auto-skip when plugin/token missing) -----
    ("cesium_check_plugin",                "cesium", case_cesium_check_plugin),
    ("cesium_setup_georeference",          "cesium", case_cesium_setup_georeference),
    ("cesium_add_tileset",                 "cesium", case_cesium_add_tileset),
    ("cesium_place_actor_at_geolocation",  "cesium", case_cesium_place_actor_at_geolocation),
]


# ----- Runner ----------------------------------------------------------------

def _cesium_available() -> Tuple[bool, str]:
    """Probe the Unreal bridge for Cesium plugin presence.

    Returns (available, reason). available=True only when the editor reports
    the plugin as available AND was compiled with WITH_CESIUM=1.
    """
    try:
        out = _unreal_send("cesium_check_plugin", {}, timeout=10.0)
    except Exception as exc:
        return False, f"cesium_check_plugin transport error: {exc}"
    data = (out.get("data") or {}) if isinstance(out.get("data"), dict) else {}
    available = bool(data.get("available") or data.get("installed"))
    compiled_with = bool(data.get("compiled_with_cesium"))
    if not available:
        return False, "Cesium for Unreal plugin not installed/enabled"
    if not compiled_with:
        return False, "UnrealMCP not compiled with WITH_CESIUM=1 (rebuild after installing Cesium)"
    return True, ""


def run(selected: Optional[List[str]] = None) -> int:
    have_unreal = _service_open(UNREAL_HOST, UNREAL_PORT)
    have_syncd  = _service_open("127.0.0.1", 8787)
    have_cesium = False
    cesium_reason = "unreal bridge unavailable"
    have_cesium_token = bool(os.environ.get("CESIUM_ION_TOKEN"))
    if have_unreal:
        have_cesium, cesium_reason = _cesium_available()
    print(f"[env] unreal-bridge :55557 = {have_unreal}, scene-syncd :8787 = {have_syncd}, "
          f"cesium = {have_cesium} ({cesium_reason or 'ok'}), CESIUM_ION_TOKEN set = {have_cesium_token}")
    state: Dict[str, Any] = {}
    report: List[Dict[str, Any]] = []
    passed = failed = skipped = 0
    for name, requires, fn in CASES:
        if selected and name not in selected:
            continue
        if requires in ("unreal", "both", "cesium") and not have_unreal:
            print(f"[skip] {name}: requires Unreal bridge")
            report.append({"name": name, "status": "skipped", "reason": "no unreal"})
            skipped += 1
            continue
        if requires in ("syncd", "both") and not have_syncd:
            print(f"[skip] {name}: requires scene-syncd")
            report.append({"name": name, "status": "skipped", "reason": "no scene-syncd"})
            skipped += 1
            continue
        if requires == "cesium" and not have_cesium:
            print(f"[skip] {name}: requires Cesium for Unreal plugin ({cesium_reason})")
            report.append({"name": name, "status": "skipped",
                           "reason": f"no cesium: {cesium_reason}"})
            skipped += 1
            continue
        # cesium_add_tileset also needs an Ion token
        if requires == "cesium" and name == "cesium_add_tileset" and not have_cesium_token:
            print(f"[skip] {name}: CESIUM_ION_TOKEN not set")
            report.append({"name": name, "status": "skipped",
                           "reason": "no CESIUM_ION_TOKEN"})
            skipped += 1
            continue
        t0 = time.time()
        try:
            out = fn(state) if fn.__code__.co_argcount else fn()  # type: ignore[arg-type]
            elapsed = round(time.time() - t0, 3)
            print(f"[pass] {name}  ({elapsed}s)")
            report.append({"name": name, "status": "pass", "elapsed": elapsed, "result": out})
            passed += 1
        except Exception as exc:
            elapsed = round(time.time() - t0, 3)
            print(f"[FAIL] {name}: {exc}")
            report.append({"name": name, "status": "fail", "elapsed": elapsed, "error": str(exc)})
            failed += 1

    summary = {"passed": passed, "failed": failed, "skipped": skipped, "total": passed + failed + skipped}
    print(f"\n[summary] {summary}")
    out_path = ARTIFACTS / f"live_e2e_{int(time.time())}.json"
    out_path.write_text(json.dumps({"summary": summary, "cases": report}, indent=2), encoding="utf-8")
    print(f"[report] {out_path}")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", nargs="*", default=None, help="case names to run")
    args = parser.parse_args()
    return run(args.case)


if __name__ == "__main__":
    sys.exit(main())
