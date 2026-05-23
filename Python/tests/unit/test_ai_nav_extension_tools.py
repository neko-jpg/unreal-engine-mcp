"""L1 unit tests for ai_nav_extension_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.ai_nav_extension_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_add_behavior_tree_node_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_behavior_tree_node("bt_path_v", "node_type_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_behavior_tree_node"


def test_connect_behavior_tree_nodes_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.connect_behavior_tree_nodes("bt_path_v", "from_node_v", "to_node_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "connect_behavior_tree_nodes"


def test_create_bt_task_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_bt_task()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_bt_task"


def test_create_bt_service_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_bt_service()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_bt_service"


def test_create_bt_decorator_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_bt_decorator()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_bt_decorator"


def test_set_blackboard_template_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_blackboard_template("controller_actor_v", "blackboard_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_blackboard_template"


def test_set_ai_controller_behavior_tree_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_ai_controller_behavior_tree("controller_actor_v", "behavior_tree_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_ai_controller_behavior_tree"


def test_spawn_run_behavior_tree_node_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_run_behavior_tree_node("bt_path_v", "target_bt_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_run_behavior_tree_node"


def test_configure_ai_sense_hearing_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ai_sense_hearing("perception_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ai_sense_hearing"


def test_configure_ai_sense_damage_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ai_sense_damage("perception_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ai_sense_damage"


def test_configure_ai_sense_team_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_ai_sense_team("perception_actor_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_ai_sense_team"


def test_configure_eqs_generator_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_eqs_generator("eqs_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_eqs_generator"


def test_configure_eqs_test_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_eqs_test("eqs_path_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_eqs_test"


def test_set_eqs_debug_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_eqs_debug()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_eqs_debug"


def test_set_smart_nav_link_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_smart_nav_link("actor_name_v", [], [])
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_smart_nav_link"


def test_create_nav_area_class_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_nav_area_class()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_nav_area_class"


def test_set_recast_navmesh_details_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_recast_navmesh_details()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_recast_navmesh_details"


def test_bridge_mass_entity_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.bridge_mass_entity()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "bridge_mass_entity"


def test_create_state_tree_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_state_tree()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_state_tree"


def test_add_state_tree_state_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_state_tree_state("state_tree_path_v", "state_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_state_tree_state"


def test_add_state_tree_task_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.add_state_tree_task("state_tree_path_v", "state_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "add_state_tree_task"


def test_set_ai_behavior_tag_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.set_ai_behavior_tag("actor_name_v", "tag_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "set_ai_behavior_tag"


def test_configure_cognitive_ai_controller_payload():
    with patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.configure_cognitive_ai_controller("actor_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "configure_cognitive_ai_controller"
