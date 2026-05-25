"""1000-component scale + idempotency test.

Builds a synthetic patch with 1000 ComponentPatches, applies it twice, and
asserts the second run is a 100% Noop. Also asserts the first run completes
under a relaxed CI threshold.
"""

from __future__ import annotations

import time
from typing import List

import pytest

from helpers.fake_unreal_connection import FakeUnrealConnection
from server.planning.design_patch import (
    ComponentPatch,
    DesignPatch,
    Intent,
    new_patch_id,
)
from server.planning.patch_executor import PatchExecutor


class _Memory:
    def __init__(self):
        self.calls = 0

    def __call__(self, path, payload):
        self.calls += 1
        return {"success": True, "data": {}}


def _intent():
    return Intent(raw_text="stress", scene_id="scale_test", action="modify", mood="creepy", domains=["lighting"])


def _build_patch(n=1000):
    dp = DesignPatch(
        patch_id=new_patch_id(),
        scene_id="scale_test",
        intent=_intent(),
        component_patches=[
            ComponentPatch(
                scene_id="scale_test",
                entity_id=f"actor:torch_{i:04d}",
                component_type="light",
                name="primary",
                properties={"intensity_multiplier": 0.4, "index": i},
                capability_id="light.set_intensity",
            )
            for i in range(n)
        ],
        max_operations=2000,
    )
    dp.fill_component_hashes()
    return dp


def test_1000_component_apply_then_idempotent_second_run():
    dp = _build_patch(1000)
    mem = _Memory()
    fake = FakeUnrealConnection()
    executor = PatchExecutor(scene_syncd=mem, unreal_connection=fake)
    t0 = time.perf_counter()
    r1 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    elapsed_first = time.perf_counter() - t0
    assert r1.succeeded == 1000
    assert r1.failed == 0
    # CI relaxed threshold (no real UE).
    assert elapsed_first < 30.0

    # second run with same executor must be all noop
    r2 = executor.apply(dp, create_snapshot=False, require_safe_only=True)
    assert r2.noop == 1000, f"expected all noops, got noop={r2.noop} succ={r2.succeeded}"
    assert r2.succeeded == 0
