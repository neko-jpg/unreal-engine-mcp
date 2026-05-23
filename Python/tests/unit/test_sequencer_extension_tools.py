"""L1 unit tests for sequencer_extension_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.sequencer_extension_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_spawn_camera_rail_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_camera_rail()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_camera_rail"


def test_spawn_camera_crane_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_camera_crane()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_camera_crane"


def test_sequencer_render_preview_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.sequencer_render_preview("level_sequence_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "sequencer_render_preview"


def test_register_take_recorder_source_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.register_take_recorder_source()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "register_take_recorder_source"


def test_add_control_rig_track_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_control_rig_track("level_sequence_path_v", "binding_id_v", "control_rig_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_control_rig_track"


def test_spawn_level_sequence_actor_payload():
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_level_sequence_actor("level_sequence_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_level_sequence_actor"
