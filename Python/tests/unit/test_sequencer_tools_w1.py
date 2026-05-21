"""L1 unit tests for sequencer_tools W1-4 residue (Visibility / Audio /
Animation / Material parameter / Keyframe delete / Keyframe interpolation /
Subsequence). Mocks the Unreal connection."""

from unittest.mock import patch, MagicMock

import server.sequencer_tools as sequencer_tools


def _mock_conn(success: bool = True):
    m = MagicMock()
    m.send_command.return_value = {"success": success}
    return m


class TestAddVisibilityTrack:
    def test_sends_required_params(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            r = sequencer_tools.add_visibility_track("/Game/X", "ABCD-1234")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "add_visibility_track"
        assert args[0][1] == {"sequence_path": "/Game/X", "binding_guid": "ABCD-1234"}
        assert r["success"] is True

    def test_rejects_empty_sequence_path(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_visibility_track("", "ABCD")
        assert r.get("success") is False

    def test_rejects_empty_binding_guid(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_visibility_track("/Game/X", "")
        assert r.get("success") is False


class TestAddAudioTrack:
    def test_minimal(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            r = sequencer_tools.add_audio_track("/Game/X")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "add_audio_track"
        payload = args[0][1]
        assert payload["sequence_path"] == "/Game/X"
        assert payload["start_frame"] == 0
        assert "sound_path" not in payload
        assert r["success"] is True

    def test_with_sound(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_audio_track("/Game/X", sound_path="/Game/Sounds/A", start_frame=60)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["sound_path"] == "/Game/Sounds/A"
        assert payload["start_frame"] == 60

    def test_rejects_empty_sequence_path(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_audio_track("")
        assert r.get("success") is False


class TestAddAnimationTrack:
    def test_minimal(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            r = sequencer_tools.add_animation_track("/Game/X", "ABCD-1234")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["binding_guid"] == "ABCD-1234"
        assert "anim_sequence_path" not in payload
        assert r["success"] is True

    def test_with_anim_path(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_animation_track(
                "/Game/X", "ABCD-1234", anim_sequence_path="/Game/Anim/Run", start_frame=30
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["anim_sequence_path"] == "/Game/Anim/Run"
        assert payload["start_frame"] == 30

    def test_rejects_empty_binding_guid(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_animation_track("/Game/X", "")
        assert r.get("success") is False


class TestAddMaterialParameterTrack:
    def test_default_index(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_material_parameter_track("/Game/X", "ABCD")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["material_index"] == 0

    def test_explicit_index(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_material_parameter_track("/Game/X", "ABCD", material_index=2)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["material_index"] == 2

    def test_rejects_negative_index(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_material_parameter_track("/Game/X", "ABCD", material_index=-1)
        assert r.get("success") is False


class TestDeleteKeyframe:
    def test_sends_required_params(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.delete_keyframe("/Game/X", "ABCD", frame=42)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "delete_keyframe"
        assert args[0][1]["frame"] == 42

    def test_rejects_empty_sequence_path(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.delete_keyframe("", "ABCD", frame=10)
        assert r.get("success") is False


class TestSetKeyframeInterpolation:
    def test_default_cubic(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.set_keyframe_interpolation("/Game/X", "ABCD")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["interpolation"] == "Cubic"

    def test_explicit_linear(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.set_keyframe_interpolation("/Game/X", "ABCD", interpolation="Linear")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["interpolation"] == "Linear"

    def test_rejects_unknown_mode(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.set_keyframe_interpolation("/Game/X", "ABCD", interpolation="Bezier")
        assert r.get("success") is False


class TestAddSubsequence:
    def test_minimal(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_subsequence("/Game/Outer", "/Game/Inner")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["sequence_path"] == "/Game/Outer"
        assert payload["inner_sequence_path"] == "/Game/Inner"
        assert payload["as_shot"] is False
        assert payload["duration_frames"] == 150

    def test_as_shot(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            sequencer_tools.add_subsequence("/Game/Outer", "/Game/Inner", start_frame=60, duration_frames=240, as_shot=True)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["as_shot"] is True
        assert payload["start_frame"] == 60
        assert payload["duration_frames"] == 240

    def test_rejects_zero_duration(self):
        with patch("server.sequencer_tools.get_unreal_connection", return_value=_mock_conn()):
            r = sequencer_tools.add_subsequence("/Game/Outer", "/Game/Inner", duration_frames=0)
        assert r.get("success") is False
