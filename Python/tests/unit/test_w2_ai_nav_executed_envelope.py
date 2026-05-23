"""L2 executed-envelope tests for AI/Nav #84 part1 (8 promoted BT handlers).

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for each promoted handler. These tests use a mocked Unreal connection that
returns a canned executed envelope.
"""

import unittest
from unittest.mock import patch, MagicMock


def _mock_send_command(cmd_type, params):
    """Simulate a successful executed response from the C++ bridge."""
    return {
        "success": True,
        "data": {
            "executed": True,
            "command": cmd_type,
            **(params or {}),
        },
    }


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestAINavPart1ExecutedEnvelope(unittest.TestCase):
    """Each AI/Nav part1 handler must return executed:true on the success path."""

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_add_behavior_tree_node(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.add_behavior_tree_node(bt_path="/Game/AI/BT_MyTree", node_type="Task", parent_node="Root")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_connect_behavior_tree_nodes(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.connect_behavior_tree_nodes(bt_path="/Game/AI/BT_MyTree", from_node="Root", to_node="Task1")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_create_bt_task(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.create_bt_task(asset_path="/Game/AI", asset_name="BTT_MyTask", base_class="BTTaskNode")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_create_bt_service(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.create_bt_service(asset_path="/Game/AI", asset_name="BTS_MyService")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_create_bt_decorator(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.create_bt_decorator(asset_path="/Game/AI", asset_name="BTD_MyDecorator")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_set_blackboard_template(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.set_blackboard_template(controller_actor="AIController_0", blackboard_path="/Game/AI/BB_MyBB")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_set_ai_controller_behavior_tree(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.set_ai_controller_behavior_tree(controller_actor="AIController_0", behavior_tree_path="/Game/AI/BT_MyTree")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.ai_nav_extension_tools.get_unreal_connection", return_value=_conn())
    def test_spawn_run_behavior_tree_node(self, mock_conn):
        from server import ai_nav_extension_tools as m
        result = m.spawn_run_behavior_tree_node(bt_path="/Game/AI/BT_MyTree", target_bt_path="/Game/AI/BT_MyTree")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
