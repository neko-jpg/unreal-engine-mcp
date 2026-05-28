"""Phase 23 handler-split smoke tests (Issue #35).

This is a regression safety net executed *before* the Phase 4 split (#31)
and the Bridge registry refactor (#32).  It exercises one or more JSON
command names per route id that was reorganised by Phase 1 / 2 / 3 (and
that will keep being reorganised by Phase 4) so that any drop-out caused
by the upcoming refactors is caught immediately instead of surfacing as a
silent ``Unknown command`` later.

Routes covered:
- route 1  `ActorCommands`       (`spawn_actor`, `clone_actor`, `apply_scene_delta`)
- route 20 `NavigationCommands`  (`create_nav_mesh_volume`, `create_patrol_route`, `create_spline_from_points`)
- route 22 `PhysicsCommands`     (`set_actor_collision_preset`)
- route 23 `ValidationCommands`  (`compile_all_blueprints`, `run_map_check`)
- route 24 `InstanceCommands`    (`list_instance_sets`)

Acceptance contract (per Issue #35):

1. Command must NOT be reported as ``Unknown command`` by the bridge.
2. With Unreal connected the response envelope must be a success
   (``{"status": "success", "result": {"success": true, ...}}``).
3. With Unreal *not* connected, the test is **skipped** rather than
   failing, so CI can still execute the suite in ``--skip-unreal`` mode.

Run:
    pytest tests/e2e/test_phase23_handler_split_smoke.py            # full E2E with Unreal
    pytest tests/e2e/test_phase23_handler_split_smoke.py --skip-unreal  # skipped lanes only
"""

from __future__ import annotations

import time

import pytest

from .conftest import unreal_command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_unreal_command(command: str, params: dict | None = None) -> dict:
    """Wrap ``unreal_command`` with skip semantics.

    The base ``unreal_command`` raises an OS / connection error when the
    bridge is not reachable.  In a smoke test we want to *skip* in that
    situation instead of failing.
    """
    try:
        return unreal_command(command, params or {})
    except (OSError, ConnectionError) as exc:
        pytest.skip(f"Unreal MCP bridge not reachable for {command!r}: {exc}")


def _assert_dispatched(response: dict, command: str) -> None:
    """Assert the bridge accepted ``command`` (i.e. routing did not fall
    through to the ``Unknown command`` default arm).

    The bridge wraps every reply in either:

    * ``{"status": "success", "result": {...}}`` for routes whose handler
      returned a payload, or
    * ``{"status": "error", "error": "..."}`` when no route matched or
      when the handler short-circuited with an error.

    For *routing*, what we care about is that the error (if any) is not
    the bridge-level ``Unknown command: <name>`` string.  Handler-level
    errors (missing param, actor not found, ...) are acceptable for a
    smoke test because they prove the route resolved.
    """
    assert isinstance(response, dict), f"Non-dict response for {command!r}: {response!r}"
    error_text = str(response.get("error") or "")
    assert "Unknown command" not in error_text, (
        f"Command {command!r} was not routed: {response!r}"
    )


def _is_success_envelope(response: dict) -> bool:
    """True iff the response is a fully-successful envelope."""
    if response.get("status") == "success":
        return True
    if response.get("success") is True:
        return True
    return False


# ---------------------------------------------------------------------------
# Route 1  --  ActorCommands
# ---------------------------------------------------------------------------


