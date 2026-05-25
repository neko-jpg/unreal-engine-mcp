"""React-for-UE v3.0 demo script.

Walks through dry_run -> explain -> apply_safe -> preview using the
FakeUnrealConnection so you can see how the dialog tools behave without a
running editor. Prints structured output to stdout.

Run:

    python -m scripts.demo_react_for_ue
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PY_ROOT = HERE.parent.parent
sys.path.insert(0, str(PY_ROOT))


def main() -> int:
    from helpers.fake_unreal_connection import FakeUnrealConnection
    import server.dialog_tools as dt

    objects = [
        {"mcp_id": f"torch_{i:02d}", "kind": "light", "name": f"torch_{i:02d}", "tags": ["torch", "wall"]}
        for i in range(3)
    ] + [
        {"mcp_id": "wall_n", "kind": "wall", "name": "wall_n", "tags": ["stone"]},
        {"mcp_id": "floor_main", "kind": "floor", "name": "floor_main", "tags": ["stone"]},
    ]

    class _Mem:
        def __init__(self):
            self.snapshots = []

        def __call__(self, path, payload):
            if path == "/objects/list":
                return {"success": True, "data": {"objects": objects}}
            if path == "/snapshots/create":
                snap = {"id": f"scene_snapshot:{len(self.snapshots)+1}"}
                self.snapshots.append(snap)
                return {"success": True, "data": snap}
            return {"success": True, "data": {path.strip('/').split('/')[-1] if path.endswith('s') else 'value': []}}

    mem = _Mem()
    fake = FakeUnrealConnection()

    # Patch the in-process indirection used by dialog_tools/executor.
    dt._summarizer_client = lambda: type("C", (), {"call_scene_syncd": staticmethod(mem)})()
    from server.planning import patch_executor
    patch_executor._default_scene_syncd = lambda: mem
    patch_executor._default_unreal_connection = lambda: fake

    intent = "make this cave creepy"
    print("=== dry_run ===")
    dry = dt.scene_edit(intent, scene_id="demo_cave", mode="dry_run")
    print(json.dumps({k: dry[k] for k in ("success", "operation_count", "risk_level", "plan")}, indent=2))

    print("\n=== explain ===")
    explained = dt.scene_explain_plan(dry["patch_id"])
    print(explained["markdown"])

    print("\n=== apply_safe ===")
    applied = dt.scene_edit(intent, scene_id="demo_cave", mode="apply_safe", create_snapshot=True)
    print(json.dumps({k: applied[k] for k in ("success", "snapshot_id", "succeeded", "noop", "failed")}, indent=2))

    print("\n=== preview ===")
    preview = dt.scene_preview(scene_id="demo_cave")
    print(json.dumps({"success": preview["success"], "vlm_status": preview.get("vlm", {}).get("vlm_status")}, indent=2))

    print("\nDemo finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
