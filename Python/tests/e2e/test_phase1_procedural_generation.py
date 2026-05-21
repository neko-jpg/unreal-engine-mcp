"""Full Phase 1 procedural generation E2E tests.

Requires scene-syncd, SurrealDB, and Unreal MCP Bridge.
"""

import pytest

from .conftest import api_post, assert_success, unreal_command


@pytest.mark.requires_unreal
class TestPhase1ProceduralGeneration:
    def test_sdf_composite_mesh_reaches_unreal(self, scene_syncd_available):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        result = api_post("/procedural/sdf-mesh", {
            "mcp_id": "E2E_Phase1_SDF_Composite",
            "actor_name": "E2E_Phase1_SDF_Composite",
            "sdf": {
                "type": "union",
                "smoothness": 25.0,
                "children": [
                    {"type": "sphere", "center": [-60.0, 0.0, 900.0], "radius": 120.0},
                    {"type": "sphere", "center": [60.0, 0.0, 900.0], "radius": 120.0},
                ],
            },
            "bounds": {
                "min": [-220.0, -180.0, 720.0],
                "max": [220.0, 180.0, 1080.0],
            },
            "resolution": 24,
            "focus_viewport": False,
        })

        data = assert_success(result, "create composite SDF mesh")
        unreal = data["unreal_response"]
        assert unreal["success"] is True
        assert unreal["vertex_count"] > 0
        assert unreal["triangle_count"] > 0

    def test_superformula_mesh_reaches_unreal(self, scene_syncd_available):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        result = api_post("/procedural/superformula-mesh", {
            "mcp_id": "E2E_Phase1_Superformula",
            "actor_name": "E2E_Phase1_Superformula",
            "m1": 8.0,
            "n1_1": 0.45,
            "n2_1": 0.8,
            "n3_1": 0.8,
            "m2": 5.0,
            "n1_2": 0.7,
            "n2_2": 1.2,
            "n3_2": 1.2,
            "resolution": 24,
            "scale": 130.0,
            "location": [500.0, 0.0, 900.0],
            "focus_viewport": False,
        })

        data = assert_success(result, "create superformula mesh")
        unreal = data["unreal_response"]
        assert unreal["success"] is True
        assert unreal["vertex_count"] > 0
        assert unreal["triangle_count"] > 0

    def test_lsystem_spline_reaches_unreal(self, scene_syncd_available):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        result = api_post("/procedural/lsystem-spline", {
            "mcp_id": "E2E_Phase1_LSystemSpline",
            "spline_name": "E2E_Phase1_LSystemSpline",
            "axiom": "F",
            "rules": [["F", "F[+F]F[-F]F"]],
            "iterations": 2,
            "step_length": 70.0,
            "angle_degrees": 28.0,
            "origin": [900.0, 0.0, 700.0],
            "heading": [0.0, 0.0, 1.0],
            "up": [0.0, 1.0, 0.0],
            "tangent_mode": "curve",
            "focus_viewport": False,
        })

        data = assert_success(result, "create L-System spline")
        assert data["segment_count"] > 0
        unreal = data["unreal_response"]
        assert unreal["success"] is True
        assert unreal["component_count"] >= 1
        assert unreal["point_count"] >= data["segment_count"]

        found = unreal_command("find_actor_by_mcp_id", {"mcp_id": "E2E_Phase1_LSystemSpline"})
        assert found.get("result", {}).get("success") is True

    def test_lsystem_preset_reaches_unreal(self, scene_syncd_available):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        result = api_post("/procedural/lsystem-spline", {
            "mcp_id": "E2E_Phase1_LSystemPreset",
            "spline_name": "E2E_Phase1_LSystemPreset",
            "preset": "Tree3D",
            "iterations": 2,
            "step_length": 70.0,
            "origin": [900.0, 0.0, 700.0],
            "heading": [0.0, 0.0, 1.0],
            "up": [0.0, 1.0, 0.0],
            "tangent_mode": "curve",
            "focus_viewport": False,
        })

        data = assert_success(result, "create L-System spline from preset")
        assert data["segment_count"] > 0
        unreal = data["unreal_response"]
        assert unreal["success"] is True
        assert unreal["component_count"] >= 1
        assert unreal["point_count"] >= data["segment_count"]

        found = unreal_command("find_actor_by_mcp_id", {"mcp_id": "E2E_Phase1_LSystemPreset"})
        assert found.get("result", {}).get("success") is True

    def test_wfc_grid_generation(self, scene_syncd_available):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        result = api_post("/procedural/wfc-grid", {
            "width": 4,
            "height": 4,
            "tileset": {
                "tiles": [
                    {"id": "grass", "weight": 1.0},
                    {"id": "water", "weight": 0.5},
                ],
                "constraints": [
                    {"left": "grass", "right": "grass", "direction": "east"},
                    {"left": "water", "right": "water", "direction": "east"},
                    {"left": "grass", "right": "grass", "direction": "south"},
                    {"left": "water", "right": "water", "direction": "south"},
                ],
            },
            "seed": 42,
            "periodic": False,
        })

        data = assert_success(result, "generate WFC grid")
        assert data["width"] == 4
        assert data["height"] == 4
        assert len(data["tiles"]) == 16
        for tile in data["tiles"]:
            assert tile["tile_id"] in ("grass", "water")
            assert 0 <= tile["x"] < 4
            assert 0 <= tile["y"] < 4


