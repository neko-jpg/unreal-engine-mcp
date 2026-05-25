"""Unit tests for server.planning.design_patch."""

import pytest

from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
    Intent,
    compute_component_key,
    compute_desired_hash,
    compute_operation_id,
    new_patch_id,
)


def _intent(scene_id="main"):
    return Intent(raw_text="test", scene_id=scene_id, action="modify")


def test_compute_desired_hash_is_deterministic_and_order_independent():
    a = {"x": 1, "y": [1, 2], "nested": {"a": 1, "b": 2}}
    b = {"y": [1, 2], "x": 1, "nested": {"b": 2, "a": 1}}
    assert compute_desired_hash(a) == compute_desired_hash(b)


def test_compute_desired_hash_changes_when_value_changes():
    assert compute_desired_hash({"x": 1, "y": 2}) != compute_desired_hash({"x": 1, "y": 3})


def test_component_key_uses_pipe_separator():
    assert (
        compute_component_key("main", "actor:foo", "material", "creepy_stone")
        == "main|actor:foo|material|creepy_stone"
    )


def test_compute_operation_id_is_idempotent():
    key = compute_component_key("main", "actor:foo", "material", "x")
    h = compute_desired_hash({"a": 1})
    op = compute_operation_id("patch_1", key, h)
    op2 = compute_operation_id("patch_1", key, h)
    assert op == op2 and len(op) == 40


def test_fill_derived_populates_hash_and_op_id():
    cp = ComponentPatch(
        scene_id="main",
        entity_id="actor:foo",
        component_type="material",
        name="creepy",
        properties={"BaseColor": [0.1, 0.1, 0.1, 1.0]},
    )
    cp.fill_derived("patch_xyz")
    assert cp.desired_hash and cp.operation_id
    op1 = cp.operation_id
    cp.fill_derived("patch_xyz")
    assert cp.operation_id == op1


def test_new_patch_id_prefixed():
    assert new_patch_id().startswith("patch_")


def test_design_patch_to_dict_and_counts():
    dp = DesignPatch(
        patch_id="patch_test",
        scene_id="main",
        intent=_intent(),
        component_patches=[
            ComponentPatch(
                scene_id="main", entity_id="actor:a", component_type="material",
                name="m1", properties={"BaseColor": [0, 0, 0, 1]},
            ),
            ComponentPatch(
                scene_id="main", entity_id="actor:b", component_type="light",
                name="l1", properties={"intensity": 0.5},
            ),
        ],
    )
    dp.fill_component_hashes()
    payload = dp.to_dict()
    assert payload["operation_count"] == 2
    assert len(payload["component_patches"]) == 2
    assert payload["intent"]["scene_id"] == "main"
    assert all(cp["desired_hash"] for cp in payload["component_patches"])
