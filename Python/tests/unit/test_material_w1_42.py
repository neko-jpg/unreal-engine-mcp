"""L1 unit tests for create_substrate_material / create_layered_material (issue #42)."""

from unittest.mock import patch, MagicMock

import server.material_graph_tools as material_graph_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSubstrateMaterial:
    def test_command_name_and_minimum_payload(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=_mock_conn(),
        ) as mock_ue:
            material_graph_tools.create_substrate_material("M_Sub")
        args = mock_ue.return_value.send_command.call_args[0]
        assert args[0] == "create_substrate_material"
        payload = args[1]
        assert payload["name"] == "M_Sub"
        assert payload["package_path"] == "/Game/Materials/"
        for k in ("base_color", "metallic", "roughness", "specular"):
            assert k not in payload

    def test_optional_inputs_are_serialized(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=_mock_conn(),
        ) as mock_ue:
            material_graph_tools.create_substrate_material(
                "M_Sub",
                package_path="/Game/MyMats/",
                base_color=[0.5, 0.5, 0.5],
                metallic=0.2,
                roughness=0.3,
                specular=0.7,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["package_path"] == "/Game/MyMats/"
        assert payload["base_color"] == [0.5, 0.5, 0.5]
        assert payload["metallic"] == 0.2
        assert payload["roughness"] == 0.3
        assert payload["specular"] == 0.7

    def test_metallic_is_float_coerced(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=_mock_conn(),
        ) as mock_ue:
            material_graph_tools.create_substrate_material("M", metallic=1)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert isinstance(payload["metallic"], float)
        assert payload["metallic"] == 1.0


class TestLayeredMaterial:
    def test_command_name_and_payload(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=_mock_conn(),
        ) as mock_ue:
            material_graph_tools.create_layered_material("M_Layered")
        args = mock_ue.return_value.send_command.call_args[0]
        assert args[0] == "create_layered_material"
        payload = args[1]
        assert payload["name"] == "M_Layered"
        assert payload["package_path"] == "/Game/Materials/"

    def test_custom_package_path(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=_mock_conn(),
        ) as mock_ue:
            material_graph_tools.create_layered_material("M", package_path="/Game/Mats/Layers/")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["package_path"] == "/Game/Mats/Layers/"

    def test_failed_connection_returns_error(self):
        with patch(
            "server.material_graph_tools.get_unreal_connection",
            return_value=None,
        ):
            res = material_graph_tools.create_layered_material("M")
        assert res.get("success") is False
