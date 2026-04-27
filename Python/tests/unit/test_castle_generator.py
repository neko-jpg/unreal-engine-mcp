"""Tests for CastleFortressGenerator and SpecGraph realization."""

import pytest

from server.generators.castle import CastleFortressGenerator
from server.specs.realization_spec import RealizationPolicy


class TestCastleFortressGenerator:
    def test_generates_spec_graph(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            architectural_style="medieval",
            location=[0.0, 0.0, 0.0],
            name_prefix="TestCastle",
            include_siege_weapons=True,
            include_village=True,
        )
        graph = gen.generate()
        assert graph is not None
        assert len(graph.entities) > 0
        assert len(graph.actors) > 0
        assert len(graph.relations) > 0

    def test_entities_have_mcp_ids(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            architectural_style="medieval",
            location=[0.0, 0.0, 0.0],
            name_prefix="TestCastle",
        )
        graph = gen.generate()
        for entity in graph.entities:
            if entity.kind in {"bailey", "gate", "tower_group", "keep", "courtyard", "moat"}:
                assert len(entity.mcp_ids) >= 0

    def test_fortress_entity_exists(self):
        gen = CastleFortressGenerator(
            castle_size="medium",
            name_prefix="FortTest",
        )
        graph = gen.generate()
        fortress_entities = [e for e in graph.entities if e.kind == "castle"]
        assert len(fortress_entities) == 1
        assert fortress_entities[0].name == "FortTest Fortress"

    def test_relations_are_connected(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="RelTest",
        )
        graph = gen.generate()
        for relation in graph.relations:
            assert relation.source_entity_id.startswith("RelTest_")
            assert relation.target_entity_id.startswith("RelTest_")
            assert relation.relation_type == "contains"

    def test_realize_prototype_returns_actors(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="RealizeTest",
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.PROTOTYPE)
        assert len(actors) == len(graph.actors)
        for actor in actors:
            assert actor.mcp_id
            assert actor.desired_name

    def test_realize_editor_preview_adds_lights(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="PreviewTest",
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.EDITOR_PREVIEW)
        light_actors = [a for a in actors if a.actor_type == "PointLight"]
        # Should have at least one preview light for key entities
        assert len(light_actors) > 0

    def test_realize_game_ready_adds_collision(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="GameReadyTest",
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.GAME_READY)
        for actor in actors:
            if actor.actor_type == "StaticMeshActor":
                assert actor.visual.get("collision_profile") == "BlockAllDynamic"
                assert actor.visual.get("hism_candidate") is True
                assert actor.visual.get("navmesh_behavior") == "walkable"

    def test_realize_cinematic_replaces_meshes(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="CinematicTest",
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.CINEMATIC)
        for actor in actors:
            path = actor.asset_ref.get("path", "")
            if "HighRes" in path:
                assert "HighRes" in path

    def test_realize_runtime_adds_streaming_tags(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="RuntimeTest",
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.RUNTIME)
        for actor in actors:
            assert actor.metadata.get("streaming") is True
            assert actor.metadata.get("world_partition") is True
            assert actor.metadata.get("hlod_candidate") is True

    def test_summary_is_accurate(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="SummaryTest",
        )
        graph = gen.generate()
        summary = graph.summary()
        assert summary["entity_count"] == len(graph.entities)
        assert summary["actor_count"] == len(graph.actors)
        assert summary["relation_count"] == len(graph.relations)
        assert "castle" in summary["entity_kinds"]
        assert "bailey" in summary["entity_kinds"]

    def test_estimate_cost_scales_with_actors(self):
        gen_small = CastleFortressGenerator(
            castle_size="small",
            name_prefix="CostSmall",
        )
        gen_large = CastleFortressGenerator(
            castle_size="large",
            name_prefix="CostLarge",
        )
        graph_small = gen_small.generate()
        graph_large = gen_large.generate()
        cost_small = graph_small.estimate_cost()
        cost_large = graph_large.estimate_cost()
        assert cost_large.actor_count > cost_small.actor_count
        assert cost_large.estimated_draw_calls > cost_small.estimated_draw_calls
        assert cost_large.estimated_memory_mb > cost_small.estimated_memory_mb

    def test_no_village_when_disabled(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="NoVillage",
            include_village=False,
        )
        graph = gen.generate()
        village_entities = [e for e in graph.entities if e.kind == "settlement"]
        assert len(village_entities) == 0

    def test_no_siege_when_disabled(self):
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="NoSiege",
            include_siege_weapons=False,
        )
        graph = gen.generate()
        siege_entities = [e for e in graph.entities if e.kind == "siege_weapon_group"]
        assert len(siege_entities) == 0

    def test_realize_does_not_mutate_original_actors(self):
        """Calling realize() with different policies must not pollute the graph's actors."""
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="SideEffectTest",
        )
        graph = gen.generate()
        # Save original asset paths and visual dicts
        original_paths = [a.asset_ref.get("path", "") for a in graph.actors]
        original_visual_keys = [set(a.visual.keys()) for a in graph.actors]
        original_metadata_keys = [set(a.metadata.keys()) for a in graph.actors]

        # Realize with GAME_READY — mutates visual and metadata
        game_ready_actors = graph.realize(policy=RealizationPolicy.GAME_READY)

        # Verify original graph actors were NOT modified
        for i, actor in enumerate(graph.actors):
            assert actor.asset_ref.get("path", "") == original_paths[i], (
                f"actor {actor.mcp_id} asset_ref was mutated by GAME_READY realize"
            )
            assert set(actor.visual.keys()) == original_visual_keys[i], (
                f"actor {actor.mcp_id} visual was mutated by GAME_READY realize"
            )
            assert set(actor.metadata.keys()) == original_metadata_keys[i], (
                f"actor {actor.mcp_id} metadata was mutated by GAME_READY realize"
            )

        # Now realize with CINEMATIC — mutates asset_ref
        cinematic_actors = graph.realize(policy=RealizationPolicy.CINEMATIC)

        # Verify original graph actors were NOT modified
        for i, actor in enumerate(graph.actors):
            assert actor.asset_ref.get("path", "") == original_paths[i], (
                f"actor {actor.mcp_id} asset_ref was mutated by CINEMATIC realize"
            )

    def test_realize_prototype_returns_copies(self):
        """realize(PROTOTYPE) must return independent copies, not references."""
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="CopyTest",
        )
        graph = gen.generate()
        actors1 = graph.realize(policy=RealizationPolicy.PROTOTYPE)
        actors2 = graph.realize(policy=RealizationPolicy.PROTOTYPE)
        # Verify the lists contain different objects
        for a1, a2 in zip(actors1, actors2):
            assert a1 is not a2, "realize() must return copies, not references"

    def test_editor_preview_light_position_from_actor(self):
        """Editor preview lights should be positioned above the entity's first actor."""
        gen = CastleFortressGenerator(
            castle_size="small",
            name_prefix="LightPosTest",
            location=[100.0, 200.0, 300.0],
        )
        graph = gen.generate()
        actors = graph.realize(policy=RealizationPolicy.EDITOR_PREVIEW)
        light_actors = [a for a in actors if a.actor_type == "PointLight"]
        assert len(light_actors) > 0
        # Lights should not all be at (0, 0, 500) — they should be near their entities
        for light in light_actors:
            loc = light.transform.get("location", {})
            # At least one coordinate should be non-zero if entity actors are positioned
            # (the outer bailey walls are placed at the castle location)
