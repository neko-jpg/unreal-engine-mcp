"""W4 unit tests for networking_tools -- 21 promoted executed-envelope handlers."""
import unittest
from unittest.mock import patch, MagicMock

import server.networking_tools as m


def _mock_send_command(cmd_type, params):
    return {"success": True, "data": {"executed": True, "command": cmd_type, **(params or {})}}


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestNetworkingPart1ExecutedEnvelope(unittest.TestCase):

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_rpc_server_function(self, mock_conn):
        result = m.create_rpc_server_function(blueprint_path="/Game/BP_MyActor", function_name="ServerRPC")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_rpc_server_function_with_validation(self, mock_conn):
        result = m.create_rpc_server_function(blueprint_path="/Game/BP_MyActor", function_name="ServerRPC", with_validation=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_rpc_client_function(self, mock_conn):
        result = m.create_rpc_client_function(blueprint_path="/Game/BP_MyActor", function_name="ClientRPC")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_rpc_multicast_function(self, mock_conn):
        result = m.create_rpc_multicast_function(blueprint_path="/Game/BP_MyActor", function_name="MulticastRPC")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_rpc_reliability(self, mock_conn):
        result = m.set_rpc_reliability(blueprint_path="/Game/BP_MyActor", function_name="ServerRPC", reliable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_rpc_reliability_unreliable(self, mock_conn):
        result = m.set_rpc_reliability(blueprint_path="/Game/BP_MyActor", function_name="ServerRPC", reliable=False)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_rep_notify(self, mock_conn):
        result = m.set_rep_notify(blueprint_path="/Game/BP_MyActor", variable_name="Health")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_rep_notify_custom_func(self, mock_conn):
        result = m.set_rep_notify(blueprint_path="/Game/BP_MyActor", variable_name="Health", repnotify_function="CustomOnRep")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_list_replicated_variables(self, mock_conn):
        result = m.list_replicated_variables(blueprint_path="/Game/BP_MyActor")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_network_prediction(self, mock_conn):
        result = m.set_network_prediction(actor_name="MyActor", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_configure_dedicated_server(self, mock_conn):
        result = m.configure_dedicated_server(map_name="/Game/Maps/BattleArena", port=27015)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_configure_dedicated_server_defaults(self, mock_conn):
        result = m.configure_dedicated_server()
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_start_listen_server(self, mock_conn):
        result = m.start_listen_server(map_name="/Game/Maps/StartUp", port=7777)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_start_client(self, mock_conn):
        result = m.start_client(host="192.168.1.100", port=27015)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_configure_multi_pie(self, mock_conn):
        result = m.configure_multi_pie(client_count=4)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_online_subsystem(self, mock_conn):
        result = m.set_online_subsystem(subsystem="Steam")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_session(self, mock_conn):
        result = m.create_session(session_name="MyGame", max_players=16)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_find_sessions(self, mock_conn):
        result = m.find_sessions(timeout_seconds=15.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_join_session(self, mock_conn):
        result = m.join_session(session_name="MyGame")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_iris_replication(self, mock_conn):
        result = m.set_iris_replication(enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_replication_graph(self, mock_conn):
        result = m.set_replication_graph(replication_graph_class="MyRepGraph")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_start_bandwidth_profiling(self, mock_conn):
        result = m.start_bandwidth_profiling(seconds=60.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_attach_network_profiler(self, mock_conn):
        result = m.attach_network_profiler(enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_create_network_component(self, mock_conn):
        result = m.create_network_component(actor_name="MyActor", component_class="ReplicatedComp")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.networking_tools.get_unreal_connection", return_value=_conn())
    def test_set_blueprint_variable_replication(self, mock_conn):
        result = m.set_blueprint_variable_replication(blueprint_path="/Game/BP_MyActor", variable_name="Score", condition="InitialOnly")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
