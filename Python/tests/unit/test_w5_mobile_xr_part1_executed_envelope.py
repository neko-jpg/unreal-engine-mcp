"""W5 executed-envelope tests for Mobile/XR part 1 handlers (issue #100)."""
from unittest.mock import patch, MagicMock
import pytest
import server.mobile_xr_tools as m
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


XR_COMMANDS = [
    ("configure_android_settings", lambda: m.configure_android_settings("com.test.app", 26)),
    ("configure_ios_settings", lambda: m.configure_ios_settings("com.test.app", "15.0")),
    ("configure_mobile_rendering", lambda: m.configure_mobile_rendering("ES3_1", True)),
    ("configure_touch_input", lambda: m.configure_touch_input(True, False)),
    ("set_device_profile", lambda: m.set_device_profile("Android_High")),
    ("create_scalability_profile", lambda: m.create_scalability_profile("High")),
    ("enable_xr_plugin", lambda: m.enable_xr_plugin("OpenXR")),
    ("configure_openxr", lambda: m.configure_openxr("Stereo")),
]


@pytest.mark.parametrize("command,call", XR_COMMANDS)
def test_xr_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", XR_COMMANDS)
def test_xr_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
