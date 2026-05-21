"""L1 unit tests for blueprint_tools W1-C asset creators."""

from unittest.mock import patch, MagicMock

import server.blueprint_tools as blueprint_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestCreateAnimationBlueprint:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_animation_blueprint(
                "/Game/Anim/ABP_Player",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
            )
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_animation_blueprint"
        payload = args[0][1]
        assert payload["asset_path"] == "/Game/Anim/ABP_Player"
        assert payload["skeleton_path"] == "/Game/Mannequin/SK_Mannequin_Skeleton"
        assert "parent_class_path" not in payload

    def test_with_parent_class(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_animation_blueprint(
                "/Game/Anim/ABP_AI",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
                parent_class_path="/Game/MyABP.MyABP_C",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["parent_class_path"] == "/Game/MyABP.MyABP_C"

    def test_rejects_empty_skeleton(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.create_animation_blueprint("/G/A", "")
        assert r.get("success") is False


class TestCreateBlendSpace:
    def test_sends_required_params(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_blend_space(
                "/Game/Anim/BS_Locomotion",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
            )
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "create_blend_space"
        assert args[0][1] == {
            "asset_path": "/Game/Anim/BS_Locomotion",
            "skeleton_path": "/Game/Mannequin/SK_Mannequin_Skeleton",
        }

    def test_rejects_empty_asset_path(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.create_blend_space("", "/G/S")
        assert r.get("success") is False
