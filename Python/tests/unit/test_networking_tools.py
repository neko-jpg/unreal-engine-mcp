"""L1 unit tests for networking_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.networking_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_rpc_server_function_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_rpc_server_function("blueprint_path_v", "function_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_rpc_server_function"


def test_create_rpc_client_function_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_rpc_client_function("blueprint_path_v", "function_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_rpc_client_function"


def test_create_rpc_multicast_function_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_rpc_multicast_function("blueprint_path_v", "function_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_rpc_multicast_function"


def test_set_rpc_reliability_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_rpc_reliability("blueprint_path_v", "function_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_rpc_reliability"


def test_set_rep_notify_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_rep_notify("blueprint_path_v", "variable_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_rep_notify"


def test_list_replicated_variables_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.list_replicated_variables("blueprint_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "list_replicated_variables"


def test_set_network_prediction_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_network_prediction("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_network_prediction"


def test_configure_dedicated_server_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_dedicated_server()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_dedicated_server"


def test_start_listen_server_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.start_listen_server()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "start_listen_server"


def test_start_client_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.start_client()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "start_client"


def test_configure_multi_pie_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_multi_pie()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_multi_pie"


def test_set_online_subsystem_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_online_subsystem()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_online_subsystem"


def test_create_session_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_session()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_session"


def test_find_sessions_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.find_sessions()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "find_sessions"


def test_join_session_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.join_session()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "join_session"


def test_set_iris_replication_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_iris_replication()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_iris_replication"


def test_set_replication_graph_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_replication_graph()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_replication_graph"


def test_start_bandwidth_profiling_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.start_bandwidth_profiling()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "start_bandwidth_profiling"


def test_attach_network_profiler_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.attach_network_profiler()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "attach_network_profiler"


def test_create_network_component_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_network_component("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_network_component"


def test_set_blueprint_variable_replication_payload():
    with patch("server.networking_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_blueprint_variable_replication("blueprint_path_v", "variable_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_blueprint_variable_replication"
