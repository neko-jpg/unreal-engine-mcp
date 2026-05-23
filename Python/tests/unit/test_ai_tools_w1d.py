"""L1 unit tests for ai_navigation_tools W1-D extensions."""

from unittest.mock import patch, MagicMock

import server.ai_navigation_tools as ai_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestAddBlackboardKey:
    def test_sends_required(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.add_blackboard_key("/Game/AI/BB", "TargetActor", "Object")
        args = mock_ue.return_value.send_command.call_args
        assert args[0][0] == "add_blackboard_key"
        payload = args[0][1]
        assert payload["blackboard_path"] == "/Game/AI/BB"
        assert payload["key_name"] == "TargetActor"
        assert payload["key_type"] == "Object"
        assert payload["instance_synced"] is False

    def test_instance_synced(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.add_blackboard_key("/G/BB", "Score", "Float", instance_synced=True)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["instance_synced"] is True

    def test_rejects_unknown_type(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.add_blackboard_key("/G/BB", "X", "Quaternion")
        assert r.get("success") is False

    def test_rejects_empty_key_name(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.add_blackboard_key("/G/BB", "", "Bool")
        assert r.get("success") is False


class TestRemoveBlackboardKey:
    def test_sends_required(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.remove_blackboard_key("/G/BB", "K")
        assert mock_ue.return_value.send_command.call_args[0][0] == "remove_blackboard_key"
        assert mock_ue.return_value.send_command.call_args[0][1] == {
            "blackboard_path": "/G/BB",
            "key_name": "K",
        }

    def test_rejects_empty(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.remove_blackboard_key("/G/BB", "")
        assert r.get("success") is False


class TestAddAIPerception:
    def test_sends_required(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.add_ai_perception("AI_Guard_01")
        assert mock_ue.return_value.send_command.call_args[0][0] == "add_ai_perception"
        assert mock_ue.return_value.send_command.call_args[0][1] == {"actor_name": "AI_Guard_01"}

    def test_rejects_empty(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.add_ai_perception("")
        assert r.get("success") is False


class TestConfigureAISenseSight:
    def test_minimal(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.configure_ai_sense_sight("AI", sight_radius=1500.0)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["sight_radius"] == 1500.0
        assert "lose_sight_radius" not in payload
        assert "detect_enemies" not in payload

    def test_full(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.configure_ai_sense_sight(
                "AI",
                sight_radius=2000.0,
                lose_sight_radius=2500.0,
                peripheral_vision_angle_degrees=60.0,
                auto_success_range_from_last_seen=300.0,
                detect_neutrals=False,
                detect_friendlies=False,
                detect_enemies=True,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["lose_sight_radius"] == 2500.0
        assert payload["detect_enemies"] is True
        assert payload["detect_friendlies"] is False

    def test_rejects_negative_radius(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.configure_ai_sense_sight("AI", sight_radius=-1.0)
        assert r.get("success") is False


class TestSetRecastNavMeshAgent:
    def test_sends_partial(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.set_recast_navmesh_agent(agent_radius=42.0, agent_height=180.0)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"agent_radius": 42.0, "agent_height": 180.0}

    def test_rejects_no_fields(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.set_recast_navmesh_agent()
        assert r.get("success") is False

    def test_rejects_zero_radius(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()):
            r = ai_tools.set_recast_navmesh_agent(agent_radius=0.0)
        assert r.get("success") is False

    def test_accepts_zero_simplification_error(self):
        with patch("server.ai_navigation_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            ai_tools.set_recast_navmesh_agent(max_simplification_error=0.0)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"max_simplification_error": 0.0}
