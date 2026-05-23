"""L1 unit tests for chaos_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.chaos_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_collision_channel_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_collision_channel("channel_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_collision_channel"


def test_create_object_channel_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_object_channel("channel_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_object_channel"


def test_create_trace_channel_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_trace_channel("channel_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_trace_channel"


def test_create_geometry_collection_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_geometry_collection()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_geometry_collection"


def test_fracture_geometry_collection_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.fracture_geometry_collection("asset_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "fracture_geometry_collection"


def test_create_chaos_field_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_chaos_field()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_chaos_field"


def test_configure_chaos_solver_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_chaos_solver()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_chaos_solver"


def test_create_chaos_cache_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_chaos_cache()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_chaos_cache"


def test_create_chaos_vehicle_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_chaos_vehicle()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_chaos_vehicle"


def test_set_vehicle_wheel_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_vehicle_wheel("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_vehicle_wheel"


def test_set_vehicle_suspension_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_vehicle_suspension("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_vehicle_suspension"


def test_set_vehicle_engine_torque_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_vehicle_engine_torque("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_vehicle_engine_torque"


def test_set_cloth_settings_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_cloth_settings("skeletal_mesh_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_cloth_settings"


def test_create_chaos_cloth_asset_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_chaos_cloth_asset()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_chaos_cloth_asset"


def test_set_groom_physics_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_groom_physics("groom_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_groom_physics"


def test_set_ragdoll_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_ragdoll("skeletal_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_ragdoll"


def test_edit_physics_asset_body_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_physics_asset_body("physics_asset_path_v", "bone_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_physics_asset_body"


def test_edit_physics_asset_constraint_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_physics_asset_constraint("physics_asset_path_v", "constraint_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_physics_asset_constraint"


def test_attach_chaos_visual_debugger_payload():
    with patch("server.chaos_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.attach_chaos_visual_debugger()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "attach_chaos_visual_debugger"
