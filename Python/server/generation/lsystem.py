"""Pure-Python L-system generator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

Vector3 = Tuple[float, float, float]


@dataclass
class SplineSegment:
    start: Vector3
    end: Vector3

    def to_dict(self) -> dict:
        return {"start": list(self.start), "end": list(self.end)}


def _normalize(v: Vector3) -> Vector3:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length <= 1.0e-9:
        return (1.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vector3, s: float) -> Vector3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _rotate(v: Vector3, axis: Vector3, angle: float) -> Vector3:
    axis = _normalize(axis)
    c = math.cos(angle)
    s = math.sin(angle)
    cross = _cross(axis, v)
    dot = axis[0] * v[0] + axis[1] * v[1] + axis[2] * v[2]
    return (
        v[0] * c + cross[0] * s + axis[0] * dot * (1.0 - c),
        v[1] * c + cross[1] * s + axis[1] * dot * (1.0 - c),
        v[2] * c + cross[2] * s + axis[2] * dot * (1.0 - c),
    )


def derive_lsystem(axiom: str, rules: Mapping[str, str], iterations: int, max_string_length: int = 1_000_000) -> str:
    current = axiom
    for _ in range(max(0, min(iterations, 10))):
        next_value = "".join(rules.get(ch, ch) for ch in current)
        if len(next_value) > max_string_length:
            return next_value[:max_string_length]
        current = next_value
    return current


def evaluate_lsystem(
    axiom: str = "F",
    rules: Mapping[str, str] | None = None,
    iterations: int = 3,
    step_length: float = 1.0,
    angle_degrees: float = 90.0,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    heading: Sequence[float] = (1.0, 0.0, 0.0),
    up: Sequence[float] = (0.0, 0.0, 1.0),
    dimension_mode: str = "3d",
) -> dict:
    rules = rules or {"F": "F+F-F-F+F"}
    derived = derive_lsystem(axiom, rules, iterations)
    pos = (float(origin[0]), float(origin[1]), float(origin[2]))
    heading_v = _normalize((float(heading[0]), float(heading[1]), float(heading[2])))
    up_v = _normalize((float(up[0]), float(up[1]), float(up[2])))
    left_v = _normalize(_cross(up_v, heading_v))
    angle = math.radians(angle_degrees)
    stack: List[Tuple[Vector3, Vector3, Vector3, Vector3]] = []
    segments: List[SplineSegment] = []
    origin_z = pos[2]
    is_2d = dimension_mode.lower() in {"2d", "twod"}
    for ch in derived:
        if ch in {"F", "G"}:
            end = _add(pos, _scale(heading_v, step_length))
            if is_2d:
                end = (end[0], end[1], origin_z)
            segments.append(SplineSegment(pos, end))
            pos = end
        elif ch == "f":
            pos = _add(pos, _scale(heading_v, step_length))
            if is_2d:
                pos = (pos[0], pos[1], origin_z)
        elif ch == "+":
            heading_v = _rotate(heading_v, up_v, angle)
            left_v = _rotate(left_v, up_v, angle)
        elif ch == "-":
            heading_v = _rotate(heading_v, up_v, -angle)
            left_v = _rotate(left_v, up_v, -angle)
        elif ch == "&":
            heading_v = _rotate(heading_v, left_v, angle)
            up_v = _rotate(up_v, left_v, angle)
        elif ch == "^":
            heading_v = _rotate(heading_v, left_v, -angle)
            up_v = _rotate(up_v, left_v, -angle)
        elif ch == "\\":
            left_v = _rotate(left_v, heading_v, angle)
            up_v = _rotate(up_v, heading_v, angle)
        elif ch == "/":
            left_v = _rotate(left_v, heading_v, -angle)
            up_v = _rotate(up_v, heading_v, -angle)
        elif ch == "[":
            stack.append((pos, heading_v, left_v, up_v))
        elif ch == "]" and stack:
            pos, heading_v, left_v, up_v = stack.pop()
    return {
        "segments": [segment.to_dict() for segment in segments],
        "derived_string": derived,
        "segment_count": len(segments),
    }
