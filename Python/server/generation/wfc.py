"""Pure-Python Wave Function Collapse grid solver."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple


def _opposite(direction: str) -> str:
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[direction]


def _neighbor(x: int, y: int, direction: str) -> Tuple[int, int]:
    if direction == "east":
        return x + 1, y
    if direction == "west":
        return x - 1, y
    if direction == "south":
        return x, y + 1
    return x, y - 1


def build_adjacency(tiles: List[Mapping[str, object]], constraints: List[Mapping[str, str]]) -> Dict[str, Dict[str, Set[str]]]:
    ids = [str(tile["id"]) for tile in tiles]
    adjacency = {direction: {tile_id: set() for tile_id in ids} for direction in ("north", "south", "east", "west")}
    if not constraints:
        return adjacency
    for constraint in constraints:
        left = str(constraint["left"])
        right = str(constraint["right"])
        direction = str(constraint["direction"]).lower()
        adjacency[direction].setdefault(left, set()).add(right)
        adjacency[_opposite(direction)].setdefault(right, set()).add(left)
    return adjacency


def solve_wfc_grid(
    width: int,
    height: int,
    tiles: List[Mapping[str, object]],
    constraints: List[Mapping[str, str]],
    seed: Optional[int] = None,
    periodic: bool = False,
    max_attempts: int = 10000,
) -> dict:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if not tiles:
        raise ValueError("tiles list cannot be empty")
    if width * height > 10000:
        raise ValueError("grid too large: max 10_000 cells")
    rng = random.Random(seed)
    tile_ids = [str(tile["id"]) for tile in tiles]
    weights = {str(tile["id"]): float(tile.get("weight", 1.0) or 1.0) for tile in tiles}
    adjacency = build_adjacency(tiles, constraints)
    grid: List[List[Set[str]]] = [[set(tile_ids) for _ in range(width)] for _ in range(height)]

    attempts = 0
    while attempts < max_attempts:
        candidates = [
            (len(grid[y][x]), x, y)
            for y in range(height)
            for x in range(width)
            if len(grid[y][x]) > 1
        ]
        if not candidates:
            return {
                "width": width,
                "height": height,
                "tiles": [
                    {"x": x, "y": y, "tile_id": next(iter(grid[y][x])), "rotation_degrees": 0.0}
                    for y in range(height)
                    for x in range(width)
                ],
                "attempts": attempts,
            }
        _, x, y = min(candidates)
        choice = _weighted_choice(sorted(grid[y][x]), weights, rng)
        snapshot = [[set(cell) for cell in row] for row in grid]
        grid[y][x] = {choice}
        attempts += 1
        if not _propagate(grid, adjacency, x, y, periodic):
            grid = snapshot
            grid[y][x].discard(choice)
            if not grid[y][x]:
                raise RuntimeError(f"WFC contradiction at {x},{y}")
    raise RuntimeError(f"WFC failed after {attempts} attempts")


def _weighted_choice(values: List[str], weights: Mapping[str, float], rng: random.Random) -> str:
    total = sum(max(weights.get(value, 1.0), 0.0) for value in values)
    if total <= 0.0:
        return rng.choice(values)
    pick = rng.random() * total
    seen = 0.0
    for value in values:
        seen += max(weights.get(value, 1.0), 0.0)
        if seen >= pick:
            return value
    return values[-1]


def _propagate(grid: List[List[Set[str]]], adjacency: Mapping[str, Mapping[str, Set[str]]], x: int, y: int, periodic: bool) -> bool:
    height = len(grid)
    width = len(grid[0])
    queue = [(x, y)]
    while queue:
        cx, cy = queue.pop()
        for direction in ("north", "south", "east", "west"):
            nx, ny = _neighbor(cx, cy, direction)
            if periodic:
                nx %= width
                ny %= height
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            allowed: Set[str] = set()
            for tile_id in grid[cy][cx]:
                allowed |= set(adjacency[direction].get(tile_id, set()))
            old = set(grid[ny][nx])
            grid[ny][nx] &= allowed
            if not grid[ny][nx]:
                return False
            if grid[ny][nx] != old:
                queue.append((nx, ny))
    return True
