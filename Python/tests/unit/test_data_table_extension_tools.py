"""L1 unit tests for data_table_extension_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.data_table_extension_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_row_struct_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_row_struct()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_row_struct"


def test_edit_row_struct_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_row_struct("struct_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_row_struct"


def test_edit_data_asset_properties_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_data_asset_properties("data_asset_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_data_asset_properties"


def test_import_gameplay_tag_table_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.import_gameplay_tag_table("csv_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "import_gameplay_tag_table"


def test_generate_item_db_template_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.generate_item_db_template()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "generate_item_db_template"


def test_generate_enemy_db_template_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.generate_enemy_db_template()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "generate_enemy_db_template"


def test_generate_quest_db_template_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.generate_quest_db_template()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "generate_quest_db_template"


def test_generate_dialogue_db_template_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.generate_dialogue_db_template()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "generate_dialogue_db_template"


def test_create_blueprint_datatable_reference_node_payload():
    with patch("server.data_table_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_blueprint_datatable_reference_node("blueprint_path_v", "datatable_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_blueprint_datatable_reference_node"
