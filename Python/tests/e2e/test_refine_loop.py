"""E2E: 100-step refine loop and refine-time target inheritance."""

from __future__ import annotations

from typing import Dict, List

import pytest

import server.dialog_tools as dt
from helpers.fake_unreal_connection import FakeUnrealConnection


class _Mem:
    def __init__(self):
        self.calls: List[tuple] = []
        self.objects = [
            {"mcp_id": f"torch_{i:02d}", "kind": "light", "name": f"torch_{i:02d}", "tags": ["torch"]}
            for i in range(8)
        ]
        component_types = ["material", "light", "atmosphere", "audio", "vfx", "navmesh"]
        self.components = [
            {
                "entity_id": f"entity_{i % 200:03d}",
                "component_type": component_types[i % len(component_types)],
                "name": f"stress_component_{i:04d}",
                "sync_status": "pending",
            }
            for i in range(1000)
        ]

    def __call__(self, path, payload):
        self.calls.append((path, payload))
        defaults = {
            "/objects/list": {"success": True, "data": {"objects": self.objects}},
            "/entities/list": {"success": True, "data": {"entities": []}},
            "/components/list": {"success": True, "data": {"components": self.components}},
            "/assets/list": {"success": True, "data": {"assets": []}},
            "/snapshots/list": {"success": True, "data": {"snapshots": []}},
            "/operations/recent": {"success": True, "data": {"operations": []}},
        }
        return defaults.get(path, {"success": True, "data": {}})


def test_100_refine_loop_with_1000_components_completes_in_under_30s(monkeypatch):
    mem = _Mem()
    fake = FakeUnrealConnection()
    monkeypatch.setattr(dt, "_summarizer_client",
                        lambda: type("C", (), {"call_scene_syncd": staticmethod(mem)})())
    monkeypatch.setattr(
        "server.planning.patch_executor._default_scene_syncd", lambda: mem
    )
    monkeypatch.setattr(
        "server.planning.patch_executor._default_unreal_connection", lambda: fake
    )

    seed = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="dry_run")
    assert seed["success"]
    described = dt.scene_describe(scene_id="cave_test")
    assert described["success"]
    assert described["context"]["component_count"] == 1000
    assert described["estimated_tokens"] < 2000

    import time
    t0 = time.perf_counter()
    for i in range(100):
        res = dt.scene_refine(
            f"refine pass {i}",
            scene_id="cave_test",
            mode="dry_run",
            max_operations=200,
        )
        assert res["success"]
    elapsed = time.perf_counter() - t0
    assert elapsed < 30.0, f"refine loop too slow: {elapsed:.2f}s"
