"""E2E tests for Water System MCP tools.

Requires live Unreal Editor + Water plugin enabled.
Tests the full stack: Python tool -> TCP -> C++ handler -> UE5 Water Body actor.
"""

import uuid

import pytest

pytestmark = [pytest.mark.e2e]


def _unique_name(base: str) -> str:
    """Generate a short unique actor name to avoid collisions."""
    return f"M{base}{uuid.uuid4().hex[:6]}"


def _delete_actor(unreal, actor_name: str) -> None:
    """Best-effort actor cleanup; ignore failures."""
    try:
        unreal.send_command("delete_actor", {"name": actor_name})
    except Exception:
        pass


def _cleanup_water_actors(unreal) -> None:
    """Delete auto-spawned Water plugin actors that may leak between tests."""
    for name in ["WaterBrushManager", "WaterZone"]:
        try:
            unreal.send_command("delete_actor", {"name": name})
        except Exception:
            pass


@pytest.mark.requires_unreal
def test_spawn_water_body_ocean(unreal):
    """Spawn a WaterBodyOcean actor in the level."""
    actor_name = _unique_name("Oc")
    try:
        result = unreal.send_command("spawn_water_body_ocean", {
            "actor_name": actor_name,
            "scale": 2.0,
        })
        assert result.get("success") is True, f"spawn_water_body_ocean failed: {result}"
    finally:
        _delete_actor(unreal, actor_name)
        _cleanup_water_actors(unreal)


@pytest.mark.requires_unreal
def test_spawn_water_body_lake(unreal):
    """Spawn a WaterBodyLake actor with spline points."""
    actor_name = _unique_name("Lk")
    try:
        result = unreal.send_command("spawn_water_body_lake", {
            "actor_name": actor_name,
            "spline_points": [
                {"x": 0, "y": 0, "z": 0},
                {"x": 1000, "y": 0, "z": 0},
                {"x": 1000, "y": 1000, "z": 0},
                {"x": 0, "y": 1000, "z": 0},
            ],
        })
        assert result.get("success") is True, f"spawn_water_body_lake failed: {result}"
    finally:
        _delete_actor(unreal, actor_name)
        _cleanup_water_actors(unreal)


@pytest.mark.requires_unreal
def test_spawn_water_body_river(unreal):
    """Spawn a WaterBodyRiver actor with spline points."""
    actor_name = _unique_name("Rv")
    try:
        result = unreal.send_command("spawn_water_body_river", {
            "actor_name": actor_name,
            "spline_points": [
                {"x": -500, "y": -500, "z": 50},
                {"x": 0, "y": 0, "z": 40},
                {"x": 500, "y": 500, "z": 30},
            ],
        })
        assert result.get("success") is True, f"spawn_water_body_river failed: {result}"
    finally:
        _delete_actor(unreal, actor_name)
        _cleanup_water_actors(unreal)


@pytest.mark.requires_unreal
def test_configure_water_wave(unreal):
    """Configure wave settings on an existing water body."""
    actor_name = _unique_name("Wv")
    try:
        spawn = unreal.send_command("spawn_water_body_ocean", {
            "actor_name": actor_name,
            "scale": 1.0,
        })
        assert spawn.get("success") is True, f"spawn failed: {spawn}"

        result = unreal.send_command("configure_water_wave", {
            "actor_name": actor_name,
            "asset_path": "/Water/WaveProfiles/Blueprints/WaveProfile_Ocean.WaveProfile_Ocean",
        })
        assert result.get("success") is True, f"configure_water_wave failed: {result}"
    finally:
        _delete_actor(unreal, actor_name)
        _cleanup_water_actors(unreal)


@pytest.mark.requires_unreal
def test_configure_water_flow(unreal):
    """Configure flow velocity on a river water body."""
    actor_name = _unique_name("Fl")
    try:
        spawn = unreal.send_command("spawn_water_body_river", {
            "actor_name": actor_name,
            "spline_points": [
                {"x": 0, "y": 0, "z": 10},
                {"x": 200, "y": 0, "z": 10},
                {"x": 400, "y": 0, "z": 10},
            ],
        })
        assert spawn.get("success") is True, f"spawn failed: {spawn}"

        result = unreal.send_command("configure_water_flow", {
            "actor_name": actor_name,
            "flow_velocity": 150.0,
        })
        assert result.get("success") is True, f"configure_water_flow failed: {result}"
    finally:
        _delete_actor(unreal, actor_name)
        _cleanup_water_actors(unreal)
