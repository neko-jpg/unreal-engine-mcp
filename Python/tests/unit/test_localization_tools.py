"""L1 unit tests for localization_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.localization_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_open_localization_dashboard_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.open_localization_dashboard()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "open_localization_dashboard"


def test_add_localization_culture_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_localization_culture("culture_code_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_localization_culture"


def test_run_text_gather_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_text_gather()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_text_gather"


def test_export_po_files_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.export_po_files("output_directory_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "export_po_files"


def test_import_po_files_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.import_po_files("po_directory_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "import_po_files"


def test_create_string_table_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_string_table()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_string_table"


def test_edit_string_table_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.edit_string_table("asset_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "edit_string_table"


def test_localize_widget_text_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.localize_widget_text("widget_path_v", "text_id_v", "translation_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "localize_widget_text"


def test_localize_dialogue_wave_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.localize_dialogue_wave("dialogue_wave_path_v", "culture_code_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "localize_dialogue_wave"


def test_configure_font_fallback_payload():
    with patch("server.localization_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_font_fallback("font_path_v", [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_font_fallback"
