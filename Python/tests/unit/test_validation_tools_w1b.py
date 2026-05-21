"""L1 unit tests for validation_tools W1-B residue."""

from unittest.mock import patch, MagicMock

import server.validation_tools as validation_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSetAutoSaveSettings:
    def test_single_field(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.set_auto_save_settings(auto_save_enable=True)
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "set_auto_save_settings"
        assert args[0][1] == {"auto_save_enable": True}

    def test_multiple_fields(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.set_auto_save_settings(
                auto_save_enable=True,
                auto_save_time_minutes=5,
                auto_save_warning_in_seconds=10,
                auto_save_content=True,
                auto_save_maps=False,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["auto_save_time_minutes"] == 5
        assert payload["auto_save_warning_in_seconds"] == 10
        assert payload["auto_save_content"] is True
        assert payload["auto_save_maps"] is False

    def test_rejects_no_fields(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = validation_tools.set_auto_save_settings()
        assert r.get("success") is False

    def test_rejects_invalid_minutes(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = validation_tools.set_auto_save_settings(auto_save_time_minutes=0)
        assert r.get("success") is False

    def test_rejects_negative_warning(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = validation_tools.set_auto_save_settings(auto_save_warning_in_seconds=-1)
        assert r.get("success") is False


class TestGetEditorStats:
    def test_no_args(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.get_editor_stats()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "get_editor_stats"
        assert args[0][1] == {}

    def test_with_stat_command(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.get_editor_stats(stat_command="stat unit")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["stat_command"] == "stat unit"


class TestStartInsightsTrace:
    def test_default_channels(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.start_unreal_insights_trace()
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert "cpu" in payload["channels"]
        assert "trace_file" not in payload

    def test_with_file(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.start_unreal_insights_trace(
                channels="cpu,gpu", trace_file="C:/tmp/t.utrace"
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["channels"] == "cpu,gpu"
        assert payload["trace_file"] == "C:/tmp/t.utrace"

    def test_rejects_empty_channels(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = validation_tools.start_unreal_insights_trace(channels="")
        assert r.get("success") is False


class TestStopInsightsTrace:
    def test_sends_empty_payload(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.stop_unreal_insights_trace()
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "stop_unreal_insights_trace"
        assert args[0][1] == {}


class TestValidateAssets:
    def test_defaults(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.validate_assets()
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"content_path": "/Game"}

    def test_with_limit(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            validation_tools.validate_assets(content_path="/Game/Maps", max_assets=50)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["content_path"] == "/Game/Maps"
        assert payload["max_assets"] == 50

    def test_rejects_negative_limit(self):
        with patch("server.validation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = validation_tools.validate_assets(max_assets=-1)
        assert r.get("success") is False
