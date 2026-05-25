"""Verify that ambiguous targets are surfaced via requires_approval per plan."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

import server.dialog_tools as dt


class _FakeClient:
    def call_scene_syncd(self, path, payload):
        # empty scene -> no objects to match "the cave" against
        defaults = {
            "/objects/list": {"success": True, "data": {"objects": []}},
            "/entities/list": {"success": True, "data": {"entities": []}},
            "/components/list": {"success": True, "data": {"components": []}},
            "/assets/list": {"success": True, "data": {"assets": []}},
            "/snapshots/list": {"success": True, "data": {"snapshots": []}},
            "/operations/recent": {"success": True, "data": {"operations": []}},
        }
        return defaults.get(path, {"success": True, "data": {}})


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr(dt, "_summarizer_client", lambda: _FakeClient())


def test_ambiguous_target_requires_approval_and_warns():
    res = dt.scene_edit(
        "make something nicer",
        scene_id="ambig",
        mode="dry_run",
        target="something nicer",
    )
    assert res["success"]
    assert res["requires_approval"] is True, "ambiguous target must require approval"
    assert any("target ambiguous" in w for w in res["warnings"]), (
        f"expected ambiguity warning, got warnings={res['warnings']}"
    )
    assert res["risk_level"] in {"review", "destructive"}, res["risk_level"]


def test_explicit_scene_wide_intent_does_not_require_approval():
    """An explicit, fully-resolved scene-wide intent (no pronouns, no target
    selector) should not flag ambiguity even in an empty scene."""
    res = dt.scene_edit(
        "creepy mood overall",  # no "this"/"it" pronouns
        scene_id="not_ambig",
        mode="dry_run",
        target=None,
    )
    assert not any("target ambiguous" in w for w in res["warnings"]), res["warnings"]
    assert res["requires_approval"] is False
