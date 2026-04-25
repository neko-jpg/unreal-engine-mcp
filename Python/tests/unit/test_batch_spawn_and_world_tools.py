"""
tests/unit/test_batch_spawn_and_world_tools.py

Priority tests for batch_spawn_actors and world-building tool surface.
Covers:
- batch_spawn_actors dry-run acceptance
- batch_spawn_actors batch limit enforcement
- spawn_actor duplicate name error propagation
- create_pyramid / create_wall smoke tests (dry-run only)
- create_maze default parameters succeed
- Response format consistency via is_success_response
"""

import pytest
from unittest.mock import patch, MagicMock

import unreal_mcp_server_advanced as srv
from server.actor_tools import batch_spawn_actors
from server.validation import MAX_ACTORS_PER_BATCH, is_success_response
from tests.conftest import FakeUnrealConnection


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


class TestBatchSpawnActorsDryRun:
    def test_dry_run_accepts_valid_actor(self):
        result = batch_spawn_actors(
            [{"name": "TestActor", "type": "StaticMeshActor"}],
            dry_run=True,
        )
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["actor_count"] == 1

    def test_dry_run_rejects_empty_list(self):
        result = batch_spawn_actors([], dry_run=True)
        assert result["success"] is False

    def test_dry_run_rejects_non_list(self):
        result = batch_spawn_actors("not a list", dry_run=True)
        assert result["success"] is False

    def test_dry_run_rejects_non_dict_entry(self):
        result = batch_spawn_actors([42], dry_run=True)
        assert result["success"] is False

    def test_dry_run_rejects_missing_name(self):
        result = batch_spawn_actors([{"type": "StaticMeshActor"}], dry_run=True)
        assert result["success"] is False

    def test_dry_run_rejects_missing_type(self):
        result = batch_spawn_actors([{"name": "Test"}], dry_run=True)
        assert result["success"] is False


class TestBatchSpawnActorsLimit:
    def test_rejects_excess_actors(self):
        too_many = [{"name": f"A{i}", "type": "StaticMeshActor"} for i in range(MAX_ACTORS_PER_BATCH + 1)]
        result = batch_spawn_actors(too_many, dry_run=True)
        assert result["success"] is False
        assert "exceeds" in result.get("error", "").lower()

    def test_accepts_at_limit(self):
        at_limit = [{"name": f"A{i}", "type": "StaticMeshActor"} for i in range(MAX_ACTORS_PER_BATCH)]
        result = batch_spawn_actors(at_limit, dry_run=True)
        assert result["success"] is True


class TestSpawnActorDuplicateNameError:
    def test_duplicate_name_returns_error_when_auto_unique_disabled(self):
        fake_conn = FakeUnrealConnection()
        fake_conn.responses["spawn_actor"] = {
            "status": "error", "error": "Actor with name 'Cube' already exists"
        }
        from helpers.actor_name_manager import safe_spawn_actor
        result = safe_spawn_actor(fake_conn, {"name": "Cube"}, auto_unique_name=False)
        assert result.get("status") == "error" or result.get("success") is False


class TestCreatePyramidDryRun:
    def test_default_params_succeed(self):
        from server.world_building_tools import create_pyramid
        with patch("server.world_building_tools.get_unreal_connection"):
            result = create_pyramid(dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["actor_count"] > 0


class TestCreateWallDryRun:
    def test_default_params_succeed(self):
        from server.world_building_tools import create_wall
        with patch("server.world_building_tools.get_unreal_connection"):
            result = create_wall(dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["actor_count"] > 0


class TestCreateMazeDefaults:
    def test_default_params_do_not_exceed_batch_limit(self):
        from server.world_building_tools import create_maze
        with patch("server.world_building_tools.get_unreal_connection"):
            result = create_maze()
        assert result.get("success") is True or is_success_response(result)


class TestIsSuccessResponse:
    def test_recognizes_success_true(self):
        assert is_success_response({"success": True}) is True

    def test_recognizes_status_success(self):
        assert is_success_response({"status": "success"}) is True

    def test_rejects_success_false(self):
        assert is_success_response({"success": False}) is False

    def test_rejects_status_error(self):
        assert is_success_response({"status": "error"}) is False

    def test_rejects_empty_dict(self):
        assert is_success_response({}) is False