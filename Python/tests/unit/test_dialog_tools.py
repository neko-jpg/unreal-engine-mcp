"""Unit tests for dialog_tools.scene_edit (dry_run) and scene_explain_plan."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

import server.dialog_tools as dt
from server.intent.scene_summarizer import SceneSummarizer
from server.planning.design_patch import DesignPatch


class _FakeClient:
    def __init__(self, payloads):
        self.payloads = payloads

    def call_scene_syncd(self, path, payload):
        return {"success": True, "data": self.payloads.get(path, {})}


def _cave_payloads():
    return {
        "/objects/list": {"objects": [
            {"mcp_id": "torch_01", "kind": "light", "name": "torch_01", "tags": ["torch", "wall", "cave"]},
            {"mcp_id": "torch_02", "kind": "light", "name": "torch_02", "tags": ["torch", "wall"]},
            {"mcp_id": "floor_01", "kind": "floor", "name": "floor_01", "tags": ["stone"]},
            {"mcp_id": "wall_n", "kind": "wall", "name": "wall_n", "tags": ["stone"]},
        ]},
        "/entities/list": {"entities": []},
        "/components/list": {"components": []},
        "/assets/list": {"assets": []},
        "/snapshots/list": {"snapshots": []},
        "/operations/recent": {"operations": []},
    }


@pytest.fixture(autouse=True)
def _patch_summarizer(monkeypatch):
    monkeypatch.setattr(
        dt, "_summarizer_client", lambda: _FakeClient(_cave_payloads())
    )


def test_scene_edit_dry_run_creates_patch_in_store():
    res = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="dry_run")
    assert res["success"]
    assert res["mode"] == "dry_run"
    assert res["operation_count"] >= 6  # at minimum 2 lights + 1 atm + 2 audio + 1 vfx
    assert res["risk_level"] in {"safe", "review"}
    store = dt.get_patch_store()
    assert store.get(res["patch_id"]) is not None


def test_scene_edit_dry_run_marks_destructive_when_keyword_present():
    res = dt.scene_edit("delete all torch lights", scene_id="cave_test", mode="dry_run", target="torch")
    assert res["risk_level"] == "destructive"
    assert res["requires_approval"] is True


def test_scene_explain_plan_returns_markdown_and_json():
    plan = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="dry_run")
    res = dt.scene_explain_plan(plan["patch_id"])
    assert res["success"]
    assert "## Patch" in res["markdown"]
    assert res["json"]["patch_id"] == plan["patch_id"]


def test_scene_explain_plan_unknown_id():
    res = dt.scene_explain_plan("patch_does_not_exist")
    assert res["success"] is False


def test_scene_edit_unknown_mode_falls_back_to_dry_run_with_warning():
    res = dt.scene_edit("make this cave creepy", scene_id="cave_test", mode="unsupported")
    assert res["success"]
    assert any("unsupported mode" in w for w in res["warnings"])
