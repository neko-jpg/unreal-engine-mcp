"""L1 unit tests for source_control_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.source_control_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_register_git_provider_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.register_git_provider("repo_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "register_git_provider"


def test_register_perforce_provider_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.register_perforce_provider("server_v", "user_v", "workspace_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "register_perforce_provider"


def test_source_control_checkout_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_checkout([])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_checkout"


def test_source_control_checkin_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_checkin([])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_checkin"


def test_source_control_revert_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_revert([])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_revert"


def test_source_control_file_lock_acquire_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_file_lock_acquire([])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_file_lock_acquire"


def test_source_control_file_lock_release_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_file_lock_release([])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_file_lock_release"


def test_source_control_create_changelist_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_create_changelist()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_create_changelist"


def test_source_control_asset_diff_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_asset_diff("asset_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_asset_diff"


def test_source_control_blueprint_diff_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_blueprint_diff("blueprint_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_blueprint_diff"


def test_source_control_merge_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.source_control_merge("asset_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "source_control_merge"


def test_multi_user_editing_start_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.multi_user_editing_start()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "multi_user_editing_start"


def test_multi_user_session_join_payload():
    with patch("server.source_control_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.multi_user_session_join("session_url_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "multi_user_session_join"
