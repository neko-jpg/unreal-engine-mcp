"""L1 unit tests for water_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.water_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_enable_water_plugin_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.enable_water_plugin()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "enable_water_plugin"


def test_spawn_water_body_ocean_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_water_body_ocean()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_water_body_ocean"


def test_spawn_water_body_lake_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_water_body_lake()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_water_body_lake"


def test_spawn_water_body_river_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_water_body_river()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_water_body_river"


def test_spawn_water_body_custom_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_water_body_custom()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_water_body_custom"


def test_configure_river_spline_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_river_spline("actor_name_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_river_spline"


def test_set_water_material_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_water_material("actor_name_v", "material_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_water_material"


def test_configure_water_wave_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_water_wave("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_water_wave"


def test_configure_water_flow_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_water_flow("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_water_flow"


def test_configure_buoyancy_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_buoyancy("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_buoyancy"


def test_configure_water_mesh_actor_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_water_mesh_actor()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_water_mesh_actor"


def test_configure_underwater_post_process_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_underwater_post_process()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_underwater_post_process"


def test_configure_shoreline_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_shoreline("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_shoreline"


def test_configure_water_landscape_carving_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_water_landscape_carving("landscape_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_water_landscape_carving"


def test_attach_floating_actor_payload():
    with patch("server.water_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.attach_floating_actor("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "attach_floating_actor"
