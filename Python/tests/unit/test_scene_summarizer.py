"""Unit tests for server.intent.scene_summarizer and scene_context."""

from __future__ import annotations

import json
import random

import pytest

from server.intent.scene_context import (
    AssetBrief,
    ComponentBrief,
    EntityBrief,
    OperationBrief,
    SceneContextPack,
    SceneObjectBrief,
    SnapshotBrief,
)
from server.intent.scene_summarizer import (
    MAX_PER_COMPONENT_TYPE,
    MAX_PER_KIND,
    SceneSummarizer,
    estimate_tokens,
)


class _FakeClient:
    def __init__(self, payloads):
        self.payloads = payloads

    def call_scene_syncd(self, path, payload):
        data = self.payloads.get(path, {"data": {}})
        return {"success": True, "data": data}


def _envelope(key, items):
    return {key: items}


def _objects(n, kinds=("wall", "floor", "light", "fog", "spawn_point")):
    out = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        out.append({
            "mcp_id": f"obj_{i:04d}",
            "kind": kind,
            "name": f"{kind}_{i}",
            "tags": [kind, "cave"],
            "group": kind,
            "sync_status": "pending" if i % 3 == 0 else "synced",
        })
    return out


def _entities(n):
    return [
        {
            "entity_id": f"ent_{i:04d}",
            "kind": "torch" if i % 2 == 0 else "ambush_zone",
            "name": f"ent_{i}",
            "tags": ["cave"],
        }
        for i in range(n)
    ]


def _components(n, types=("material", "light", "atmosphere", "audio", "vfx", "navmesh")):
    return [
        {
            "entity_id": f"obj_{i:04d}",
            "component_type": types[i % len(types)],
            "name": f"comp_{i}",
            "sync_status": "pending" if i % 5 == 0 else "synced",
        }
        for i in range(n)
    ]


def _make_payloads(scene_id, object_count, component_count, entity_count=0, asset_count=0):
    payloads = {
        "/objects/list": _envelope("objects", _objects(object_count)),
        "/entities/list": _envelope("entities", _entities(entity_count)),
        "/components/list": _envelope("components", _components(component_count)),
        "/assets/list": _envelope("assets", [
            {"asset_id": f"asset_{i:03d}", "kind": "material_instance"}
            for i in range(asset_count)
        ]),
        "/snapshots/list": _envelope("snapshots", [
            {"id": "scene_snapshot:abc", "name": "before_creepy", "revision": 1, "created_at": "2026-05-24T00:00:00Z"},
        ]),
        "/operations/recent": _envelope("operations", [
            {"operation_id": f"op_{i:02d}", "action": "update_visual", "mcp_id": f"obj_{i:03d}", "status": "ok", "reason": "patch_apply"}
            for i in range(3)
        ]),
    }
    return payloads


def test_summarizer_returns_pack_with_correct_counts():
    summarizer = SceneSummarizer(client=_FakeClient(_make_payloads("main", 50, 30, entity_count=10)))
    pack = summarizer.build("main")
    assert isinstance(pack, SceneContextPack)
    assert pack.object_count == 50
    assert pack.component_count == 30
    assert pack.entity_count == 10
    assert len(pack.snapshots) == 1
    assert len(pack.recent_operations) == 3


def test_summarizer_caps_samples_per_kind():
    summarizer = SceneSummarizer(client=_FakeClient(_make_payloads("main", 500, 0)))
    pack = summarizer.build("main")
    for kind, items in pack.objects_by_kind.items():
        assert len(items) <= MAX_PER_KIND, f"kind {kind} not capped"


def test_summarizer_caps_components_per_type():
    summarizer = SceneSummarizer(client=_FakeClient(_make_payloads("main", 0, 500)))
    pack = summarizer.build("main")
    for ctype, items in pack.components_by_type.items():
        assert len(items) <= MAX_PER_COMPONENT_TYPE


def test_scene_context_fits_in_2k_tokens_for_200_actors_and_components():
    summarizer = SceneSummarizer(
        client=_FakeClient(_make_payloads("main", 200, 200, entity_count=50, asset_count=20))
    )
    pack = summarizer.build("main")
    tokens = estimate_tokens(pack.to_dict())
    assert tokens <= 2000, f"context pack too large: {tokens} tokens"


def test_estimate_tokens_handles_strings_and_objects():
    assert estimate_tokens("hello world") >= 1
    assert estimate_tokens({"a": 1}) >= 1


def test_scene_object_brief_infers_kind_from_metadata_before_actor_type():
    obj = SceneObjectBrief.from_dict(
        {
            "mcp_id": "cave_floor",
            "desired_name": "Cave_Floor",
            "actor_type": "StaticMeshActor",
            "metadata": {"kind": "floor"},
            "tags": ["cave", "stone"],
        }
    )
    assert obj.kind == "floor"
    assert obj.name == "Cave_Floor"


def test_scene_object_brief_infers_kind_from_tags():
    obj = SceneObjectBrief.from_dict(
        {
            "mcp_id": "cave_wall_n",
            "desired_name": "Cave_Wall_N",
            "actor_type": "StaticMeshActor",
            "tags": ["cave", "kind:wall"],
        }
    )
    assert obj.kind == "wall"
