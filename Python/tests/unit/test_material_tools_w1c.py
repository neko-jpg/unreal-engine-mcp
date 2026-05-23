"""L1 unit tests for material_graph_tools W1-C domain wrappers."""

from unittest.mock import patch, MagicMock

import server.material_graph_tools as material_graph_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


def _check_domain(fn, expected_domain: str, expected_name: str = "M_Test"):
    with patch("server.material_graph_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
        fn(expected_name)
    args = mock_ue.return_value.send_command.call_args
    assert args[0][0] == "create_advanced_material"
    payload = args[0][1]
    assert payload["name"] == expected_name
    assert payload["package_path"] == "/Game/Materials/"
    assert payload["material_domain"] == expected_domain


class TestMaterialDomainWrappers:
    def test_decal(self):
        _check_domain(material_graph_tools.create_decal_material, "DeferredDecal", "M_Decal")

    def test_light_function(self):
        _check_domain(material_graph_tools.create_light_function_material, "LightFunction", "M_Beam")

    def test_post_process(self):
        _check_domain(material_graph_tools.create_post_process_material, "PostProcess", "M_PP")

    def test_landscape(self):
        _check_domain(material_graph_tools.create_landscape_material, "Landscape", "M_Land")

    def test_runtime_virtual_texture(self):
        _check_domain(material_graph_tools.create_runtime_virtual_texture_material, "VirtualTexture", "M_RVT")

    def test_custom_package_path(self):
        with patch("server.material_graph_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            material_graph_tools.create_decal_material("M_Decal", package_path="/Game/Decals/")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["package_path"] == "/Game/Decals/"
