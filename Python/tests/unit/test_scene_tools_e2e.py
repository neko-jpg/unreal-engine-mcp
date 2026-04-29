"""E2E tests for scene_create_wall and scene_create_pyramid via SceneDbActorSink.

These tests mock call_scene_syncd to verify that the SceneDbActorSink
flush path produces correct API payloads.
"""

import pytest
from unittest.mock import patch, MagicMock

from server.actor_sink import SceneDbActorSink
from server.scene_tools import scene_create_wall, scene_create_pyramid
from server.specs.actor_spec import ActorSpec


def _make_syncd_mock():
    """Create a mock that captures the payload before the buffer is cleared."""
    captured = {}

    def mock_call(path, payload):
        # Deep copy the objects list since SceneDbActorSink clears buffer after flush
        import copy
        captured["path"] = path
        captured["payload"] = copy.deepcopy(payload)
        return {"success": True, "data": {"upserted_count": len(payload.get("objects", [])), "error_count": 0}}

    return captured, mock_call


@pytest.fixture(autouse=True)
def _reset_singletons():
    import server.core as core_mod
    import helpers.actor_name_manager as anm
    with core_mod._connection_lock:
        core_mod._unreal_connection = None
    anm.clear_actor_cache()
    yield
    with core_mod._connection_lock:
        core_mod._unreal_connection = None
    anm.clear_actor_cache()


class TestSceneCreateWallE2E:
    def test_flush_sends_bulk_upsert_with_correct_scene(self):
        captured, mock_fn = _make_syncd_mock()
        with patch("server.scene_client.call_scene_syncd", side_effect=mock_fn):
            result = scene_create_wall(
                scene_id="test_scene",
                group_id="my_wall",
                segments=5,
                length=500.0,
                height=200.0,
            )
            assert result["success"] is True
        assert captured["path"] == "/objects/bulk-upsert"
        assert captured["payload"]["scene_id"] == "test_scene"
        assert captured["payload"]["group_id"] == "my_wall"
        assert len(captured["payload"]["objects"]) == 5

    def test_each_object_has_group_id(self):
        captured, mock_fn = _make_syncd_mock()
        with patch("server.scene_client.call_scene_syncd", side_effect=mock_fn):
            scene_create_wall(scene_id="s1", group_id="wall_a", segments=3)
        for obj in captured["payload"]["objects"]:
            assert obj["group_id"] == "wall_a"

    def test_transform_values_are_correct(self):
        captured, mock_fn = _make_syncd_mock()
        with patch("server.scene_client.call_scene_syncd", side_effect=mock_fn):
            scene_create_wall(
                scene_id="s1",
                group_id="w1",
                start={"x": 100.0, "y": 200.0, "z": 0.0},
                length=500.0,
                height=300.0,
                thickness=50.0,
                segments=1,
                axis="x",
            )
        obj = captured["payload"]["objects"][0]
        loc = obj["transform"]["location"]
        assert loc["x"] == pytest.approx(100.0)
        assert loc["z"] == pytest.approx(150.0)  # height/2

    def test_rejects_zero_segments(self):
        result = scene_create_wall(segments=0)
        assert result["success"] is False

    def test_rejects_invalid_axis(self):
        result = scene_create_wall(axis="z")
        assert result["success"] is False


class TestSceneCreatePyramidE2E:
    def test_flush_sends_bulk_upsert_with_correct_scene(self):
        captured, mock_fn = _make_syncd_mock()
        with patch("server.scene_client.call_scene_syncd", side_effect=mock_fn):
            result = scene_create_pyramid(
                scene_id="pyr_scene",
                group_id="pyr_01",
                levels=2,
            )
            assert result["success"] is True
        assert captured["path"] == "/objects/bulk-upsert"
        assert captured["payload"]["scene_id"] == "pyr_scene"
        assert captured["payload"]["group_id"] == "pyr_01"
        # 2 levels: level 0 = 2x2=4 blocks, level 1 = 1x1=1 block = 5 total
        assert len(captured["payload"]["objects"]) == 5

    def test_each_object_has_group_id_and_tags(self):
        captured, mock_fn = _make_syncd_mock()
        with patch("server.scene_client.call_scene_syncd", side_effect=mock_fn):
            scene_create_pyramid(scene_id="s1", group_id="pyr_a", levels=1)
        obj = captured["payload"]["objects"][0]
        assert obj["group_id"] == "pyr_a"
        assert "scene_pyramid" in obj["tags"]

    def test_rejects_zero_levels(self):
        result = scene_create_pyramid(levels=0)
        assert result["success"] is False

    def test_rejects_negative_block_size(self):
        result = scene_create_pyramid(block_size=-1)
        assert result["success"] is False


class TestSceneDbActorSink:
    def test_flush_chunks_large_bulk_upserts(self):
        calls = []

        def mock_call(path, payload):
            calls.append((path, payload))
            return {
                "success": True,
                "data": {
                    "upserted_count": len(payload["objects"]),
                    "error_count": 0,
                },
            }

        sink = SceneDbActorSink(scene_id="large_scene", group_id="large_group")
        for index in range(SceneDbActorSink.MAX_BULK_UPSERT_SIZE + 1):
            sink.spawn(ActorSpec(
                mcp_id=f"actor_{index}",
                desired_name=f"actor_{index}",
                actor_type="StaticMeshActor",
                asset_ref={"path": "/Engine/BasicShapes/Cube.Cube"},
                transform={
                    "location": {"x": float(index), "y": 0.0, "z": 0.0},
                    "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
            ))

        with patch("server.scene_client.call_scene_syncd", side_effect=mock_call):
            result = sink.flush()

        assert result["success"] is True
        assert result["generated_count"] == SceneDbActorSink.MAX_BULK_UPSERT_SIZE + 1
        assert result["upserted_count"] == SceneDbActorSink.MAX_BULK_UPSERT_SIZE + 1
        assert len(calls) == 2
        assert len(calls[0][1]["objects"]) == SceneDbActorSink.MAX_BULK_UPSERT_SIZE
        assert len(calls[1][1]["objects"]) == 1
