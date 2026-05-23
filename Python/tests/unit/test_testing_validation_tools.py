"""L1 unit tests for testing_validation_tools (auto-generated scaffold)."""
from unittest.mock import patch, MagicMock
import server.testing_validation_tools as m


def _conn():
    c = MagicMock(); c.send_command.return_value = {"success": True, "data": {}}
    return c


def test_create_ue_automation_test_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.create_ue_automation_test("test_name_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "create_ue_automation_test"


def test_spawn_functional_test_actor_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.spawn_functional_test_actor()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "spawn_functional_test_actor"


def test_run_automation_test_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_automation_test()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_automation_test"


def test_fetch_automation_test_results_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.fetch_automation_test_results()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "fetch_automation_test_results"


def test_run_collision_validation_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_collision_validation()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_collision_validation"


def test_run_navigation_validation_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_navigation_validation()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_navigation_validation"


def test_run_performance_budget_validation_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_performance_budget_validation()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_performance_budget_validation"


def test_run_gameplay_screenshot_test_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_gameplay_screenshot_test("screenshot_id_v")
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_gameplay_screenshot_test"


def test_run_python_unit_test_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_python_unit_test()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_python_unit_test"


def test_run_rust_test_payload():
    with patch("server.testing_validation_tools.get_unreal_connection", return_value=_conn()) as ue:
        m.run_rust_test()
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "run_rust_test"
