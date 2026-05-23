"""L1 unit tests for audio_tools W1-C SoundSubmix creation."""

from unittest.mock import patch, MagicMock

import server.audio_tools as audio_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestCreateSoundSubmix:
    def test_minimal(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.create_sound_submix("/Game/Audio/SM_MainMix")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"asset_path": "/Game/Audio/SM_MainMix"}

    def test_with_parent_and_volume(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.create_sound_submix(
                "/Game/Audio/SM_Music",
                parent_submix_path="/Game/Audio/SM_MainMix",
                output_volume_db=0.8,
                auto_disable=False,
                auto_disable_time=0.5,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["parent_submix_path"] == "/Game/Audio/SM_MainMix"
        assert payload["output_volume_db"] == 0.8
        assert payload["auto_disable"] is False
        assert payload["auto_disable_time"] == 0.5

    def test_rejects_negative_auto_disable_time(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()):
            r = audio_tools.create_sound_submix("/G/S", auto_disable_time=-0.1)
        assert r.get("success") is False

    def test_rejects_empty_path(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()):
            r = audio_tools.create_sound_submix("")
        assert r.get("success") is False
