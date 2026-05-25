"""E2E: snapshot restore by name resolves latest when multiple match."""

from __future__ import annotations

from typing import Dict, List

import pytest

import server.dialog_tools as dt


@pytest.fixture
def mock_scene_syncd(monkeypatch):
    calls: List[tuple] = []

    def fake_call(path, payload):
        calls.append((path, payload))
        if path == "/snapshots/restore_by_name":
            return {
                "success": True,
                "data": {
                    "snapshot_id": "scene_snapshot:latest",
                    "name": payload.get("name"),
                    "restore": {"restored": 4},
                    "candidates": ["scene_snapshot:latest", "scene_snapshot:older"],
                },
                "warnings": ["multiple snapshots match name 'before_creepy' (2); restored latest by created_at"],
            }
        return {"success": True, "data": {}}

    monkeypatch.setattr("server.scene_client.call_scene_syncd", fake_call)
    return calls


def test_scene_snapshot_restore_by_name_returns_warnings(mock_scene_syncd):
    res = dt.scene_snapshot_restore_by_name(scene_id="cave_test", name="before_creepy")
    assert res["success"]
    assert res["data"]["snapshot_id"] == "scene_snapshot:latest"
    assert res["warnings"], "warnings present when multiple candidates"


def test_scene_snapshot_restore_by_name_requires_name(mock_scene_syncd):
    res = dt.scene_snapshot_restore_by_name(scene_id="cave_test", name="")
    assert res["success"] is False
