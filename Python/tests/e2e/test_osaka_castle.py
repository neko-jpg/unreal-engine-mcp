"""E2E: Osaka castle heroic mood scenario."""

from __future__ import annotations

from typing import Dict, List

import pytest

import server.dialog_tools as dt
from helpers.fake_unreal_connection import FakeUnrealConnection


class _Mem:
    def __init__(self):
        self.calls: List[tuple] = []
        self.objects = [
            {"mcp_id": "donjon", "kind": "wall", "name": "donjon", "tags": ["castle", "stone"]},
            {"mcp_id": "watch_tower", "kind": "wall", "name": "watch_tower", "tags": ["castle", "stone"]},
            {"mcp_id": "directional_sun", "kind": "DirectionalLight", "name": "sun", "tags": []},
        ]

    def __call__(self, path, payload):
        self.calls.append((path, payload))
        defaults = {
            "/objects/list": {"success": True, "data": {"objects": self.objects}},
            "/entities/list": {"success": True, "data": {"entities": []}},
            "/components/list": {"success": True, "data": {"components": []}},
            "/assets/list": {"success": True, "data": {"assets": []}},
            "/snapshots/list": {"success": True, "data": {"snapshots": []}},
            "/operations/recent": {"success": True, "data": {"operations": []}},
            "/snapshots/create": {"success": True, "data": {"id": "scene_snapshot:1"}},
            "/components/upsert": {"success": True, "data": {}},
            "/operations/record": {"success": True},
            "/objects/bulk-upsert": {"success": True, "data": {"upserted_count": 0}},
        }
        return defaults.get(path, {"success": True, "data": {}})


def test_osaka_castle_heroic_mood(monkeypatch):
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

    res = dt.scene_edit(
        "make Osaka castle heroic",
        scene_id="osaka",
        mode="apply_safe",
        style_profile="osaka_castle",
    )
    assert res["success"]
    # The osaka_castle profile is loaded as style_profile; verify lighting fired.
    assert any(c.startswith("set_light_") for c in fake.commands())