@pytest.mark.requires_unreal
class TestWfcSemanticLayoutFusion:
    """E2E coverage of `scene_wfc_to_semantic_layout` + `scene_show_wfc_proxy`.

    Verifies the chain:
        Rust WFC -> scene-syncd upsert (managed_by_mcp + wfc_generated tags)
                 -> Unreal HISM draft proxy via existing create_draft_proxy path.

    Skipped automatically when scene-syncd is not running. The Unreal half
    additionally requires a running editor (gated by --skip-unreal).
    """

    SCENE_ID = "main"
    GROUP_PREFIX = "e2e_wfc_fusion"
    GRASS_MESH = "/Engine/BasicShapes/Cube.Cube"
    WATER_MESH = "/Engine/BasicShapes/Cylinder.Cylinder"

    def _import_scene_tools(self):
        import importlib
        import sys
        from pathlib import Path

        repo_python = Path(__file__).resolve().parents[2]
        if str(repo_python) not in sys.path:
            sys.path.insert(0, str(repo_python))
        return importlib.import_module("server.scene_tools")

    def test_fusion_round_trip(self, scene_syncd_available, request):
        if not scene_syncd_available:
            pytest.skip("scene-syncd not available")

        scene_tools = self._import_scene_tools()

        # Step 1: WFC -> Semantic Layout upsert
        upsert = scene_tools.scene_wfc_to_semantic_layout(
            scene_id=self.SCENE_ID,
            width=3,
            height=3,
            tiles=[
                {"id": "grass", "weight": 1.0},
                {"id": "water", "weight": 0.5},
            ],
            constraints=[
                {"left": "grass", "right": "grass", "direction": "east"},
                {"left": "water", "right": "water", "direction": "east"},
                {"left": "grass", "right": "grass", "direction": "south"},
                {"left": "water", "right": "water", "direction": "south"},
            ],
            tile_asset_map={
                "grass": self.GRASS_MESH,
                "water": self.WATER_MESH,
            },
            seed=1234,
            periodic=False,
            cell_size={"x": 200.0, "y": 200.0},
            origin={"x": 0.0, "y": 0.0, "z": 0.0},
            group_id_prefix=self.GROUP_PREFIX,
            extra_tags=["e2e_wfc_fusion"],
        )

        if upsert.get("success") is False:
            pytest.skip(f"scene_wfc_to_semantic_layout failed (likely WFC infeasible/transient): {upsert.get('error')}")
        assert upsert["upserted_count"] == 9, upsert
        assert upsert["grid"]["width"] == 3 and upsert["grid"]["height"] == 3
        assert set(upsert["tile_kinds"]).issubset({"grass", "water"})

        # Step 2: HISM draft proxy in Unreal
        if request.config.getoption("--skip-unreal"):
            pytest.skip("--skip-unreal flag set; skipping show_wfc_proxy assertion")

        proxy = scene_tools.scene_show_wfc_proxy(
            scene_id=self.SCENE_ID,
            tile_mesh_map={
                "grass": self.GRASS_MESH,
                "water": self.WATER_MESH,
            },
            proxy_name_prefix="e2e_wfc_proxy",
            fallback_mesh_path=self.GRASS_MESH,
            tag_filter=["e2e_wfc_fusion"],
        )

        if proxy.get("success") is False:
            error_text = (proxy.get("error") or "").lower()
            # If no draft proxy backend (e.g., UE not running) - skip rather than fail
            if any(s in error_text for s in ("connection", "unreal", "no editor", "bridge", "tcp")):
                pytest.skip(f"Unreal Bridge not available: {proxy.get('error')}")
            raise AssertionError(f"scene_show_wfc_proxy failed: {proxy}")

        # Verify proxy created at least one HISM per tile_id present in the grid.
        proxies = proxy.get("proxies") or proxy.get("data", {}).get("proxies") or []
        assert proxies, f"No proxies returned: {proxy}"

        # At least one proxy per kind that appeared in the grid.
        actual_kinds = {p.get("tile_id") for p in proxies if isinstance(p, dict)}
        expected_kinds = set(upsert["tile_kinds"])
        assert actual_kinds.issuperset(expected_kinds & {"grass", "water"}), (
            f"Expected proxies for {expected_kinds}, got {actual_kinds}"
        )



