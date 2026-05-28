"""L3 E2E tests for Lighting / Atmosphere MCP tools.

Requires live Unreal Editor + MCP server.
Tests the full stack: Python tool -> TCP -> C++ handler -> UE5 actor modification.
"""

import time

import pytest

pytestmark = [pytest.mark.e2e]


def _spawn_actor(unreal, actor_type, base_name, **kwargs):
    """Spawn an actor and return the actual name used by Unreal."""
    name = f"{base_name}_{time.time_ns()}"
    params = {"type": actor_type, "name": name}
    params.update(kwargs)
    result = unreal.send_command("spawn_actor", params)
    assert result["success"] is True, f"spawn_actor failed: {result}"
    # C++ may rename the actor; use the returned name if available.
    actual_name = result.get("name") or result.get("actor_name") or name
    return actual_name


@pytest.mark.requires_unreal
def test_spawn_and_configure_point_light(unreal):
    """Spawn a PointLight and configure all basic properties."""
    actor_name = _spawn_actor(unreal, "PointLight", "E2E_PointLight", location=[0, 0, 200])

    # Set intensity
    result = unreal.send_command("set_light_intensity", {"actor_name": actor_name, "intensity": 10000.0})
    assert result["success"] is True
    assert result["intensity"] == 10000.0

    # Set color
    result = unreal.send_command("set_light_color", {"actor_name": actor_name, "color": [1.0, 0.5, 0.0]})
    assert result["success"] is True

    # Set temperature
    result = unreal.send_command("set_light_temperature", {"actor_name": actor_name, "temperature": 3200.0, "enabled": True})
    assert result["success"] is True
    assert result["use_temperature"] is True

    # Set mobility
    result = unreal.send_command("set_light_mobility", {"actor_name": actor_name, "mobility": "Movable"})
    assert result["success"] is True
    assert result["mobility"] == "Movable"

    # Shadow on/off
    result = unreal.send_command("set_light_shadow_enabled", {"actor_name": actor_name, "enabled": False})
    assert result["success"] is True
    assert result["cast_shadows"] is False

    # Attenuation radius
    result = unreal.send_command("set_light_attenuation_radius", {"actor_name": actor_name, "radius": 3000.0})
    assert result["success"] is True
    assert result["attenuation_radius"] == 3000.0

    # Source radius
    result = unreal.send_command("set_light_source_radius", {"actor_name": actor_name, "radius": 10.0, "soft_radius": 5.0})
    assert result["success"] is True

    # Cleanup
    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_spawn_and_configure_spot_light(unreal):
    """Spawn a SpotLight and set cone angles."""
    actor_name = _spawn_actor(unreal, "SpotLight", "E2E_SpotLight", location=[0, 0, 300])

    result = unreal.send_command("set_light_cone_angles", {"actor_name": actor_name, "inner": 15.0, "outer": 35.0})
    assert result["success"] is True
    assert result["inner_cone_angle"] == 15.0
    assert result["outer_cone_angle"] == 35.0

    result = unreal.send_command("set_light_volumetric_scattering", {"actor_name": actor_name, "enabled": True, "intensity": 1.5})
    assert result["success"] is True

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_spawn_and_configure_rect_light(unreal):
    """Spawn a RectLight and set rect-specific properties."""
    actor_name = _spawn_actor(unreal, "RectLight", "E2E_RectLight", location=[0, 0, 250])

    result = unreal.send_command("set_rect_light_properties", {
        "actor_name": actor_name,
        "source_width": 128.0,
        "source_height": 64.0,
        "barn_door_angle": 45.0,
        "barn_door_length": 10.0
    })
    assert result["success"] is True
    assert result["source_width"] == 128.0
    assert result["source_height"] == 64.0

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_spawn_and_configure_sky_light(unreal):
    """Spawn a SkyLight and set properties."""
    actor_name = _spawn_actor(unreal, "SkyLight", "E2E_SkyLight", location=[0, 0, 0])

    result = unreal.send_command("set_sky_light_properties", {
        "actor_name": actor_name,
        "intensity": 2.0
    })
    assert result["success"] is True
    assert result["intensity"] == 2.0

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_spawn_and_configure_sky_atmosphere(unreal):
    """Spawn a SkyAtmosphere and set properties."""
    actor_name = _spawn_actor(unreal, "SkyAtmosphere", "E2E_SkyAtmosphere", location=[0, 0, 0])

    result = unreal.send_command("set_sky_atmosphere_properties", {
        "actor_name": actor_name,
        "ground_radius": 6360.0,
        "atmosphere_height": 100.0
    })
    assert result["success"] is True

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_spawn_and_configure_height_fog(unreal):
    """Spawn an ExponentialHeightFog and configure it."""
    actor_name = _spawn_actor(unreal, "ExponentialHeightFog", "E2E_Fog", location=[0, 0, 0])

    result = unreal.send_command("set_height_fog_properties", {
        "actor_name": actor_name,
        "fog_density": 0.02,
        "fog_height_falloff": 0.1,
        "fog_max_opacity": 0.8
    })
    assert result["success"] is True

    result = unreal.send_command("set_volumetric_fog", {"actor_name": actor_name, "enabled": True})
    assert result["success"] is True
    assert result["volumetric_fog_enabled"] is True

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_directional_light_as_sun(unreal):
    """Spawn a DirectionalLight, tag it as sun, and set sun position."""
    actor_name = _spawn_actor(unreal, "DirectionalLight", "E2E_Sun", location=[0, 0, 500], rotation=[-45, 0, 0])

    result = unreal.send_command("set_directional_light_as_sun", {"actor_name": actor_name, "is_sun": True})
    assert result["success"] is True
    assert result["is_sun"] is True

    result = unreal.send_command("set_sun_position", {"actor_name": actor_name, "azimuth": 90.0, "zenith": 30.0})
    assert result["success"] is True

    unreal.send_command("delete_actor", {"name": actor_name})


@pytest.mark.requires_unreal
def test_create_reflection_capture(unreal):
    """Create a sphere reflection capture."""
    result = unreal.send_command("create_reflection_capture", {
        "actor_name": "E2E_RC",
        "type": "Sphere",
        "location": [0, 0, 100],
        "radius": 800.0,
        "brightness": 1.5
    })
    assert result["success"] is True
    assert result["actor_name"] == "E2E_RC"
    assert result["type"] == "Sphere"

    unreal.send_command("delete_actor", {"name": "E2E_RC"})


@pytest.mark.requires_unreal
def test_create_lightmass_importance_volume(unreal):
    """Create a Lightmass Importance Volume."""
    result = unreal.send_command("create_lightmass_importance_volume", {
        "location": [0, 0, 0],
        "extent": [2000, 2000, 500]
    })
    assert result["success"] is True
    assert result["class"] == "LightmassImportanceVolume"

    # Cleanup
    unreal.send_command("delete_actor", {"name": result["actor_name"]})


@pytest.mark.requires_unreal
def test_build_lighting_preview(unreal):
    """Trigger a preview lighting build."""
    result = unreal.send_command("build_lighting", {"quality": "Preview"})
    assert result["success"] is True
    assert result["quality"] == "Preview"
    assert "message" in result
