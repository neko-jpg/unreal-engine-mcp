"""W5 executed-envelope tests for Testing/Validation part 1 handlers (issue #101)."""
from unittest.mock import patch, MagicMock
import pytest
import server.testing_validation_tools as m
from utils.envelope import assert_executed, assert_no_queued, EnvelopeAssertionError


def _conn_returning(payload):
    c = MagicMock()
    c.send_command.return_value = payload
    return c


def _executed_envelope(command, extra=None):
    data = {"executed": True, "command": command}
    if extra:
        data.update(extra)
    return {"success": True, "data": data}


TESTING_COMMANDS = [
    ("create_ue_automation_test", lambda: m.create_ue_automation_test("TestFoo", "Game")),
    ("spawn_functional_test_actor", lambda: m.spawn_functional_test_actor("FuncTest", "")),
    ("run_automation_test", lambda: m.run_automation_test("Game")),
    ("fetch_automation_test_results", lambda: m.fetch_automation_test_results("")),
    ("run_collision_validation", lambda: m.run_collision_validation("Level")),
    ("run_navigation_validation", lambda: m.run_navigation_validation("Level")),
    ("run_performance_budget_validation", lambda: m.run_performance_budget_validation(16.6, 16.6, 4096)),
    ("run_gameplay_screenshot_test", lambda: m.run_gameplay_screenshot_test("test_screenshot")),
]


@pytest.mark.parametrize("command,call", TESTING_COMMANDS)
def test_testing_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", TESTING_COMMANDS)
def test_testing_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
