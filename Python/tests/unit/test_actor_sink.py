"""Tests for the ActorSink abstraction."""

import pytest
from unittest.mock import patch, MagicMock
from server.actor_sink import ActorSpec, DryRunActorSink, SceneDbActorSink, UnrealActorSink


def _make_spec(**overrides):
    defaults = dict(
        mcp_id="test_obj_001",
        desired_name="TestObject_001",
        actor_type="StaticMeshActor",
        asset_ref={"path": "/Engine/BasicShapes/Cube.Cube"},
        transform={
            "location": {"x": 100.0, "y": 200.0, "z": 50.0},
            "rotation": {"pitch": 0.0, "yaw": 90.0, "roll": 0.0},
            "scale": {"x": 1.0, "y": 2.0, "z": 3.0},
        },
        tags=["test"],
    )
    defaults.update(overrides)
    return ActorSpec(**defaults)


class TestActorSpec:
    def test_to_db_dict_includes_scene_id(self):
        spec = _make_spec()
        d = spec.to_db_dict("main")
        assert d["scene_id"] == "main"
        assert d["mcp_id"] == "test_obj_001"
        assert d["actor_type"] == "StaticMeshActor"
        assert d["transform"]["location"]["x"] == 100.0

    def test_to_db_dict_optional_fields(self):
        spec = _make_spec(group_id="wall_001", visual={"color": "red"})
        d = spec.to_db_dict("main")
        assert d["group_id"] == "wall_001"
        assert d["visual"] == {"color": "red"}

    def test_to_db_dict_omits_empty_optionals(self):
        spec = _make_spec()
        d = spec.to_db_dict("main")
        assert "group_id" not in d
        assert "visual" not in d
        assert "physics" not in d

    def test_to_unreal_dict_format(self):
        spec = _make_spec()
        d = spec.to_unreal_dict()
        assert d["name"] == "TestObject_001"
        assert d["type"] == "StaticMeshActor"
        assert d["location"] == [100.0, 200.0, 50.0]
        assert d["rotation"] == [0.0, 90.0, 0.0]
        assert d["scale"] == [1.0, 2.0, 3.0]
        assert d["static_mesh"] == "/Engine/BasicShapes/Cube.Cube"

    def test_to_unreal_dict_defaults(self):
        spec = ActorSpec(mcp_id="x", desired_name="y")
        d = spec.to_unreal_dict()
        assert d["location"] == [0.0, 0.0, 0.0]
        assert d["scale"] == [1.0, 1.0, 1.0]
        # Default asset_ref has the Cube path
        assert d["static_mesh"] == "/Engine/BasicShapes/Cube.Cube"


class TestDryRunActorSink:
    def test_spawn_records_spec(self):
        sink = DryRunActorSink()
        spec = _make_spec()
        result = sink.spawn(spec)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert len(sink.specs) == 1
        assert sink.specs[0].mcp_id == "test_obj_001"

    def test_flush_returns_specs(self):
        sink = DryRunActorSink()
        sink.spawn(_make_spec(mcp_id="a"))
        sink.spawn(_make_spec(mcp_id="b"))
        result = sink.flush()
        assert result["count"] == 2
        assert result["dry_run"] is True

    def test_delete_records_mcp_id(self):
        sink = DryRunActorSink()
        result = sink.delete("obj_42")
        assert result["success"] is True
        assert "obj_42" in sink.deletions

    def test_empty_flush(self):
        sink = DryRunActorSink()
        result = sink.flush()
        assert result["count"] == 0


class TestSceneDbActorSink:
    def test_spawn_buffers(self):
        sink = SceneDbActorSink(scene_id="main", group_id="wall_001")
        spec = _make_spec()
        result = sink.spawn(spec)
        assert result["buffered"] is True
        assert len(sink._buffer) == 1
        assert sink._buffer[0]["scene_id"] == "main"

    def test_buffered_dict_has_group_id(self):
        sink = SceneDbActorSink(scene_id="main", group_id="wall_001")
        sink.spawn(_make_spec(group_id="wall_001"))
        assert sink._buffer[0]["group_id"] == "wall_001"

    def test_empty_flush_no_call(self):
        sink = SceneDbActorSink(scene_id="main")
        result = sink.flush()
        assert result["upserted_count"] == 0


class TestActorSpecRoundTrip:
    def test_db_and_unreal_formats_are_consistent(self):
        spec = _make_spec()
        db = spec.to_db_dict("main")
        unreal = spec.to_unreal_dict()
        # Location values should match (just different format)
        db_loc = db["transform"]["location"]
        assert db_loc["x"] == unreal["location"][0]
        assert db_loc["y"] == unreal["location"][1]
        assert db_loc["z"] == unreal["location"][2]
        # Actor type == Unreal type
        assert db["actor_type"] == unreal["type"]
        # Asset path == static_mesh
        assert db["asset_ref"]["path"] == unreal["static_mesh"]


class TestUnrealActorSink:
    def test_spawn_calls_safe_spawn_actor(self):
        sink = UnrealActorSink()
        spec = _make_spec()
        mock_resp = {"status": "success", "name": "TestObject_001"}
        with patch("server.core.get_unreal_connection") as mock_conn, \
             patch("helpers.actor_name_manager.safe_spawn_actor", return_value=mock_resp) as mock_spawn:
            result = sink.spawn(spec)
            mock_spawn.assert_called_once()
            call_args = mock_spawn.call_args
            assert call_args[0][1]["name"] == "TestObject_001"
            assert call_args[0][1]["type"] == "StaticMeshActor"
            assert call_args[0][1]["location"] == [100.0, 200.0, 50.0]
            assert result == mock_resp

    def test_flush_returns_count(self):
        sink = UnrealActorSink()
        result = sink.flush()
        assert result["success"] is True
        assert result["count"] == 0

    def test_delete_calls_safe_delete_actor(self):
        sink = UnrealActorSink()
        mock_resp = {"status": "success"}
        with patch("server.core.get_unreal_connection") as mock_conn, \
             patch("helpers.actor_name_manager.safe_delete_actor", return_value=mock_resp) as mock_delete:
            result = sink.delete("obj_42")
            mock_delete.assert_called_once()
            assert result == mock_resp