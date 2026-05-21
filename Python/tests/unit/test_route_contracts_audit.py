"""Smoke test for scripts/audit_route_contracts.py (中長期-5)."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_route_contracts.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_route_contracts", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_route_contracts"] = module
    spec.loader.exec_module(module)
    return module


def test_collect_python_send_commands_returns_dict():
    module = _load_module()
    result = module.collect_python_send_commands()
    assert isinstance(result, dict)
    # Should find at least one known command from scene_sync_tools.py
    assert any("spawn_instance_set" == k for k in result.keys())


def test_collect_rust_routes_returns_dict():
    module = _load_module()
    result = module.collect_rust_routes()
    assert isinstance(result, dict)
    # Should include the new streaming endpoint added in 中長期-3
    assert "/sync/apply-stream" in result
    # And the existing endpoints
    assert "/sync/plan" in result
    assert "/sync/apply" in result


def test_collect_cpp_handlers_finds_instance_dispatch():
    module = _load_module()
    result = module.collect_cpp_handlers()
    assert isinstance(result, dict)
    # The InstanceCommands dispatch table registers these
    for name in [
        "spawn_instance_set",
        "update_instance_set",
        "delete_instance_set",
        "list_instance_sets",
    ]:
        assert name in result, f"missing cpp handler for {name}: {sorted(result.keys())[:10]}"


def test_main_writes_csv(tmp_path):
    module = _load_module()
    output = tmp_path / "report.csv"
    exit_code = module.main(["--output", str(output)])
    assert exit_code == 0
    assert output.exists()
    with output.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert rows, "CSV report should not be empty"
    assert all(
        set(row.keys())
        == {"command_name", "python_callers", "rust_routes", "cpp_handlers", "layers"}
        for row in rows
    )


def test_rust_route_normalization():
    module = _load_module()
    fn = module._rust_route_to_command_name
    assert fn("/sync/plan") == "sync_plan"
    assert fn("/sync/apply-stream") == "sync_apply-stream"
    # Curly-brace path params are flattened to "_<name>" and adjacent
    # underscores collapse, so /generator-runs/{run_id} -> generator-runs_run_id
    assert fn("/generator-runs/{run_id}") == "generator-runs_run_id"
