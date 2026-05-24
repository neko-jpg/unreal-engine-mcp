"""W5 executed-envelope tests for Testing/Validation part 2 handlers (issue #101)."""
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


TESTING_PART2_COMMANDS = [
    ("run_python_unit_test", lambda: m.run_python_unit_test("Python/tests/unit")),
    ("run_rust_test", lambda: m.run_rust_test("")),
]


@pytest.mark.parametrize("command,call", TESTING_PART2_COMMANDS)
def test_testing_part2_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", TESTING_PART2_COMMANDS)
def test_testing_part2_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
