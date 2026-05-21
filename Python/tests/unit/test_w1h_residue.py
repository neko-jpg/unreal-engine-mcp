"""L1 unit tests for W1-H Component Replicates + AudioVolume + DialogueWave +
SourceControl + Stat convenience wrappers."""

from unittest.mock import patch, MagicMock

import server.actor_tools as actor_tools
import server.audio_tools as audio_tools
import server.validation_tools as validation_tools


def _mock_conn(payload=None):
    m = MagicMock()
    m.send_command.return_value = payload if payload is not None else {"success": True}
    return m


class TestSetComponentReplicates:
    def test_default_true(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_component_replicates("MyActor", "StaticMeshComponent")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "set_component_replicates"
        assert args[0][1] == {
            "actor_name": "MyActor",
            "component_name": "StaticMeshComponent",
            "replicates": True,
        }

    def test_explicit_false(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_component_replicates("MyActor", "Health", replicates=False)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["replicates"] is False

    def test_rejects_empty_actor(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()):
            r = actor_tools.set_component_replicates("", "X")
        assert r.get("success") is False

    def test_rejects_empty_component(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()):
            r = actor_tools.set_component_replicates("A", "")
        assert r.get("success") is False


class TestSpawnAudioVolume:
    def test_minimal(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.spawn_audio_volume("AV01")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["name"] == "AV01"
        assert payload["priority"] == 0.0
        assert payload["enabled"] is True
        assert "location" not in payload
        assert "scale" not in payload

    def test_full(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.spawn_audio_volume(
                "AV01",
                location=[0, 0, 200],
                scale=[2, 2, 1],
                priority=5.0,
                enabled=False,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["location"] == [0, 0, 200]
        assert payload["scale"] == [2, 2, 1]
        assert payload["priority"] == 5.0
        assert payload["enabled"] is False

    def test_rejects_empty(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()):
            r = audio_tools.spawn_audio_volume("")
        assert r.get("success") is False


class TestCreateDialogueWave:
    def test_minimal(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.create_dialogue_wave("/Game/Loc/Dialogue/D_Hello")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"asset_path": "/Game/Loc/Dialogue/D_Hello"}

    def test_with_text(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            audio_tools.create_dialogue_wave("/Game/Loc/Dialogue/D_Hello", spoken_text="Hello, world!")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["spoken_text"] == "Hello, world!"

    def test_rejects_non_string_spoken(self):
        with patch("server.audio_tools.get_unreal_connection", return_value=_mock_conn()):
            r = audio_tools.create_dialogue_wave("/G/D", spoken_text=123)  # type: ignore[arg-type]
        assert r.get("success") is False


class TestGetSourceControlStatus:
    def test_empty_payload(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.get_source_control_status()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "get_source_control_status"
        assert args[0][1] == {}


class TestStatWrappers:
    def test_get_fps_returns_filtered_fields(self):
        mock_conn = _mock_conn({
            "success": True,
            "fps": 60.5,
            "delta_seconds": 0.0165,
            "memory": {"used_physical_mb": 4000.0},  # should not appear in output
        })
        with patch("server.validation_tools.get_unreal_connection", return_value=mock_conn) as mock_ue:
            r = validation_tools.get_fps()
        assert r["fps"] == 60.5
        assert r["delta_seconds"] == 0.0165
        assert "memory" not in r
        # And the underlying command is get_editor_stats
        assert mock_ue.return_value.send_command.call_args[0][0] == "get_editor_stats"
        assert mock_ue.return_value.send_command.call_args[0][1] == {}

    def test_stat_unit_routes_to_editor_stats(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.get_stat_unit()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "get_editor_stats"
        assert args[0][1] == {"stat_command": "stat unit"}

    def test_stat_gpu_routes_to_editor_stats(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.get_stat_gpu()
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"stat_command": "stat gpu"}
