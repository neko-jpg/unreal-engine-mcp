"""L1 unit tests for enable_blueprint_profiler / disable_blueprint_profiler (issue #40)."""

from unittest.mock import patch, MagicMock

import server.validation_tools as validation_tools


def _conn_with_responses(payloads):
    m = MagicMock()
    m.send_command.side_effect = payloads
    return m


class TestEnableBlueprintProfiler:
    def test_calls_insights_then_stat_scriptvm(self):
        m = _conn_with_responses([
            {"success": True, "file": "/tmp/x.utrace"},
            {"success": True, "stat_command": "stat ScriptVM"},
        ])
        with patch(
            "server.validation_tools.get_unreal_connection",
            return_value=m,
        ):
            res = validation_tools.enable_blueprint_profiler()
        calls = [c.args for c in m.send_command.call_args_list]
        assert calls[0][0] == "start_unreal_insights_trace"
        assert "bp" in calls[0][1]["channels"]
        assert calls[1] == ("get_editor_stats", {"stat_command": "stat ScriptVM"})
        assert res["success"] is True
        assert "stat_scriptvm" in res
        assert "trace" in res

    def test_file_parameter_is_forwarded(self):
        m = _conn_with_responses([
            {"success": True},
            {"success": True},
        ])
        with patch(
            "server.validation_tools.get_unreal_connection",
            return_value=m,
        ):
            validation_tools.enable_blueprint_profiler(file="C:/tmp/bp.utrace")
        first_call = m.send_command.call_args_list[0].args
        assert first_call[1]["file"] == "C:/tmp/bp.utrace"

    def test_failed_connection_returns_error(self):
        with patch(
            "server.validation_tools.get_unreal_connection",
            return_value=None,
        ):
            res = validation_tools.enable_blueprint_profiler()
        assert res["success"] is False


class TestDisableBlueprintProfiler:
    def test_calls_stop_then_clear(self):
        m = _conn_with_responses([
            {"success": True, "stopped": True},
            {"success": True},
        ])
        with patch(
            "server.validation_tools.get_unreal_connection",
            return_value=m,
        ):
            res = validation_tools.disable_blueprint_profiler()
        calls = [c.args for c in m.send_command.call_args_list]
        assert calls[0][0] == "stop_unreal_insights_trace"
        assert calls[1] == ("get_editor_stats", {"stat_command": "stat ScriptVM"})
        assert res["success"] is True
