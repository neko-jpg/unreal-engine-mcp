"""Python geometry primitives mirroring scene-syncd's Rust geom layer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

Vector3 = Tuple[float, float, float]


def vec3(value: Sequence[float]) -> Vector3:
    return (float(value[0]), float(value[1]), float(value[2]))


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _scale(a: Vector3, scalar: float) -> Vector3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def _length(a: Vector3) -> float:
    return math.sqrt(max(_dot(a, a), 0.0))


def _normalize(a: Vector3, fallback: Vector3 = (0.0, 0.0, 1.0)) -> Vector3:
    length = _length(a)
    if length <= 1.0e-9:
        return fallback
    return (a[0] / length, a[1] / length, a[2] / length)


@dataclass(frozen=True)
class Aabb3:
    min: Vector3
    max: Vector3

    @classmethod
    def from_center_extent(cls, center: Sequence[float], extent: Sequence[float]) -> "Aabb3":
        c = vec3(center)
        e = vec3(extent)
        return cls((c[0] - e[0], c[1] - e[1], c[2] - e[2]), (c[0] + e[0], c[1] + e[1], c[2] + e[2]))

    @classmethod
    def from_points(cls, points: Iterable[Sequence[float]]) -> Optional["Aabb3"]:
        pts = [vec3(p) for p in points]
        if not pts:
            return None
        return cls(
            (min(p[0] for p in pts), min(p[1] for p in pts), min(p[2] for p in pts)),
            (max(p[0] for p in pts), max(p[1] for p in pts), max(p[2] for p in pts)),
        )

    def intersects(self, other: "Aabb3", epsilon: float = 0.0) -> bool:
        e = float(epsilon)
        return (
            self.max[0] + e > other.min[0]
            and self.min[0] - e < other.max[0]
            and self.max[1] + e > other.min[1]
            and self.min[1] - e < other.max[1]
            and self.max[2] + e > other.min[2]
            and self.min[2] - e < other.max[2]
        )

    def contains_point(self, point: Sequence[float], epsilon: float = 0.0) -> bool:
        p = vec3(point)
        e = float(epsilon)
        return all(self.min[i] - e <= p[i] <= self.max[i] + e for i in range(3))

    def volume(self) -> float:
        return (self.max[0] - self.min[0]) * (self.max[1] - self.min[1]) * (self.max[2] - self.min[2])

    def merge(self, other: "Aabb3") -> "Aabb3":
        return Aabb3(
            (min(self.min[0], other.min[0]), min(self.min[1], other.min[1]), min(self.min[2], other.min[2])),
            (max(self.max[0], other.max[0]), max(self.max[1], other.max[1]), max(self.max[2], other.max[2])),
        )

    def expand(self, padding: float) -> "Aabb3":
        p = float(padding)
        return Aabb3((self.min[0] - p, self.min[1] - p, self.min[2] - p), (self.max[0] + p, self.max[1] + p, self.max[2] + p))

    def size(self) -> Vector3:
        return (self.max[0] - self.min[0], self.max[1] - self.min[1], self.max[2] - self.min[2])


def segment_intersection_2d(a: Sequence[float], b: Sequence[float], epsilon: float = 0.0) -> Optional[Tuple[float, float]]:
    """Return the intersection point of two 2D segments.

    ``a`` and ``b`` are ``(x1, y1, x2, y2)``.
    """
    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)
    dx1 = ax2 - ax1
    dy1 = ay2 - ay1
    dx2 = bx2 - bx1
    dy2 = by2 - by1
    denom = dx1 * dy2 - dy1 * dx2
    e = float(epsilon)
    if abs(denom) < e:
        return None
    t = ((bx1 - ax1) * dy2 - (by1 - ay1) * dx2) / denom
    u = ((bx1 - ax1) * dy1 - (by1 - ay1) * dx1) / denom
    if -e <= t <= 1.0 + e and -e <= u <= 1.0 + e:
        return (ax1 + t * dx1, ay1 + t * dy1)
    return None


@dataclass(frozen=True)
class Obb3:
    center: Vector3
    half_extents: Vector3
    axes: Tuple[Vector3, Vector3, Vector3]

    @classmethod
    def from_euler_degrees(
        cls,
        center: Sequence[float],
        half_extents: Sequence[float],
        pitch: float = 0.0,
        yaw: float = 0.0,
        roll: float = 0.0,
    ) -> "Obb3":
        axes = _euler_axes(math.radians(pitch), math.radians(yaw), math.radians(roll))
        return cls(vec3(center), vec3(half_extents), axes)

    def vertices(self) -> List[Vector3]:
        verts: List[Vector3] = []
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                for sz in (-1.0, 1.0):
                    offset = (0.0, 0.0, 0.0)
                    for axis, extent, sign in zip(self.axes, self.half_extents, (sx, sy, sz)):
                        offset = _add(offset, _scale(axis, extent * sign))
                    verts.append(_add(self.center, offset))
        return verts

    def to_aabb(self) -> Aabb3:
        aabb = Aabb3.from_points(self.vertices())
        assert aabb is not None
        return aabb

    def contains_point(self, point: Sequence[float], epsilon: float = 0.0) -> bool:
        p = _sub(vec3(point), self.center)
        e = float(epsilon)
        return all(abs(_dot(p, self.axes[i])) <= self.half_extents[i] + e for i in range(3))

    def intersects_obb(self, other: "Obb3", epsilon: float = 0.0) -> bool:
        axes = list(self.axes) + list(other.axes)
        axes.extend(_cross(a, b) for a in self.axes for b in other.axes)
        for axis in axes:
            n = _normalize(axis, fallback=(0.0, 0.0, 0.0))
            if _length(n) <= 1.0e-9:
                continue
            a_min, a_max = _project(self.vertices(), n)
            b_min, b_max = _project(other.vertices(), n)
            if a_max + epsilon < b_min or b_max + epsilon < a_min:
                return False
        return True


def _project(points: List[Vector3], axis: Vector3) -> Tuple[float, float]:
    values = [_dot(point, axis) for point in points]
    return min(values), max(values)


def _euler_axes(pitch: float, yaw: float, roll: float) -> Tuple[Vector3, Vector3, Vector3]:
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)
    # Unreal-ish Z yaw, Y pitch, X roll composition.
    x_axis = _normalize((cy * cp, sy * cp, sp), (1.0, 0.0, 0.0))
    z_axis = _normalize((cy * sp * sr - sy * cr, sy * sp * sr + cy * cr, -cp * sr), (0.0, 0.0, 1.0))
    y_axis = _normalize(_cross(z_axis, x_axis), (0.0, 1.0, 0.0))
    return (x_axis, y_axis, z_axis)
