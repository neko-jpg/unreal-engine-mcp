"""Unit tests for scene_object_info and scene_spatial_query."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import ANY, MagicMock

import pytest

import server.dialog_tools as dt


_SENTINEL = object()

class _FakeClient:
    def __init__(self, objects=_SENTINEL):
        if objects is not _SENTINEL:
            self._objects = objects
        else:
            self._objects = [
                {"mcp_id": "torch_01", "name": "torch_01", "kind": "light",
                 "tags": ["torch", "wall"], "transform": {"location": [100, 200, 50]}},
                {"mcp_id": "torch_02", "name": "torch_02", "kind": "light",
                 "tags": ["torch", "wall"], "transform": {"location": [300, 200, 50]}},
                {"mcp_id": "wall_n", "name": "wall_n", "kind": "wall",
                 "tags": ["stone"], "transform": {"location": [200, 0, 0]}},
                {"mcp_id": "floor_main", "name": "floor_main", "kind": "floor",
                 "tags": ["stone"], "transform": {"location": [0, 0, -10]}},
            ]

    def call_scene_syncd(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if path == "/objects/list":
            return {"success": True, "data": {"objects": self._objects}}
        return {"success": True, "data": {}}


def _no_ue():
    raise ConnectionError("no UE in tests")


def _patch_summarizer(monkeypatch, objects=_SENTINEL):
    def _factory():
        if objects is _SENTINEL:
            return _FakeClient()
        return _FakeClient(objects)
    monkeypatch.setattr(dt, "_summarizer_client", _factory)


# --- scene_object_info ---


def test_object_info_returns_all_objects(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test")
    assert res["success"] is True
    assert res["count"] == 4


def test_object_info_filter_by_mcp_id(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", mcp_id="torch_01")
    assert res["count"] == 1
    assert res["objects"][0]["mcp_id"] == "torch_01"


def test_object_info_filter_by_kind(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", kind="light")
    assert res["count"] == 2
    assert all(o["kind"] == "light" for o in res["objects"])


def test_object_info_filter_by_tags(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", tags=["torch"])
    assert res["count"] == 2


def test_object_info_filter_by_tags_and_kind(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", tags=["stone"], kind="wall")
    assert res["count"] == 1
    assert res["objects"][0]["mcp_id"] == "wall_n"


def test_object_info_empty_result(monkeypatch):
    _patch_summarizer(monkeypatch, objects=[])
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="empty")
    assert res["success"] is True
    assert res["count"] == 0
    assert res["warnings"]


def test_object_info_no_matching_filter(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", mcp_id="nonexistent")
    assert res["success"] is True
    assert res["count"] == 0


def test_object_info_includes_transform(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", mcp_id="torch_01")
    obj = res["objects"][0]
    assert "transform" in obj
    assert obj["transform"]["location"] == [100, 200, 50]


def test_object_info_includes_tags_and_kind(monkeypatch):
    _patch_summarizer(monkeypatch)
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_object_info(scene_id="test", mcp_id="wall_n")
    obj = res["objects"][0]
    assert obj["kind"] == "wall"
    assert "stone" in obj["tags"]


def test_object_info_enriches_with_ue_data(monkeypatch):
    """When UE is connected, scene_object_info should enrich with live data."""
    _patch_summarizer(monkeypatch)
    mock_ue = MagicMock()
    mock_ue.send_command.return_value = {"success": True, "value": [100, 200, 50]}
    monkeypatch.setattr("server.core.get_unreal_connection", lambda: mock_ue)
    res = dt.scene_object_info(scene_id="test", mcp_id="torch_01")
    assert res["count"] == 1
    obj = res["objects"][0]
    assert "location" in obj


# --- scene_spatial_query ---


def test_spatial_query_missing_center_for_overlap():
    res = dt.scene_spatial_query(scene_id="test", query_type="overlap", center=None)
    assert res["success"] is False
    assert "center" in res["error"]["message"]


def test_spatial_query_missing_origin_for_raycast():
    res = dt.scene_spatial_query(scene_id="test", query_type="raycast", origin=None, direction={"x": 0, "y": 0, "z": -1})
    assert res["success"] is False
    assert "origin" in res["error"]["message"]


def test_spatial_query_missing_origin_for_linecast():
    res = dt.scene_spatial_query(scene_id="test", query_type="linecast", origin=None, end={"x": 0, "y": 0, "z": 0})
    assert res["success"] is False


def test_spatial_query_missing_reference_for_nearest():
    res = dt.scene_spatial_query(scene_id="test", query_type="nearest", reference_actor=None)
    assert res["success"] is False


def test_spatial_query_invalid_type():
    res = dt.scene_spatial_query(scene_id="test", query_type="teleport")
    assert res["success"] is False
    assert "invalid_query_type" in res["error"]["code"]


def test_spatial_query_overlap_delegates_to_ue(monkeypatch):
    """Overlap query should send spatial_overlap_sphere to UE."""
    mock_ue = MagicMock()
    mock_ue.send_command.return_value = {
        "success": True,
        "hits": [
            {"mcp_id": "torch_01", "distance": 50.0, "hit_point": [100, 200, 50]},
        ],
    }
    monkeypatch.setattr("server.core.get_unreal_connection", lambda: mock_ue)

    res = dt.scene_spatial_query(
        scene_id="test", query_type="overlap",
        center={"x": 100, "y": 200, "z": 50}, radius=100,
    )
    assert res["success"] is True
    assert res["count"] == 1
    assert res["hits"][0]["mcp_id"] == "torch_01"
    mock_ue.send_command.assert_called_once_with("spatial_overlap_sphere", ANY)


def test_spatial_query_raycast_delegates_to_ue(monkeypatch):
    mock_ue = MagicMock()
    mock_ue.send_command.return_value = {
        "success": True,
        "hits": [
            {"mcp_id": "wall_n", "distance": 500.0, "hit_point": [200, 0, 0], "hit_normal": [0, 1, 0]},
        ],
    }
    monkeypatch.setattr("server.core.get_unreal_connection", lambda: mock_ue)

    res = dt.scene_spatial_query(
        scene_id="test", query_type="raycast",
        origin={"x": 0, "y": 0, "z": 0}, direction={"x": 1, "y": 0, "z": 0},
    )
    assert res["success"] is True
    assert res["hits"][0]["hit_normal"] == [0, 1, 0]
    mock_ue.send_command.assert_called_once_with("spatial_raycast", ANY)


def test_spatial_query_linecast_delegates_to_ue(monkeypatch):
    mock_ue = MagicMock()
    mock_ue.send_command.return_value = {
        "success": True,
        "hits": [
            {"mcp_id": "torch_01", "distance": 150.0, "hit_point": [100, 200, 50]},
            {"mcp_id": "wall_n", "distance": 500.0, "hit_point": [200, 0, 0]},
        ],
    }
    monkeypatch.setattr("server.core.get_unreal_connection", lambda: mock_ue)

    res = dt.scene_spatial_query(
        scene_id="test", query_type="linecast",
        origin={"x": 0, "y": 0, "z": 0}, end={"x": 200, "y": 0, "z": 0},
    )
    assert res["success"] is True
    assert res["count"] == 2
    mock_ue.send_command.assert_called_once_with("spatial_linecast", ANY)


def test_spatial_query_nearest_delegates_to_ue(monkeypatch):
    mock_ue = MagicMock()
    mock_ue.send_command.return_value = {
        "success": True,
        "hits": [
            {"mcp_id": "torch_01", "distance": 80.0},
        ],
    }
    monkeypatch.setattr("server.core.get_unreal_connection", lambda: mock_ue)

    res = dt.scene_spatial_query(
        scene_id="test", query_type="nearest",
        reference_actor="torch_02",
    )
    assert res["success"] is True
    assert res["count"] == 1
    mock_ue.send_command.assert_called_once_with("spatial_nearest", ANY)


def test_spatial_query_no_ue_connection(monkeypatch):
    monkeypatch.setattr("server.core.get_unreal_connection", _no_ue)
    res = dt.scene_spatial_query(
        scene_id="test", query_type="overlap",
        center={"x": 0, "y": 0, "z": 0}, radius=100,
    )
    assert res["success"] is False
    assert "no_unreal_connection" in res["error"]["code"]
