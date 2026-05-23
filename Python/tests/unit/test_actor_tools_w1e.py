"""L1 unit tests for actor_tools W1-E networking minimal."""

from unittest.mock import patch, MagicMock

import server.actor_tools as actor_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSetActorReplicates:
    def test_default_true(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_replicates("MyActor")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "MyActor", "replicates": True}

    def test_explicit_false(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_replicates("MyActor", replicates=False)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["replicates"] is False

    def test_rejects_empty_name(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()):
            r = actor_tools.set_actor_replicates("")
        assert r.get("success") is False


class TestSetActorReplicateMovement:
    def test_default_true(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_replicate_movement("MyActor")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["replicate_movement"] is True


class TestSetActorNetDormancy:
    def test_sends_required(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_net_dormancy("MyActor", "DormantAll")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "MyActor", "dormancy": "DormantAll"}

    def test_rejects_unknown(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()):
            r = actor_tools.set_actor_net_dormancy("MyActor", "Sleepy")
        assert r.get("success") is False


class TestSetActorNetCullDistance:
    def test_sends_required(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_net_cull_distance("MyActor", 5000.0)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "MyActor", "distance": 5000.0}

    def test_rejects_negative(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()):
            r = actor_tools.set_actor_net_cull_distance("MyActor", -1.0)
        assert r.get("success") is False


class TestSetActorOwnerOnlyRelevant:
    def test_default_true(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_owner_only_relevant("MyActor")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "MyActor", "owner_only": True}

    def test_explicit_false(self):
        with patch("server.actor_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            actor_tools.set_actor_owner_only_relevant("MyActor", owner_only=False)
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["owner_only"] is False
