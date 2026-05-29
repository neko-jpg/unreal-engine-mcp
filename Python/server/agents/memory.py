"""Structured memory for agent context persistence.

References:
- Mem0 (episodic + semantic memory)
- Zep (long-term memory for agents)
- GraphRAG (scene graph as structured knowledge)

AgentMemory provides short-term session memory, long-term retrieval,
and a scene graph that represents the 3D world semantically.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """A single observation or event in agent memory."""

    agent: str
    observation: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    entry_id: str = field(default_factory=lambda: f"mem_{time.time_ns()}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent": self.agent,
            "observation": self.observation,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            entry_id=data.get("entry_id", f"mem_{time.time_ns()}"),
            agent=data["agent"],
            observation=data["observation"],
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


class AgentMemory:
    """Structured memory shared across agents in a session.

    Provides:
    - **short_term**: Episodic memory for the current session.
    - **scene_graph**: Semantic 3D scene representation.
    - **long_term**: Simple keyword-indexed retrieval (placeholder for RAG).
    """

    def __init__(self, scene_id: str = "main") -> None:
        self.scene_id = scene_id
        self.short_term: List[MemoryEntry] = []
        self.scene_graph: Dict[str, Any] = {}
        self._long_term: List[MemoryEntry] = []
        self._keyword_index: Dict[str, List[int]] = {}

    # ------------------------------------------------------------------
    # Short-term memory
    # ------------------------------------------------------------------

    def add_observation(
        self,
        agent: str,
        observation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Record an observation into short-term memory."""
        entry = MemoryEntry(
            agent=agent,
            observation=observation,
            metadata=metadata or {},
        )
        self.short_term.append(entry)
        self._index_entry(entry, len(self.short_term) - 1)
        return entry

    def get_recent(self, n: int = 5) -> List[MemoryEntry]:
        """Get the most recent *n* short-term entries."""
        return self.short_term[-n:]

    def get_by_agent(self, agent: str) -> List[MemoryEntry]:
        """Get all entries from a specific agent."""
        return [e for e in self.short_term if e.agent == agent]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_relevant(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """Retrieve entries relevant to *query*.

        Uses a simple keyword overlap scorer.  Production systems may
        replace this with a proper vector store (e.g. Chroma, Qdrant).
        """
        query_words = set(query.lower().split())
        if not query_words:
            return self.get_recent(k)

        scored: List[tuple[float, MemoryEntry]] = []
        for entry in reversed(self.short_term):  # prefer recent
            entry_words = set(entry.observation.lower().split())
            score = len(query_words & entry_words)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:k]]

    def retrieve_by_metadata(self, key: str, value: Any) -> List[MemoryEntry]:
        """Retrieve entries where metadata[key] == value."""
        return [
            e for e in self.short_term
            if e.metadata.get(key) == value
        ]

    # ------------------------------------------------------------------
    # Scene graph
    # ------------------------------------------------------------------

    def update_scene_graph(self, delta: Dict[str, Any]) -> None:
        """Merge a scene delta into the scene graph.

        ``delta`` should be a dict of node_id → node_properties.
        Existing nodes are updated; new nodes are added.
        """
        for node_id, props in delta.items():
            if node_id in self.scene_graph:
                self.scene_graph[node_id].update(props)
            else:
                self.scene_graph[node_id] = dict(props)

    def get_scene_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node from the scene graph."""
        return self.scene_graph.get(node_id)

    def list_scene_nodes(self) -> List[str]:
        """List all node IDs in the scene graph."""
        return list(self.scene_graph.keys())

    # ------------------------------------------------------------------
    # Quality history
    # ------------------------------------------------------------------

    def add_quality_snapshot(
        self,
        quality_vector: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        gate_result: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Record a quality vector and generation parameters."""
        return self.add_observation(
            agent="quality_system",
            observation=f"Quality snapshot overall={quality_vector.get('overall')}",
            metadata={
                "quality_vector": dict(quality_vector),
                "parameters": dict(parameters or {}),
                "gate_result": dict(gate_result or {}),
            },
        )

    def get_quality_history(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return recent quality-vector entries."""
        entries = [
            entry.metadata
            for entry in self.short_term
            if isinstance(entry.metadata, dict) and "quality_vector" in entry.metadata
        ]
        return entries[-n:]

    # ------------------------------------------------------------------
    # Long-term (simplified)
    # ------------------------------------------------------------------

    def archive_to_long_term(self, entries: Optional[List[MemoryEntry]] = None) -> None:
        """Move entries from short-term to long-term storage."""
        to_archive = entries or list(self.short_term)
        for entry in to_archive:
            self._long_term.append(entry)
            idx = len(self._long_term) - 1
            self._index_entry(entry, idx, long_term=True)
        if entries is None:
            self.short_term.clear()

    def search_long_term(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """Search long-term memory by keyword overlap."""
        query_words = set(query.lower().split())
        scored: List[tuple[float, MemoryEntry]] = []
        for entry in self._long_term:
            entry_words = set(entry.observation.lower().split())
            score = len(query_words & entry_words)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:k]]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "short_term": [e.to_dict() for e in self.short_term],
            "scene_graph": self.scene_graph,
            "long_term": [e.to_dict() for e in self._long_term],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMemory":
        mem = cls(scene_id=data.get("scene_id", "main"))
        mem.short_term = [MemoryEntry.from_dict(e) for e in data.get("short_term", [])]
        mem.scene_graph = dict(data.get("scene_graph", {}))
        mem._long_term = [MemoryEntry.from_dict(e) for e in data.get("long_term", [])]
        return mem

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _index_entry(
        self,
        entry: MemoryEntry,
        idx: int,
        long_term: bool = False,
    ) -> None:
        """Add entry words to the keyword index."""
        target = self._keyword_index
        for word in entry.observation.lower().split():
            target.setdefault(word, []).append(idx)