@pytest.mark.requires_unreal
class TestRoute1ActorCommands:
    """Smoke: route 1 (`FEpicUnrealMCPActorCommands`)."""

    def test_spawn_actor_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        actor_name = f"E2E_Phase23_Spawn_{time.time_ns()}"
        response = _safe_unreal_command(
            "spawn_actor",
            {
                "type": "StaticMeshActor",
                "name": actor_name,
                "location": [0.0, 0.0, 100.0],
            },
        )
        _assert_dispatched(response, "spawn_actor")
        assert _is_success_envelope(response), (
            f"spawn_actor should succeed when Unreal is up: {response!r}"
        )

        # Best-effort cleanup -- we deliberately do not assert on this
        # so a stale leftover never fails the smoke run.
        try:
            unreal_command("delete_actor", {"name": actor_name})
        except Exception:
            pass

    def test_clone_actor_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        source_name = f"E2E_Phase23_Clone_Src_{time.time_ns()}"
        clone_name = f"{source_name}_Clone"

        spawn_response = _safe_unreal_command(
            "spawn_actor",
            {
                "type": "StaticMeshActor",
                "name": source_name,
                "location": [200.0, 0.0, 100.0],
            },
        )
        _assert_dispatched(spawn_response, "spawn_actor")
        assert _is_success_envelope(spawn_response), (
            f"spawn_actor must succeed for clone test: {spawn_response!r}"
        )

        # C++ may rename the actor; use the returned name if available.
        actual_source_name = (
            spawn_response.get("name")
            or spawn_response.get("actor_name")
            or source_name
        )

        try:
            response = _safe_unreal_command(
                "clone_actor",
                {
                    "source_actor_name": actual_source_name,
                    "new_actor_name": clone_name,
                    "location": [400.0, 0.0, 100.0],
                },
            )
            _assert_dispatched(response, "clone_actor")
            # When the source actor was successfully spawned, the clone
            # must succeed too.  Otherwise the route is fine but the
            # earlier spawn was rejected for an unrelated reason -- the
            # smoke test only guarantees routing in that case.
            if _is_success_envelope(spawn_response):
                assert _is_success_envelope(response), (
                    f"clone_actor should succeed when source exists: {response!r}"
                )
        finally:
            for name in (clone_name, actual_source_name):
                try:
                    unreal_command("delete_actor", {"name": name})
                except Exception:
                    pass

    def test_apply_scene_delta_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        mcp_id = f"e2e_phase23_delta_{time.time_ns()}"
        actor_name = f"E2E_Phase23_Delta_{time.time_ns()}"

        response = _safe_unreal_command(
            "apply_scene_delta",
            {
                "transaction_id": f"phase23_smoke_{time.time_ns()}",
                "creates": [
                    {
                        "name": actor_name,
                        "mcp_id": mcp_id,
                        "type": "StaticMeshActor",
                        "location": [600.0, 0.0, 100.0],
                    }
                ],
                "updates": [],
                "deletes": [],
            },
        )
        _assert_dispatched(response, "apply_scene_delta")
        assert _is_success_envelope(response), (
            f"apply_scene_delta should succeed when Unreal is up: {response!r}"
        )

        try:
            unreal_command("delete_actor_by_mcp_id", {"mcp_id": mcp_id})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Routes 22 / 23 / 24  --  Phase 4 split handlers
# ---------------------------------------------------------------------------


