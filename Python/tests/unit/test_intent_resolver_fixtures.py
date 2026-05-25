"""50-fixture regression test for IntentResolver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from server.intent.intent_resolver import resolve_intent
from server.intent.intent_types import Intent


HERE = Path(__file__).resolve()
FIXTURES = json.loads(
    (HERE.parent.parent / "fixtures" / "intent_fixtures.json").read_text(encoding="utf-8")
)["fixtures"]


def _ids(fixtures: List[Dict[str, Any]]) -> List[str]:
    return [f["id"] for f in fixtures]


@pytest.mark.parametrize("fixture", FIXTURES, ids=_ids(FIXTURES))
def test_intent_fixture(fixture):
    res = resolve_intent(fixture["raw"], scene_id="main", target=fixture.get("target"))
    intent: Intent = res.intent
    assert isinstance(intent, Intent)

    if "expect_action" in fixture:
        assert intent.action == fixture["expect_action"], (
            f"fixture {fixture['id']} expected action {fixture['expect_action']}, got {intent.action}"
        )

    if "expect_mood" in fixture and fixture["expect_mood"] is not None:
        assert intent.mood == fixture["expect_mood"], (
            f"fixture {fixture['id']} expected mood {fixture['expect_mood']}, got {intent.mood}"
        )

    if "expect_domains" in fixture:
        assert sorted(intent.domains) == sorted(fixture["expect_domains"]), (
            f"fixture {fixture['id']} expected domains {fixture['expect_domains']}, got {intent.domains}"
        )

    if "expect_domains_min" in fixture:
        for d in fixture["expect_domains_min"]:
            assert d in intent.domains, (
                f"fixture {fixture['id']} expected domain {d} in {intent.domains}"
            )

    if "expect_risk" in fixture:
        assert intent.risk_hint == fixture["expect_risk"], (
            f"fixture {fixture['id']} expected risk_hint {fixture['expect_risk']}, got {intent.risk_hint}"
        )


def test_fifty_fixtures_present():
    assert len(FIXTURES) >= 50


def test_japanese_creepy_cave_intent_infers_creepy_mood_and_domains():
    res = resolve_intent("洞窟を不気味にして", scene_id="cave_test")
    assert res.intent.action == "modify"
    assert res.intent.mood == "creepy"
    assert {"lighting", "material", "atmosphere", "audio", "vfx"}.issubset(set(res.intent.domains))