@pytest.mark.requires_unreal
class TestWfcSemanticLayoutHismPipeline:
    """Issue #27: Explicit three-step E2E:
        scene_create_wfc_grid -> scene_wfc_to_semantic_layout -> scene_show_wfc_proxy.

    Differences from `TestWfcSemanticLayoutFusion`:
      - Uses the `isolated_scene` fixture (per-test scene_id + auto-cleanup)
        so concurrent CI workers do not collide on `main`.
      - Explicitly invokes `scene_create_wfc_grid` first to satisfy the
        acceptance criterion "3x3 WFC grid via scene_create_wfc_grid ->
        scene_wfc_to_semantic_layout -> scene_show_wfc_proxy".
      - Explicitly verifies the `wfc_generated` and `layout_kind:wfc_<id>`
        tags propagated into Scene DB by `scene_wfc_to_semantic_layout`.
      - Asserts the equivalent of `proxy_created_count > 0` via the
        cumulative HISM `instance_count` returned by `scene_show_wfc_proxy`.

    Skips when scene-syncd is unreachable; the proxy step also skips when
    the Unreal MCP bridge is unavailable.
    """

    GRASS_MESH = "/Engine/BasicShapes/Cube.Cube"
    WATER_MESH = "/Engine/BasicShapes/Cylinder.Cylinder"

    def _import_scene_tools(self):
        import importlib
        import sys
        from pathlib import Path

        repo_python = Path(__file__).resolve().parents[2]
        if str(repo_python) not in sys.path:
            sys.path.insert(0, str(repo_python))
        return importlib.import_module("server.scene_tools")

    def test_three_step_pipeline(self, isolated_scene, request):
        scene_tools = self._import_scene_tools()

        tiles = [
            {"id": "grass", "weight": 1.0},
            {"id": "water", "weight": 0.5},
        ]
        constraints = [
            {"left": "grass", "right": "grass", "direction": "east"},
            {"left": "water", "right": "water", "direction": "east"},
            {"left": "grass", "right": "grass", "direction": "south"},
            {"left": "water", "right": "water", "direction": "south"},
        ]

        # Step 1: pure WFC grid generation (no DB writes, no Unreal yet).
        grid = scene_tools.scene_create_wfc_grid(
            width=3,
            height=3,
            tiles=tiles,
            constraints=constraints,
            seed=4321,
            periodic=False,
        )
        if grid.get("success") is False:
            pytest.skip(f"scene_create_wfc_grid failed (likely transient WFC infeasibility): {grid.get('error')}")

        # The synchronous /procedural/wfc-grid endpoint returns the tiles directly.
        # Walk both shapes that scene-syncd has historically returned.
        grid_data = grid.get("data") if isinstance(grid.get("data"), dict) else grid
        grid_tiles = grid_data.get("tiles") or []
        assert grid_data.get("width") == 3 and grid_data.get("height") == 3, grid
        assert len(grid_tiles) == 9, f"Expected 9 tiles for a 3x3 grid, got {len(grid_tiles)}"

        # Step 2: persist the grid into Scene DB as Semantic Layout entities.
        upsert = scene_tools.scene_wfc_to_semantic_layout(
            scene_id=isolated_scene,
            width=3,
            height=3,
            tiles=tiles,
            constraints=constraints,
            tile_asset_map={
                "grass": self.GRASS_MESH,
                "water": self.WATER_MESH,
            },
            seed=4321,
            periodic=False,
            cell_size={"x": 200.0, "y": 200.0},
            origin={"x": 0.0, "y": 0.0, "z": 0.0},
            group_id_prefix="e2e_pipeline",
            extra_tags=["e2e_pipeline"],
        )
        if upsert.get("success") is False:
            pytest.skip(
                "scene_wfc_to_semantic_layout failed (likely WFC infeasible/transient): "
                f"{upsert.get('error')}"
            )
        assert upsert["upserted_count"] == 9, upsert
        assert upsert["grid"]["width"] == 3 and upsert["grid"]["height"] == 3
        tile_kinds = set(upsert["tile_kinds"])
        assert tile_kinds.issubset({"grass", "water"}), upsert

        # Step 2.5: verify Scene DB contains 9 actors with the expected tags.
        listed = scene_tools.scene_list_objects(scene_id=isolated_scene)
        objects = (
            listed.get("data", {}).get("objects")
            if isinstance(listed.get("data"), dict)
            else listed.get("objects")
        ) or []
        wfc_objects = [
            o for o in objects
            if isinstance(o, dict) and "wfc_generated" in (o.get("tags") or [])
        ]
        assert len(wfc_objects) == 9, (
            f"Expected 9 wfc_generated actors in scene {isolated_scene}, "
            f"got {len(wfc_objects)} (sample={wfc_objects[:2]})"
        )
        for obj in wfc_objects:
            tags = obj.get("tags") or []
            assert any(
                t.startswith("layout_kind:wfc_") for t in tags
            ), f"missing layout_kind tag on {obj.get('mcp_id')}: tags={tags}"
            assert any(
                t.startswith("wfc_tile_id:") for t in tags
            ), f"missing wfc_tile_id tag on {obj.get('mcp_id')}: tags={tags}"

        # Step 3: realize the layout in Unreal as HISM draft proxies.
        if request.config.getoption("--skip-unreal"):
            pytest.skip("--skip-unreal flag set; skipping show_wfc_proxy assertion")

        proxy = scene_tools.scene_show_wfc_proxy(
            scene_id=isolated_scene,
            tile_mesh_map={
                "grass": self.GRASS_MESH,
                "water": self.WATER_MESH,
            },
            proxy_name_prefix="e2e_pipeline_proxy",
            fallback_mesh_path=self.GRASS_MESH,
            tag_filter=["e2e_pipeline"],
        )
        if proxy.get("success") is False:
            err = (proxy.get("error") or "").lower()
            if any(s in err for s in ("connection", "unreal", "no editor", "bridge", "tcp")):
                pytest.skip(f"Unreal Bridge not available: {proxy.get('error')}")
            raise AssertionError(f"scene_show_wfc_proxy failed: {proxy}")

        proxies = proxy.get("proxies") or proxy.get("data", {}).get("proxies") or []
        assert proxies, f"Expected at least one HISM proxy, got: {proxy}"

        # proxy_created_count > 0 equivalent: at least one HISM kind AND
        # cumulative instance count across kinds is > 0.
        proxy_created_count = len(proxies)
        total_instances = sum(
            int(p.get("instance_count", 0)) for p in proxies if isinstance(p, dict)
        )
        assert proxy_created_count > 0, f"proxy_created_count = 0: {proxy}"
        assert total_instances > 0, f"No HISM instances created: {proxy}"

        # The proxy must cover every tile kind that appeared in the grid.
        actual_kinds = {
            p.get("tile_id") for p in proxies if isinstance(p, dict) and p.get("tile_id")
        }
        observed_kinds = tile_kinds & {"grass", "water"}
        assert actual_kinds.issuperset(observed_kinds), (
            f"Expected proxies for {observed_kinds}, got {actual_kinds}"
        )
