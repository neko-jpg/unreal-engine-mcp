"""Tests for the structured memory module."""

from __future__ import annotations

import time

import pytest

from server.agents.memory import AgentMemory, MemoryEntry


class TestMemoryEntry:
    """Test MemoryEntry dataclass."""

    def test_basic_creation(self):
        entry = MemoryEntry(agent="test_agent", observation="spawned a cube")
        assert entry.agent == "test_agent"
        assert entry.observation == "spawned a cube"
        assert entry.metadata == {}
        assert entry.timestamp > 0
        assert entry.entry_id.startswith("mem_")

    def test_to_dict(self):
        entry = MemoryEntry(
            agent="a", observation="obs", metadata={"key": "val"}, timestamp=123.0
        )
        d = entry.to_dict()
        assert d["agent"] == "a"
        assert d["observation"] == "obs"
        assert d["metadata"] == {"key": "val"}
        assert d["timestamp"] == 123.0
        assert "entry_id" in d

    def test_from_dict(self):
        data = {
            "entry_id": "mem_123",
            "agent": "a",
            "observation": "obs",
            "metadata": {},
            "timestamp": 456.0,
        }
        entry = MemoryEntry.from_dict(data)
        assert entry.entry_id == "mem_123"
        assert entry.agent == "a"
        assert entry.observation == "obs"
        assert entry.timestamp == 456.0


class TestAgentMemory:
    """Test AgentMemory."""

    def test_add_observation(self):
        mem = AgentMemory(scene_id="test")
        entry = mem.add_observation("agent1", "created cave entrance")
        assert len(mem.short_term) == 1
        assert mem.short_term[0] == entry
        assert entry.agent == "agent1"
        assert entry.observation == "created cave entrance"

    def test_get_recent(self):
        mem = AgentMemory()
        mem.add_observation("a", "first")
        mem.add_observation("a", "second")
        mem.add_observation("a", "third")
        recent = mem.get_recent(2)
        assert len(recent) == 2
        assert recent[0].observation == "second"
        assert recent[1].observation == "third"

    def test_get_by_agent(self):
        mem = AgentMemory()
        mem.add_observation("alice", "alice task")
        mem.add_observation("bob", "bob task")
        mem.add_observation("alice", "alice task 2")
        alice_entries = mem.get_by_agent("alice")
        assert len(alice_entries) == 2
        assert all(e.agent == "alice" for e in alice_entries)

    def test_retrieve_relevant(self):
        mem = AgentMemory()
        mem.add_observation("a", "spawned red cube in the cave")
        mem.add_observation("a", "adjusted lighting in the room")
        mem.add_observation("a", "placed a tree outside")
        results = mem.retrieve_relevant("cave lighting", k=2)
        assert len(results) <= 2
        # "cave" matches first entry, "lighting" matches second
        observations = {r.observation for r in results}
        assert "spawned red cube in the cave" in observations

    def test_retrieve_relevant_empty_query(self):
        mem = AgentMemory()
        mem.add_observation("a", "obs1")
        results = mem.retrieve_relevant("", k=5)
        assert len(results) == 1
        assert results[0].observation == "obs1"

    def test_retrieve_by_metadata(self):
        mem = AgentMemory()
        mem.add_observation("a", "obs1", {"domain": "lighting"})
        mem.add_observation("a", "obs2", {"domain": "audio"})
        mem.add_observation("a", "obs3", {"domain": "lighting"})
        results = mem.retrieve_by_metadata("domain", "lighting")
        assert len(results) == 2
        assert all(r.metadata["domain"] == "lighting" for r in results)

    def test_scene_graph(self):
        mem = AgentMemory()
        mem.update_scene_graph({
            "cave_entrance": {"type": "mesh", "location": [0, 0, 0]},
            "torch_01": {"type": "light", "intensity": 1000},
        })
        assert mem.list_scene_nodes() == ["cave_entrance", "torch_01"]
        node = mem.get_scene_node("torch_01")
        assert node == {"type": "light", "intensity": 1000}

    def test_scene_graph_update_existing(self):
        mem = AgentMemory()
        mem.update_scene_graph({"node1": {"x": 1}})
        mem.update_scene_graph({"node1": {"y": 2}})
        node = mem.get_scene_node("node1")
        assert node == {"x": 1, "y": 2}

    def test_long_term_archive(self):
        mem = AgentMemory()
        mem.add_observation("a", "short term 1")
        mem.add_observation("a", "short term 2")
        mem.archive_to_long_term()
        assert len(mem.short_term) == 0
        results = mem.search_long_term("short term", k=5)
        assert len(results) == 2

    def test_long_term_search(self):
        mem = AgentMemory()
        mem.add_observation("a", "cave geometry refined")
        mem.add_observation("a", "foliage painted")
        mem.archive_to_long_term()
        results = mem.search_long_term("cave", k=5)
        assert len(results) == 1
        assert results[0].observation == "cave geometry refined"

    def test_serialization(self):
        mem = AgentMemory(scene_id="s1")
        mem.add_observation("a", "obs1", {"k": "v"})
        mem.update_scene_graph({"n1": {"x": 1}})
        mem.archive_to_long_term()

        data = mem.to_dict()
        restored = AgentMemory.from_dict(data)

        assert restored.scene_id == "s1"
        assert len(restored.short_term) == 0  # archived
        assert len(restored._long_term) == 1
        assert restored.scene_graph == {"n1": {"x": 1}}

    def test_from_dict_defaults(self):
        restored = AgentMemory.from_dict({})
        assert restored.scene_id == "main"
        assert restored.short_term == []
        assert restored.scene_graph == {}
