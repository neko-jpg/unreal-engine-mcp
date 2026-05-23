"""L1 unit tests for pcg_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.pcg_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_pcg_graph_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_pcg_graph()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_pcg_graph"


def test_add_pcg_component_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_pcg_component("actor_name_v", "graph_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_pcg_component"


def test_create_pcg_volume_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_pcg_volume()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_pcg_volume"


def test_add_pcg_node_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_pcg_node("graph_path_v", "node_type_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_pcg_node"


def test_connect_pcg_nodes_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.connect_pcg_nodes("graph_path_v", "from_node_v", "to_node_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "connect_pcg_nodes"


def test_set_pcg_graph_parameter_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_pcg_graph_parameter("graph_path_v", "parameter_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_pcg_graph_parameter"


def test_configure_pcg_spline_sampler_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pcg_spline_sampler("graph_path_v", "spline_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pcg_spline_sampler"


def test_configure_pcg_surface_sampler_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pcg_surface_sampler("graph_path_v", "surface_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pcg_surface_sampler"


def test_configure_pcg_static_mesh_spawner_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pcg_static_mesh_spawner("graph_path_v", "mesh_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pcg_static_mesh_spawner"


def test_configure_pcg_rule_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pcg_rule("graph_path_v", "rule_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pcg_rule"


def test_create_pcg_biome_graph_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_pcg_biome_graph()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_pcg_biome_graph"


def test_operate_pcg_point_data_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.operate_pcg_point_data("graph_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "operate_pcg_point_data"


def test_operate_pcg_attribute_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.operate_pcg_attribute("graph_path_v", "attribute_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "operate_pcg_attribute"


def test_execute_pcg_graph_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.execute_pcg_graph("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "execute_pcg_graph"


def test_regenerate_pcg_graph_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.regenerate_pcg_graph("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "regenerate_pcg_graph"


def test_set_pcg_runtime_generation_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_pcg_runtime_generation("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_pcg_runtime_generation"


def test_use_pcg_editor_mode_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.use_pcg_editor_mode()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "use_pcg_editor_mode"


def test_create_pcg_tool_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_pcg_tool()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_pcg_tool"


def test_set_pcg_debug_display_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_pcg_debug_display()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_pcg_debug_display"


def test_configure_pcg_self_pruning_payload():
    with patch("server.pcg_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_pcg_self_pruning("graph_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_pcg_self_pruning"
