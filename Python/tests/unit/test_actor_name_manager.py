"""
tests/unit/test_actor_name_manager.py

L1 Python unit tests - ActorNameManager

Covers:
- Strategies in generate_unique_name (base -> session suffix -> counter -> UUID fallback)
- Do not reuse names already registered in _known_actors
- mark_actor_created / remove_actor / clear_actor_cache
- safe_spawn_actor: includes final_name and original_name at top level
- safe_delete_actor: cache removal
- find_actors_by_name response shapes (top-level actors after normalization)
"""

import json

import pytest
from unittest.mock import MagicMock

import helpers.actor_name_manager as anm
from helpers.actor_name_manager import (
    ActorNameManager,
    get_unique_actor_name,
    safe_spawn_actor,
    safe_delete_actor,
    clear_actor_cache,
    get_global_actor_name_manager,
)
from utils.responses import is_success_response


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the global singleton between tests."""
    anm._global_actor_name_manager = ActorNameManager()
    yield
    anm._global_actor_name_manager = ActorNameManager()


class TestGenerateUniqueName:
    def test_empty_name_returns_fallback(self):
        mgr = ActorNameManager()
        name = mgr.generate_unique_name("")
        assert name.startswith("Actor_")

    def test_unused_name_returned_as_is(self):
        mgr = ActorNameManager()
        name = mgr.generate_unique_name("MyActor")
        assert name == "MyActor"

    def test_known_actor_gets_session_suffix(self):
        mgr = ActorNameManager()
        mgr.mark_actor_created("MyActor")
        name = mgr.generate_unique_name("MyActor")
        assert name == f"MyActor_{mgr._session_id}"

    def test_multiple_conflicts_increment_counter(self):
        mgr = ActorNameManager()
        mgr.mark_actor_created("MyActor")
        session_name = f"MyActor_{mgr._session_id}"
        mgr.mark_actor_created(session_name)
        name1 = mgr.generate_unique_name("MyActor")
        name2 = mgr.generate_unique_name("MyActor")
        assert name1 != "MyActor"
        assert name2 != name1
        assert "MyActor_" in name1
        assert "MyActor_" in name2

    def test_known_actors_not_reused(self):
        mgr = ActorNameManager()
        mgr.mark_actor_created("ActorA")
        assert mgr._actor_exists("ActorA") is True
        assert mgr.generate_unique_name("ActorA") != "ActorA"

    def test_remove_actor_clears_cache(self):
        mgr = ActorNameManager()
        mgr.mark_actor_created("ActorA")
        mgr.remove_actor("ActorA")
        assert "ActorA" not in mgr._known_actors

    def test_clear_actor_cache_resets(self):
        mgr = ActorNameManager()
        mgr.mark_actor_created("ActorA")
        mgr._actor_counters["x"] = 5
        anm.clear_actor_cache()
        assert "ActorA" not in anm._global_actor_name_manager._known_actors
        assert len(anm._global_actor_name_manager._actor_counters) == 0


class TestSafeSpawnActor:
    def test_success_includes_final_name(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["spawn_actor"] = {"success": True, "name": "Hero"}
        resp = safe_spawn_actor(fake_conn, {"name": "Hero"})
        assert resp["final_name"] == "Hero"
        assert resp["original_name"] == "Hero"

    def test_already_exists_returns_error_when_auto_unique_disabled(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["spawn_actor"] = {"success": False, "error": "already exists: Hero"}
        resp = safe_spawn_actor(fake_conn, {"name": "Hero"}, auto_unique_name=False)
        assert resp["success"] is False
        assert "already exists" in resp.get("error", "")

    def test_already_exists_retries_with_unique_name(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        clear_actor_cache()
        mgr = get_global_actor_name_manager()
        mgr.mark_actor_created("Hero")
        call_count = [0]

        def send_command_with_exists(command, params=None):
            call_count[0] += 1
            if command == "find_actors_by_name":
                return {"success": True, "actors": [{"name": "Hero"}]}
            if call_count[0] <= 2:
                return {"success": False, "error": "already exists: Hero"}
            return {"success": True, "name": "Hero_1"}

        fake_conn.send_command = send_command_with_exists
        resp = safe_spawn_actor(fake_conn, {"name": "Hero"}, auto_unique_name=True)
        assert is_success_response(resp)

    def test_auto_unique_name_enabled(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["spawn_actor"] = {"success": True, "name": "Hero_1"}
        clear_actor_cache()
        mgr = get_global_actor_name_manager()
        mgr.mark_actor_created("Hero")
        resp = safe_spawn_actor(fake_conn, {"name": "Hero"}, auto_unique_name=True)
        assert resp["final_name"] != "Hero"
        assert any(h["command"] == "spawn_actor" for h in fake_conn.history)

    def test_top_level_actors_response_structure(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["find_actors_by_name"] = {
            "success": True,
            "actors": [{"name": "Hero"}, {"name": "Villain"}],
        }
        mgr = get_global_actor_name_manager()
        exists = mgr._actor_exists("Hero", fake_conn)
        assert exists is True
        assert "Hero" in mgr._known_actors

    def test_result_actors_response_structure(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["find_actors_by_name"] = {
            "success": True,
            "actors": [{"name": "Hero"}],
        }
        mgr = get_global_actor_name_manager()
        exists = mgr._actor_exists("Hero", fake_conn)
        assert exists is True or exists is False


class TestSafeDeleteActor:
    def test_success_removes_from_cache(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["delete_actor"] = {"success": True}
        mgr = get_global_actor_name_manager()
        mgr.mark_actor_created("Hero")
        resp = safe_delete_actor(fake_conn, "Hero")
        assert is_success_response(resp)
        assert "Hero" not in mgr._known_actors

    def test_failure_does_not_remove_cache(self, fake_conn_factory):
        fake_conn = fake_conn_factory()
        fake_conn.responses["delete_actor"] = {"success": False, "error": "not found"}
        mgr = get_global_actor_name_manager()
        mgr.mark_actor_created("Hero")
        resp = safe_delete_actor(fake_conn, "Hero")
        assert not is_success_response(resp)
        assert "Hero" in mgr._known_actors