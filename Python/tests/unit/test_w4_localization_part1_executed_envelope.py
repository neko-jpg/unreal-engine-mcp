"""234-stubs W4 (#94): executed-envelope tests for Localization handlers (part 1, 10 handlers).

This file pairs with the C++ promotion of all 10 Localization handlers in
`EpicUnrealMCPLocalizationCommands.cpp` from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.localization_tools as loc
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


LOCALIZATION_COMMANDS = [
    ("open_localization_dashboard", lambda: loc.open_localization_dashboard()),
    ("add_localization_culture", lambda: loc.add_localization_culture("ja")),
    ("run_text_gather", lambda: loc.run_text_gather("Game")),
    ("export_po_files", lambda: loc.export_po_files("/tmp/po", "Game")),
    ("import_po_files", lambda: loc.import_po_files("/tmp/po", "Game")),
    ("localization_create_string_table", lambda: loc.localization_create_string_table("/Game/Localization", "ST_Test")),
    ("edit_string_table", lambda: loc.edit_string_table("/Game/Localization/ST_Test", [{"key": "hello", "source_string": "Hello"}])),
    ("localize_widget_text", lambda: loc.localize_widget_text("/Game/UI/WBP_Main", "greeting", "Hello")),
    ("localize_dialogue_wave", lambda: loc.localize_dialogue_wave("/Game/Audio/DW_Intro", "ja")),
    ("configure_font_fallback", lambda: loc.configure_font_fallback("/Game/Fonts/Main", ["/Game/Fonts/Fallback"])),
]


@pytest.mark.parametrize("command,call", LOCALIZATION_COMMANDS)
def test_localization_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.localization_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", LOCALIZATION_COMMANDS)
def test_localization_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.localization_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
