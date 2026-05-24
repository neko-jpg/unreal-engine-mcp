"""W5 executed-envelope tests for Mobile/XR part 2 handlers (issue #100)."""
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


XR_PART2_COMMANDS = [
    ("spawn_vr_pawn", lambda: m.spawn_vr_pawn("VRPawn", "")),
    ("configure_motion_controller", lambda: m.configure_motion_controller("VRPawn", "Right")),
    ("configure_hmd_camera", lambda: m.configure_hmd_camera("VRPawn")),
    ("configure_ar_session", lambda: m.configure_ar_session("Gravity")),
    ("configure_ar_plane_detection", lambda: m.configure_ar_plane_detection(True, False)),
    ("platform_specific_packaging", lambda: m.platform_specific_packaging("Android", "Shipping")),
]


@pytest.mark.parametrize("command,call", XR_PART2_COMMANDS)
def test_xr_part2_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", XR_PART2_COMMANDS)
def test_xr_part2_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.mobile_xr_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
