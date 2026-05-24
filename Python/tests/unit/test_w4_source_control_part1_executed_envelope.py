"""234-stubs W4 (#97): executed-envelope tests for Source Control handlers (13 handlers).

This file pairs with the C++ promotion of all 13 Source Control handlers in
`EpicUnrealMCPSourceControlCommands.cpp` from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.source_control_tools as scm
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


SCM_COMMANDS = [
    ("register_git_provider", lambda: scm.register_git_provider("/repo", True)),
    ("register_perforce_provider", lambda: scm.register_perforce_provider("ssl:1666", "user", "workspace")),
    ("source_control_checkout", lambda: scm.source_control_checkout(["/Game/Foo"])),
    ("source_control_checkin", lambda: scm.source_control_checkin(["/Game/Foo"], "test")),
    ("source_control_revert", lambda: scm.source_control_revert(["/Game/Foo"])),
    ("source_control_file_lock_acquire", lambda: scm.source_control_file_lock_acquire(["/Game/Foo"])),
    ("source_control_file_lock_release", lambda: scm.source_control_file_lock_release(["/Game/Foo"])),
    ("source_control_create_changelist", lambda: scm.source_control_create_changelist("desc")),
    ("source_control_asset_diff", lambda: scm.source_control_asset_diff("/Game/Foo")),
    ("source_control_blueprint_diff", lambda: scm.source_control_blueprint_diff("/Game/BP_Foo")),
    ("source_control_merge", lambda: scm.source_control_merge("/Game/Foo")),
    ("multi_user_editing_start", lambda: scm.multi_user_editing_start("Session")),
    ("multi_user_session_join", lambda: scm.multi_user_session_join("udp://host:1234")),
]


@pytest.mark.parametrize("command,call", SCM_COMMANDS)
def test_scm_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.source_control_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", SCM_COMMANDS)
def test_scm_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.source_control_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
