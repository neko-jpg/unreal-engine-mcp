"""L1 unit tests for mobile_xr_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.mobile_xr_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_configure_android_settings_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_android_settings()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_android_settings"


def test_configure_ios_settings_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ios_settings()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ios_settings"


def test_configure_mobile_rendering_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_mobile_rendering()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_mobile_rendering"


def test_configure_touch_input_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_touch_input()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_touch_input"


def test_set_device_profile_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_device_profile()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_device_profile"


def test_create_scalability_profile_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_scalability_profile()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_scalability_profile"


def test_enable_xr_plugin_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.enable_xr_plugin()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "enable_xr_plugin"


def test_configure_openxr_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_openxr()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_openxr"


def test_spawn_vr_pawn_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_vr_pawn()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_vr_pawn"


def test_configure_motion_controller_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_motion_controller("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_motion_controller"


def test_configure_hmd_camera_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_hmd_camera("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_hmd_camera"


def test_configure_ar_session_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ar_session()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ar_session"


def test_configure_ar_plane_detection_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ar_plane_detection()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ar_plane_detection"


def test_platform_specific_packaging_payload():
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.platform_specific_packaging()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "platform_specific_packaging"
