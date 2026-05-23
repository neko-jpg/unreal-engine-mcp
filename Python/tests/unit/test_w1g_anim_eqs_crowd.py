"""L1 unit tests for W1-G Animation residue + EQS + Crowd Following."""

from unittest.mock import patch, MagicMock

import server.blueprint_tools as blueprint_tools
import server.ai_navigation_tools as ai_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSetAnimRootMotion:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.set_anim_root_motion("/Game/Anim/A_Run")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"anim_sequence_path": "/Game/Anim/A_Run", "enable_root_motion": True}

    def test_with_lock(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.set_anim_root_motion(
                "/Game/Anim/A_Run", enable_root_motion=False, root_motion_root_lock="Zero"
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["enable_root_motion"] is False
        assert payload["root_motion_root_lock"] == "Zero"

    def test_rejects_unknown_lock(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.set_anim_root_motion("/G/A", root_motion_root_lock="Floating")
        assert r.get("success") is False


class TestAddAnimNotify:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.add_anim_notify("/Game/Anim/A_Attack", "FootStep", time_seconds=0.5)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["notify_name"] == "FootStep"
        assert payload["time_seconds"] == 0.5
        assert "notify_class_path" not in payload

    def test_with_class(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.add_anim_notify(
                "/Game/Anim/A_Attack",
                "PlaySound",
                time_seconds=0.25,
                notify_class_path="/Script/Engine.AnimNotify_PlaySound",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["notify_class_path"] == "/Script/Engine.AnimNotify_PlaySound"

    def test_rejects_negative_time(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()):
            r = blueprint_tools.add_anim_notify("/G/A", "N", time_seconds=-1.0)
        assert r.get("success") is False


class TestCreatePoseAsset:
    def test_minimal(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_pose_asset(
                "/Game/Anim/PA_Face",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {
            "asset_path": "/Game/Anim/PA_Face",
            "skeleton_path": "/Game/Mannequin/SK_Mannequin_Skeleton",
        }

    def test_with_source(self):
        with patch("server.blueprint_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            blueprint_tools.create_pose_asset(
                "/Game/Anim/PA_Face",
                "/Game/Mannequin/SK_Mannequin_Skeleton",
                source_anim_sequence_path="/Game/Anim/A_FacePoses",
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["source_anim_sequence_path"] == "/Game/Anim/A_FacePoses"


class TestCreateEQSQuery:
    def test_minimal(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.create_eqs_query("/Game/AI/EQ_FindCover")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"asset_path": "/Game/AI/EQ_FindCover"}

    def test_with_query_name(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.create_eqs_query("/Game/AI/EQ_FindCover", query_name="FindCover")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["query_name"] == "FindCover"

    def test_rejects_empty(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.create_eqs_query("")
        assert r.get("success") is False


class TestSetCrowdFollowingEnable:
    def test_enable(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.set_crowd_following_enable("AIC_Guard_0")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "AIC_Guard_0", "enable": True}

    def test_disable(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.set_crowd_following_enable("AIC_Guard_0", enable=False)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["enable"] is False
