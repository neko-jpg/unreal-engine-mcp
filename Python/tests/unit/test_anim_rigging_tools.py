"""L1 unit tests for Animation / Skeletal / Rigging tools (Sub-batch K, issue #48)."""
from unittest.mock import patch, MagicMock
import server.anim_rigging_tools as art


def _mock_conn():
    m = MagicMock(); m.send_command.return_value = {"success": True, "data": {}}
    return m


class TestAssetCreators:
    def test_create_skeleton_defaults(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_skeleton_asset()
        a = ue.return_value.send_command.call_args
        assert a[0][0] == "create_skeleton_asset"
        assert a[0][1] == {"asset_path": "/Game/Anim", "asset_name": "SKEL_New"}

    def test_create_physics_overrides(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_physics_asset(asset_path="/Game/Custom", asset_name="PHYS_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["asset_name"] == "PHYS_Robot"


class TestAnimGraph:
    def test_add_node(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_anim_graph_node("/Game/ABP", "BlendListByBool", 100.0, 50.0)
        a = ue.return_value.send_command.call_args
        assert a[0][1]["node_type"] == "BlendListByBool"
        assert a[0][1]["location_x"] == 100.0

    def test_state_machine(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_anim_state_machine("/Game/ABP", graph_name="Locomotion")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["graph_name"] == "Locomotion"

    def test_state_add(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_anim_state("/Game/ABP", "Locomotion", "Idle")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["state_name"] == "Idle"

    def test_transition(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_anim_transition_rule("/Game/ABP", "Idle", "Run", condition="Speed > 100")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["condition"] == "Speed > 100"

    def test_aim_offset(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_aim_offset()
        a = ue.return_value.send_command.call_args
        assert a[0][0] == "create_aim_offset"

    def test_notify_state(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_notify_state("/Game/Anim/A_Run", "AnimNotifyState_Trail", start_time=0.5, duration=1.0)
        a = ue.return_value.send_command.call_args
        assert a[0][1]["duration"] == 1.0


class TestIK:
    def test_create_ik_rig(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_ik_rig(asset_name="IKRig_Robot", skeletal_mesh_path="/Game/SK_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["skeletal_mesh_path"] == "/Game/SK_Robot"

    def test_add_ik_goal(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_ik_goal("/Game/IKRig_Robot", "RightHandGoal", "hand_r")
        a = ue.return_value.send_command.call_args
        assert a[0][1] == {"ik_rig_path": "/Game/IKRig_Robot", "goal_name": "RightHandGoal", "bone": "hand_r"}

    def test_add_ik_solver(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_ik_solver("/Game/IKRig_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["solver_type"] == "FBIK"

    def test_create_retargeter(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_ik_retargeter(source_ik_rig="/Game/IKA", target_ik_rig="/Game/IKB")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["source_ik_rig"] == "/Game/IKA"

    def test_retarget_chain(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.set_retarget_chain("/Game/IKR", "Spine", "pelvis", "head")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["chain_name"] == "Spine"


class TestControlRig:
    def test_create_control_rig(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.create_control_rig(skeleton_path="/Game/SKEL_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["skeleton_path"] == "/Game/SKEL_Robot"

    def test_add_control(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_control_rig_control("/Game/CR", "MyCtrl", control_type="Float", bone="head")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["control_type"] == "Float"

    def test_add_bone(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.add_control_rig_bone("/Game/CR", "NewBone", parent_bone="root")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["parent_bone"] == "root"

    def test_constraint(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.set_control_rig_constraint("/Game/CR", "MyCtrl", constraint_type="Position", target="root")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["constraint_type"] == "Position"

    def test_sequencer_track(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.sequencer_control_rig_track("/Game/Cine/LS_Shot", "MyActor", "/Game/CR_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["control_rig_path"] == "/Game/CR_Robot"


class TestMisc:
    def test_retarget_manager(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.set_retarget_manager("/Game/SKEL_Robot", rig_bp_path="/Game/CR_Robot")
        a = ue.return_value.send_command.call_args
        assert a[0][1]["rig_bp_path"] == "/Game/CR_Robot"

    def test_facial(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.set_facial_animation("/Game/SK_Face", "/Game/Anim_Face")
        a = ue.return_value.send_command.call_args
        assert a[0][0] == "set_facial_animation"

    def test_morph(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.set_morph_target("/Game/SK_Face", "Smile", weight=0.5)
        a = ue.return_value.send_command.call_args
        assert a[0][1]["weight"] == 0.5

    def test_metahuman(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=_mock_conn()) as ue:
            art.connect_metahuman("/Game/MH_BP", target_actor="MyMetahuman")
        a = ue.return_value.send_command.call_args
        assert a[0][0] == "connect_metahuman"


class TestConnection:
    def test_no_connection(self):
        with patch("server.anim_rigging_tools.get_unreal_connection", return_value=None):
            r = art.create_skeleton_asset()
        assert r.get("success") is False