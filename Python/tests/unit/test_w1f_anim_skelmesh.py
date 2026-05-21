"""L1 unit tests for W1-F Skeletal Mesh / AnimMontage / AnimComposite tools."""

from unittest.mock import patch, MagicMock

import server.asset_import_tools as asset_import_tools
import server.blueprint_tools as blueprint_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSkeletalMeshFbxImport:
    def test_minimal(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            asset_import_tools.skeletal_mesh_fbx_import_tool(
                "C:/m.fbx", "/Game/SK"
            )
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "import_skeletal_mesh_fbx"
        payload = args[0][1]
        assert payload["source_path"] == "C:/m.fbx"
        assert payload["destination_path"] == "/Game/SK"
        assert payload["scale"] == 1.0
        assert payload["import_materials"] is True
        assert payload["import_morph_targets"] is False
        assert "skeleton_path" not in payload

    def test_with_skeleton_and_morph(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            asset_import_tools.skeletal_mesh_fbx_import_tool(
                "C:/m.fbx",
                "/Game/SK",
                asset_name="SK_Hero",
                skeleton_path="/Game/Shared/SK_Shared_Skeleton",
                scale=2.0,
                convert_scene_unit=True,
                import_morph_targets=True,
                import_materials=False,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["asset_name"] == "SK_Hero"
        assert payload["skeleton_path"] == "/Game/Shared/SK_Shared_Skeleton"
        assert payload["import_morph_targets"] is True
        assert payload["import_materials"] is False

    def test_rejects_empty_source(self):
        with patch("server.asset_import_tools.get_unreal_connection", return_value=_mock_conn()):
            r = asset_import_tools.skeletal_mesh_fbx_import_tool("", "/Game/SK")
        assert r.get("success") is False


class TestCreateAnimMontage:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_anim_montage(
                "/Game/Anim/AM_Attack", "/Game/Mannequin/SK_Mannequin_Skeleton"
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {
            "asset_path": "/Game/Anim/AM_Attack",
            "skeleton_path": "/Game/Mannequin/SK_Mannequin_Skeleton",
        }

    def test_with_source(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_anim_montage(
                "/Game/Anim/AM_Attack",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
                source_anim_sequence_path="/Game/Anim/A_Attack",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["source_anim_sequence_path"] == "/Game/Anim/A_Attack"


class TestCreateAnimComposite:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_anim_composite(
                "/Game/Anim/AC_Combo", "/Game/Mannequin/SK_Mannequin_Skeleton"
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {
            "asset_path": "/Game/Anim/AC_Combo",
            "skeleton_path": "/Game/Mannequin/SK_Mannequin_Skeleton",
        }

    def test_rejects_empty_skeleton(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.create_anim_composite("/G/A", "")
        assert r.get("success") is False