@pytest.mark.requires_unreal
class TestPhase4SplitCommands:
    """Smoke: commands moved out of `FEpicUnrealMCPProceduralCommands`.

    Phase 4 (#31) routes Physics to 22, Validation to 23, and
    Draft/InstanceSet commands to 24 while keeping JSON command names
    unchanged.
    """

    def test_set_actor_collision_preset_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        actor_name = f"E2E_Phase23_Collision_{time.time_ns()}"
        spawn_response = _safe_unreal_command(
            "spawn_actor",
            {
                "type": "StaticMeshActor",
                "name": actor_name,
                "location": [800.0, 0.0, 100.0],
            },
        )
        _assert_dispatched(spawn_response, "spawn_actor")
        assert _is_success_envelope(spawn_response), (
            f"spawn_actor must succeed for collision test: {spawn_response!r}"
        )

        # C++ may rename the actor; use the returned name if available.
        actual_actor_name = (
            spawn_response.get("name")
            or spawn_response.get("actor_name")
            or actor_name
        )

        try:
            response = _safe_unreal_command(
                "set_actor_collision_preset",
                {
                    "actor_name": actual_actor_name,
                    "preset": "BlockAll",
                },
            )
            _assert_dispatched(response, "set_actor_collision_preset")
            if _is_success_envelope(spawn_response):
                assert _is_success_envelope(response), (
                    f"set_actor_collision_preset should succeed: {response!r}"
                )
        finally:
            try:
                unreal_command("delete_actor", {"name": actual_actor_name})
            except Exception:
                pass

    def test_compile_all_blueprints_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        response = _safe_unreal_command("compile_all_blueprints", {})
        _assert_dispatched(response, "compile_all_blueprints")
        # compile_all_blueprints is allowed to report compilation
        # warnings/errors in the payload, but the routing itself must
        # produce a success envelope.
        assert _is_success_envelope(response), (
            f"compile_all_blueprints should succeed when Unreal is up: {response!r}"
        )

    def test_run_map_check_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        response = _safe_unreal_command("run_map_check", {})
        _assert_dispatched(response, "run_map_check")
        assert _is_success_envelope(response), (
            f"run_map_check should succeed when Unreal is up: {response!r}"
        )

    def test_list_instance_sets_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        response = _safe_unreal_command("list_instance_sets", {})
        _assert_dispatched(response, "list_instance_sets")
        assert _is_success_envelope(response), (
            f"list_instance_sets should succeed when Unreal is up: {response!r}"
        )


# ---------------------------------------------------------------------------
# Route 20  --  NavigationCommands  (NavMesh + AI + Spline)
# ---------------------------------------------------------------------------


@pytest.mark.requires_unreal
class TestRoute20NavigationCommands:
    """Smoke: route 20 (`FEpicUnrealMCPNavigationCommands`)."""

    def test_create_nav_mesh_volume_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        volume_name = f"E2E_Phase23_NavMesh_{time.time_ns()}"
        response = _safe_unreal_command(
            "create_nav_mesh_volume",
            {
                "volume_name": volume_name,
                "location": [0.0, 0.0, 0.0],
                "extent": [1000.0, 1000.0, 500.0],
            },
        )
        _assert_dispatched(response, "create_nav_mesh_volume")
        assert _is_success_envelope(response), (
            f"create_nav_mesh_volume should succeed when Unreal is up: {response!r}"
        )

        try:
            unreal_command("delete_actor", {"name": volume_name})
        except Exception:
            pass

    def test_create_patrol_route_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        route_name = f"E2E_Phase23_Patrol_{time.time_ns()}"
        response = _safe_unreal_command(
            "create_patrol_route",
            {
                "patrol_route_name": route_name,
                "points": [
                    {"x": 0.0, "y": 0.0, "z": 0.0},
                    {"x": 500.0, "y": 0.0, "z": 0.0},
                    {"x": 500.0, "y": 500.0, "z": 0.0},
                ],
                "closed_loop": True,
            },
        )
        _assert_dispatched(response, "create_patrol_route")
        assert _is_success_envelope(response), (
            f"create_patrol_route should succeed when Unreal is up: {response!r}"
        )

        try:
            unreal_command("delete_actor", {"name": route_name})
        except Exception:
            pass

    def test_create_spline_from_points_dispatches(self, unreal_available):
        if not unreal_available:
            pytest.skip("Unreal MCP bridge not available")

        spline_name = f"E2E_Phase23_Spline_{time.time_ns()}"
        response = _safe_unreal_command(
            "create_spline_from_points",
            {
                "spline_name": spline_name,
                "points": [
                    {"x": 0.0, "y": 0.0, "z": 0.0},
                    {"x": 200.0, "y": 0.0, "z": 0.0},
                    {"x": 400.0, "y": 200.0, "z": 0.0},
                ],
                "closed_loop": False,
                "tangent_mode": "curve",
                "focus_viewport": False,
            },
        )
        _assert_dispatched(response, "create_spline_from_points")
        assert _is_success_envelope(response), (
            f"create_spline_from_points should succeed when Unreal is up: {response!r}"
        )

        try:
            unreal_command("delete_actor", {"name": spline_name})
        except Exception:
            pass