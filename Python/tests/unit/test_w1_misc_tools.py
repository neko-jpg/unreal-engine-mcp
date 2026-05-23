"""L1 unit tests for W1-1 (add_latent_node, animation_fbx_import_tool) and
W1-6 (create_advanced_material) Python tools."""

from unittest.mock import patch, MagicMock

import server.blueprint_tools as blueprint_tools
import server.asset_import_tools as asset_import_tools
import server.material_graph_tools as material_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestAddLatentNode:
    def test_defaults_use_delay(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.add_latent_node("/Game/BP_X")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "add_latent_node"
        payload = args[0][1]
        assert payload["blueprint_path"] == "/Game/BP_X"
        assert payload["function_name"] == "Delay"
        assert payload["library_path"] == "/Script/Engine.KismetSystemLibrary"
        assert payload["graph_name"] == "EventGraph"

    def test_custom_function(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.add_latent_node(
                "/Game/BP_X",
                function_name="AsyncLoadAsset",
                library_path="/Script/Engine.KismetSystemLibrary",
                pos_x=100.0,
                pos_y=50.0,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["function_name"] == "AsyncLoadAsset"
        assert payload["pos_x"] == 100.0
        assert payload["pos_y"] == 50.0

    def test_rejects_empty_blueprint(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.add_latent_node("")
        assert r.get("success") is False


class TestAnimationFbxImport:
    def test_sends_required_params(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            asset_import_tools.animation_fbx_import_tool(
                "C:/anim/run.fbx",
                "/Game/Anim",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
            )
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "import_animation_fbx"
        payload = args[0][1]
        assert payload["source_path"] == "C:/anim/run.fbx"
        assert payload["destination_path"] == "/Game/Anim"
        assert payload["skeleton_path"] == "/Game/Mannequin/SK_Mannequin_Skeleton"
        assert payload["scale"] == 1.0
        assert payload["convert_scene_unit"] is False
        assert "asset_name" not in payload

    def test_with_optional_name(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            asset_import_tools.animation_fbx_import_tool(
                "C:/anim/run.fbx",
                "/Game/Anim",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
                asset_name="Anim_Run",
                scale=2.5,
                convert_scene_unit=True,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["asset_name"] == "Anim_Run"
        assert payload["scale"] == 2.5
        assert payload["convert_scene_unit"] is True

    def test_rejects_empty_skeleton(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()):
            r = asset_import_tools.animation_fbx_import_tool("a.fbx", "/Game/Anim", "")
        assert r.get("success") is False


class TestCreateAdvancedMaterial:
    def test_default_domain(self):
        with patch("server.material_graph_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            material_tools.create_advanced_material("M_Test")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_advanced_material"
        payload = args[0][1]
        assert payload["name"] == "M_Test"
        assert payload["package_path"] == "/Game/Materials/"
        assert payload["material_domain"] == "Surface"

    def test_decal_domain(self):
        with patch("server.material_graph_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            material_tools.create_advanced_material(
                "M_Decal", package_path="/Game/Decals/", material_domain="DeferredDecal"
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["material_domain"] == "DeferredDecal"
        assert payload["package_path"] == "/Game/Decals/"

    def test_passes_unknown_domain_through(self):
        # The current implementation does not validate domain client-side; UE
        # will reject unknown values server-side. Verify pass-through.
        with patch("server.material_graph_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            material_tools.create_advanced_material("M_X", material_domain="Hologram")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["material_domain"] == "Hologram"
