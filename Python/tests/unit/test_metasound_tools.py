"""L1 unit tests for metasound_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.metasound_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_edit_sound_cue_graph_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_sound_cue_graph("sound_cue_path_v", "node_type_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_sound_cue_graph"


def test_create_metasound_source_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_metasound_source()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_metasound_source"


def test_create_metasound_patch_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_metasound_patch()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_metasound_patch"


def test_add_metasound_graph_node_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_metasound_graph_node("asset_path_v", "node_type_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_metasound_graph_node"


def test_set_metasound_parameter_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_metasound_parameter("actor_name_v", "parameter_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_metasound_parameter"


def test_bind_footstep_audio_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.bind_footstep_audio("anim_sequence_path_v", "sound_cue_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "bind_footstep_audio"


def test_configure_ui_sound_payload():
    with patch("server.metasound_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ui_sound("widget_class_v", "sound_cue_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ui_sound"
