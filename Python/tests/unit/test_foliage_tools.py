"""L1 unit tests for foliage_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.foliage_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_foliage_type_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_foliage_type()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_foliage_type"


def test_register_static_mesh_foliage_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.register_static_mesh_foliage("foliage_type_path_v", "static_mesh_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "register_static_mesh_foliage"


def test_register_actor_foliage_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.register_actor_foliage("foliage_type_path_v", "actor_class_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "register_actor_foliage"


def test_foliage_paint_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.foliage_paint("foliage_type_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "foliage_paint"


def test_foliage_erase_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.foliage_erase("foliage_type_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "foliage_erase"


def test_set_foliage_density_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_density("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_density"


def test_set_foliage_scale_range_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_scale_range("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_scale_range"


def test_set_foliage_random_yaw_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_random_yaw("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_random_yaw"


def test_set_foliage_align_to_normal_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_align_to_normal("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_align_to_normal"


def test_set_foliage_cull_distance_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_cull_distance("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_cull_distance"


def test_set_foliage_lod_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_lod("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_lod"


def test_create_procedural_foliage_spawner_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_procedural_foliage_spawner()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_procedural_foliage_spawner"


def test_create_procedural_foliage_volume_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_procedural_foliage_volume()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_procedural_foliage_volume"


def test_set_procedural_foliage_seed_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_procedural_foliage_seed("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_procedural_foliage_seed"


def test_spawn_biome_foliage_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_biome_foliage("biome_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_biome_foliage"


def test_create_grass_type_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_grass_type()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_grass_type"


def test_bind_landscape_grass_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.bind_landscape_grass("landscape_actor_v", "grass_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "bind_landscape_grass"


def test_set_foliage_nanite_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_nanite("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_nanite"


def test_set_foliage_wind_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_foliage_wind("foliage_type_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_foliage_wind"


def test_configure_pivot_painter_payload():
    with patch("server.foliage_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pivot_painter("mesh_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pivot_painter"
