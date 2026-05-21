"""L1 unit tests for data_table_tools W1-B residue."""

from unittest.mock import patch, MagicMock

import server.data_table_tools as data_table_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestCreateDataTableFromJSON:
    def test_sends_required_params(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_data_table_from_json(
                "/Game/Data/MyTable",
                "/Game/Structs/MyRow",
                "[]",
            )
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_data_table_from_json"
        payload = args[0][1]
        assert payload["table_path"] == "/Game/Data/MyTable"
        assert payload["row_struct_path"] == "/Game/Structs/MyRow"
        assert payload["json_content"] == "[]"

    def test_rejects_empty_json(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.create_data_table_from_json("/G/T", "/G/S", "")
        assert r.get("success") is False


class TestCreateCurveTable:
    def test_minimal(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_curve_table("/Game/Data/MyCurve")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["table_path"] == "/Game/Data/MyCurve"
        assert payload["interp_mode"] == "Linear"
        assert "csv_content" not in payload

    def test_with_csv(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_curve_table(
                "/Game/Data/MyCurve",
                csv_content="---,0,1,2\nA,1,2,3",
                interp_mode="Cubic",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["interp_mode"] == "Cubic"
        assert "A,1,2,3" in payload["csv_content"]

    def test_rejects_unknown_interp(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.create_curve_table("/G/C", interp_mode="Bezier")
        assert r.get("success") is False


class TestCreateStringTable:
    def test_minimal(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_string_table("/Game/Loc/MyTable")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"table_path": "/Game/Loc/MyTable"}

    def test_with_namespace_and_entries(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_string_table(
                "/Game/Loc/MyTable",
                namespace="UI",
                entries={"HELLO": "Hello!", "BYE": "Goodbye."},
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["namespace"] == "UI"
        assert payload["entries"] == {"HELLO": "Hello!", "BYE": "Goodbye."}

    def test_rejects_non_string_value_in_entries(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.create_string_table("/G/T", entries={"HELLO": 123})
        assert r.get("success") is False

    def test_rejects_non_dict_entries(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.create_string_table("/G/T", entries=["HELLO"])  # type: ignore[arg-type]
        assert r.get("success") is False


class TestSetStringTableEntry:
    def test_sends_required_params(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.set_string_table_entry("/Game/Loc/T", "K", "V")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"table_path": "/Game/Loc/T", "key": "K", "value": "V"}

    def test_rejects_empty_key(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.set_string_table_entry("/G/T", "", "V")
        assert r.get("success") is False

    def test_rejects_non_string_value(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.set_string_table_entry("/G/T", "K", 1)  # type: ignore[arg-type]
        assert r.get("success") is False


class TestCreateDataAsset:
    def test_sends_required_params(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            data_table_tools.create_data_asset(
                "/Game/Data/MyAsset",
                "/Script/Engine.DataAsset",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["asset_path"] == "/Game/Data/MyAsset"
        assert payload["class_path"] == "/Script/Engine.DataAsset"

    def test_rejects_empty_class(self):
        with patch("server.data_table_tools.get_unreal_connection", return_value=_mock_conn()):
            r = data_table_tools.create_data_asset("/G/A", "")
        assert r.get("success") is False
