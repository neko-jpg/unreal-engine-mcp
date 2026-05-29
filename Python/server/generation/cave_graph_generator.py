"""Cave topology graph generation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

Vector3 = Tuple[float, float, float]


@dataclass
class CaveNode:
    node_id: str
    kind: str
    position: Vector3
    radius: float
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "position": list(self.position),
            "radius": self.radius,
            "tags": list(self.tags),
        }


@dataclass
class CaveEdge:
    start: str
    end: str
    kind: str
    radius: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "kind": self.kind,
            "radius": self.radius,
        }


class CaveGraphGenerator:
    """Generate a cave graph with entrance, chambers, branches, and dead ends."""

    def generate(self, params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        params = params or {}
        seed = int(params.get("seed", 252539))
        rng = random.Random(seed)
        chamber_count = max(3, min(int(params.get("chamber_count", params.get("tunnel_count", 5))), 12))
        branch_count = max(2, min(int(params.get("branch_count", 3)), 8))
        main_length = float(params.get("main_path_length", 3000.0))
        room_variance = float(params.get("room_scale_variance", 0.38))
        base_radius = float(params.get("base_radius", 320.0))
        tunnel_radius = float(params.get("tunnel_radius", 180.0))

        nodes: List[CaveNode] = [
            CaveNode("entrance", "entrance", (-main_length * 0.5, 0.0, 110.0), tunnel_radius * 0.9, ["entrance"])
        ]
        for index in range(1, chamber_count + 1):
            t = index / chamber_count
            radius = base_radius * (1.0 + rng.uniform(-room_variance, room_variance))
            nodes.append(
                CaveNode(
                    f"chamber_{index:02d}",
                    "chamber",
                    (
                        -main_length * 0.5 + t * main_length + rng.uniform(-180.0, 180.0),
                        rng.uniform(-220.0, 260.0),
                        180.0 + rng.uniform(-70.0, 120.0),
                    ),
                    max(160.0, radius),
                    ["main_path"] if index < chamber_count else ["deepest"],
                )
            )

        edges: List[CaveEdge] = []
        for prev, cur in zip(nodes, nodes[1:]):
            edges.append(CaveEdge(prev.node_id, cur.node_id, "main_tunnel", tunnel_radius))

        dead_ends = 0
        for index in range(branch_count):
            anchor = nodes[1 + (index % max(1, len(nodes) - 2))]
            side = -1.0 if index % 2 else 1.0
            branch_len = rng.uniform(520.0, 1100.0)
            branch_id = f"branch_{index + 1:02d}"
            node = CaveNode(
                branch_id,
                "dead_end" if index % 3 == 0 else "side_chamber",
                (
                    anchor.position[0] + rng.uniform(-120.0, 220.0),
                    anchor.position[1] + side * branch_len,
                    anchor.position[2] + rng.uniform(-50.0, 110.0),
                ),
                base_radius * rng.uniform(0.42, 0.76),
                ["branch", "dead_end"] if index % 3 == 0 else ["branch"],
            )
            dead_ends += 1 if "dead_end" in node.tags else 0
            nodes.append(node)
            edges.append(CaveEdge(anchor.node_id, node.node_id, "branch_tunnel", tunnel_radius * rng.uniform(0.55, 0.82)))

        # Cycle-closing pass: connect nearby branch tips to create loops
        cycle_count = 0
        max_cycles = max(0, min(branch_count // 2, 3))
        branch_nodes = [n for n in nodes if "branch" in n.tags]
        if len(branch_nodes) >= 2 and max_cycles > 0:
            # Compute pairwise distances between branch tips
            pairs: list[tuple[float, CaveNode, CaveNode]] = []
            for i, a in enumerate(branch_nodes):
                for b in branch_nodes[i + 1:]:
                    dx = a.position[0] - b.position[0]
                    dy = a.position[1] - b.position[1]
                    dz = a.position[2] - b.position[2]
                    dist = (dx * dx + dy * dy + dz * dz) ** 0.5
                    pairs.append((dist, a, b))
            pairs.sort(key=lambda x: x[0])
            used: set[str] = set()
            for dist, a, b in pairs:
                if cycle_count >= max_cycles:
                    break
                if a.node_id in used or b.node_id in used:
                    continue
                # Only close cycles for reasonably close nodes
                if dist > main_length * 0.45:
                    continue
                edges.append(CaveEdge(a.node_id, b.node_id, "shortcut", tunnel_radius * 0.5))
                cycle_count += 1
                used.add(a.node_id)
                used.add(b.node_id)

        graph = {
            "seed": seed,
            "nodes": [node.to_dict() for node in nodes],
            "edges": [edge.to_dict() for edge in edges],
            "branch_count": branch_count,
            "dead_end_count": max(1, dead_ends),
            "chamber_count": chamber_count,
            "cycle_count": cycle_count,
            "main_path_length": main_length,
            "room_scale_variance": room_variance,
        }
        return graph
