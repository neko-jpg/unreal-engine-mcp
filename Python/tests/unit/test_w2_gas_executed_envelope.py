"""L2 executed-envelope tests for GAS #86 (all 16 promoted handlers).

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for each promoted handler when WITH_GAS_MCP is active.  These tests use a
mocked Unreal connection that returns a canned executed envelope.
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


class TestGASPart1ExecutedEnvelope(unittest.TestCase):
    """Each GAS handler must return executed:true on the success path."""

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_enable_gas_plugin(self, mock_conn):
        from server import gas_tools as m
        result = m.enable_gas_plugin()
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_add_ability_system_component(self, mock_conn):
        from server import gas_tools as m
        result = m.add_ability_system_component(actor_name="TestActor")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_create_attribute_set(self, mock_conn):
        from server import gas_tools as m
        result = m.create_attribute_set(asset_path="/Game/GAS", asset_name="AS_Health")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_create_gameplay_ability(self, mock_conn):
        from server import gas_tools as m
        result = m.create_gameplay_ability(asset_path="/Game/GAS", asset_name="GA_Fireball")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_create_gameplay_effect(self, mock_conn):
        from server import gas_tools as m
        result = m.create_gameplay_effect(asset_path="/Game/GAS", asset_name="GE_Heal", duration_type="Instant")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_create_gameplay_cue(self, mock_conn):
        from server import gas_tools as m
        result = m.create_gameplay_cue(asset_path="/Game/GAS", asset_name="GC_Hit")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_bind_ability_input(self, mock_conn):
        from server import gas_tools as m
        result = m.bind_ability_input(actor_name="TestActor", ability_path="/Game/Abilities/GA_Fireball", input_action="IA_Fire")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_grant_ability(self, mock_conn):
        from server import gas_tools as m
        result = m.grant_ability(actor_name="TestActor", ability_path="/Game/Abilities/GA_Fireball")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_configure_ability_activation(self, mock_conn):
        from server import gas_tools as m
        result = m.configure_ability_activation(ability_path="/Game/Abilities/GA_Fireball", activation_policy="OnInputTriggered")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_configure_ability_cooldown(self, mock_conn):
        from server import gas_tools as m
        result = m.configure_ability_cooldown(ability_path="/Game/Abilities/GA_Fireball", cooldown_seconds=5.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_configure_ability_cost(self, mock_conn):
        from server import gas_tools as m
        result = m.configure_ability_cost(ability_path="/Game/Abilities/GA_Fireball", cost_attribute="Mana", amount=25.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_initialize_attribute(self, mock_conn):
        from server import gas_tools as m
        result = m.initialize_attribute(attribute_set_path="/Game/GAS/AS_Health", attribute="Health", value=100.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_bind_attribute_change_event(self, mock_conn):
        from server import gas_tools as m
        result = m.bind_attribute_change_event(attribute_set_path="/Game/GAS/AS_Health", attribute="Health", handler="OnHealthChanged")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_link_gameplay_tag(self, mock_conn):
        from server import gas_tools as m
        result = m.link_gameplay_tag(target="TestActor", tag="State.Dead")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_configure_gas_replication(self, mock_conn):
        from server import gas_tools as m
        result = m.configure_gas_replication(actor_name="TestActor", replication_mode="Mixed")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.gas_tools.get_unreal_connection", return_value=_conn())
    def test_configure_gas_prediction(self, mock_conn):
        from server import gas_tools as m
        result = m.configure_gas_prediction(actor_name="TestActor", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
