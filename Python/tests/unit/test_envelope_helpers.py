"""Unit tests for utils.envelope (Wave 0 #72)."""

from __future__ import annotations

import pytest

from utils.envelope import (
    EnvelopeAssertionError,
    assert_error,
    assert_executed,
    assert_no_queued,
    is_executed_envelope,
    is_queued_envelope,
)


def test_assert_executed_happy_path():
    result = {"success": True, "data": {"executed": True, "path": "/Game/Foo"}}
    data = assert_executed(result, "create_niagara_system")
    assert data["path"] == "/Game/Foo"


def test_assert_executed_rejects_queued_only():
    result = {"success": True, "data": {"queued": True, "system_path": "/Game/Foo"}}
    with pytest.raises(EnvelopeAssertionError) as exc:
        assert_executed(result, "add_emitter_to_system")
    assert "queued" in str(exc.value)


def test_assert_executed_rejects_legacy_flat_by_default():
    result = {"success": True, "path": "/Game/Foo"}
    with pytest.raises(EnvelopeAssertionError) as exc:
        assert_executed(result, "legacy_flat_handler")
    assert "legacy flat" in str(exc.value)


def test_assert_executed_accepts_legacy_flat_when_opted_in():
    result = {"success": True, "path": "/Game/Foo"}
    data = assert_executed(result, "legacy_flat_handler", allow_legacy=True)
    assert data["path"] == "/Game/Foo"


def test_assert_executed_accepts_status_success_alias():
    result = {"status": "success", "data": {"executed": True, "value": 42}}
    data = assert_executed(result, "alias_status_success")
    assert data["value"] == 42


def test_assert_executed_surfaces_error_with_hint():
    result = {"success": False, "error": "module missing", "hint": "enable plugin"}
    with pytest.raises(EnvelopeAssertionError) as exc:
        assert_executed(result, "set_niagara_color")
    assert "module missing" in str(exc.value)
    assert "enable plugin" in str(exc.value)


def test_assert_no_queued_passes_for_executed():
    result = {"success": True, "data": {"executed": True}}
    assert_no_queued(result, "ok")


def test_assert_no_queued_raises_for_queued():
    result = {"success": True, "data": {"queued": True}}
    with pytest.raises(EnvelopeAssertionError):
        assert_no_queued(result, "regression")


def test_assert_error_happy_path():
    result = {"success": False, "error": "actor not found"}
    out = assert_error(result, "set_actor_transform", expected_substring="actor")
    assert out is result


def test_assert_error_rejects_success_envelopes():
    result = {"success": True, "data": {"executed": True}}
    with pytest.raises(EnvelopeAssertionError):
        assert_error(result, "set_actor_transform")


def test_assert_error_checks_substring():
    result = {"success": False, "error": "nope"}
    with pytest.raises(EnvelopeAssertionError):
        assert_error(result, "set_actor_transform", expected_substring="actor not found")


def test_is_executed_envelope_predicates():
    assert is_executed_envelope({"success": True, "data": {"executed": True}})
    assert not is_executed_envelope({"success": True, "data": {"queued": True}})
    assert not is_executed_envelope({"success": False, "error": "boom"})
    assert not is_executed_envelope("not a dict")


def test_is_queued_envelope_predicates():
    assert is_queued_envelope({"success": True, "data": {"queued": True}})
    assert is_queued_envelope({"success": True, "queued": True})  # legacy flat
    assert not is_queued_envelope({"success": True, "data": {"executed": True}})
    assert not is_queued_envelope({"success": False, "error": "boom"})
