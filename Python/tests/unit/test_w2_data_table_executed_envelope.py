"""234-stubs W2 (#85): executed-envelope tests for DataTable Extension (9 handlers).

This file pairs with the C++ promotion of all 9 handlers in
`EpicUnrealMCPDataTableExtensionCommands.cpp` from `queued: true` to the
canonical `{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.data_table_extension_tools as dt
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True, "object_path": extra.pop("object_path", "/Game/Data/DT_Test")}
    data.update(extra)
    return {"success": True, "data": data}


DATATABLE_COMMANDS = [
    ("create_row_struct", lambda: dt.create_row_struct("/Game/Data", "FRow_New", [])),
    ("edit_row_struct", lambda: dt.edit_row_struct("/Game/Data/FRow_New", [])),
    ("edit_data_asset_properties", lambda: dt.edit_data_asset_properties("/Game/Data/DA_Test", [])),
    ("import_gameplay_tag_table", lambda: dt.import_gameplay_tag_table("/Game/Tags/Tags.csv")),
    ("generate_item_db_template", lambda: dt.generate_item_db_template("/Game/Data", "DT_Items")),
    ("generate_enemy_db_template", lambda: dt.generate_enemy_db_template("/Game/Data", "DT_Enemies")),
    ("generate_quest_db_template", lambda: dt.generate_quest_db_template("/Game/Data", "DT_Quests")),
    ("generate_dialogue_db_template", lambda: dt.generate_dialogue_db_template("/Game/Data", "DT_Dialogue")),
    ("create_blueprint_datatable_reference_node", lambda: dt.create_blueprint_datatable_reference_node("/Game/BP_Hero", "/Game/Data/DT_Items")),
]


@pytest.mark.parametrize("command,call", DATATABLE_COMMANDS)
def test_datatable_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command, mcp_metadata_keys_persisted=1)
    conn = _conn_returning(payload)
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", DATATABLE_COMMANDS)
def test_datatable_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
