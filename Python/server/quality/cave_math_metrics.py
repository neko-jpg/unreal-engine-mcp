"""Deterministic mathematical quality metrics for cave scenes."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

Vector3 = Tuple[float, float, float]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _entropy(values: Iterable[float], bins: int = 12) -> float:
    data = [float(v) for v in values if math.isfinite(float(v))]
    if not data:
        return 0.0
    vmin = min(data)
    vmax = max(data)
    if abs(vmax - vmin) <= 1.0e-9:
        return 0.0
    counts = [0] * bins
    for value in data:
        idx = min(bins - 1, int((value - vmin) / (vmax - vmin) * bins))
        counts[idx] += 1
    total = float(sum(counts))
    h = 0.0
    for count in counts:
        if count:
            p = count / total
            h -= p * math.log(p, 2)
    return _clamp(h / math.log(bins, 2))


def _as_mapping(mesh: Any) -> Mapping[str, Any]:
    if hasattr(mesh, "to_dict"):
        return mesh.to_dict()
    if isinstance(mesh, Mapping):
        return mesh
    return {}


def _mesh_vertices(mesh: Mapping[str, Any]) -> List[Vector3]:
    vertices = mesh.get("vertices") or mesh.get("vertex_positions") or []
    out: List[Vector3] = []
    if isinstance(vertices, list):
        for value in vertices:
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    out.append((float(value[0]), float(value[1]), float(value[2])))
                except (TypeError, ValueError):
                    continue
    return out


class CaveMathMetrics:
    """Compute objective cave quality metrics from mesh and scene metadata."""

    def compute_curvature_entropy(self, mesh: Any) -> float:
        data = _as_mapping(mesh)
        if "curvature_entropy" in data:
            return _clamp(float(data.get("curvature_entropy") or 0.0))
        curvatures = data.get("curvatures") or data.get("mean_curvature") or []
        if isinstance(curvatures, list) and curvatures:
            return _entropy(curvatures)
        normal_entropy = data.get("normal_entropy")
        if isinstance(normal_entropy, (int, float)):
            return _clamp(float(normal_entropy) * 0.92)
        flat = self.compute_flat_surface_ratio(data)
        return _clamp(1.0 - flat * 1.35)

    def compute_flat_surface_ratio(self, mesh: Any) -> float:
        data = _as_mapping(mesh)
        if "flat_surface_ratio" in data:
            return _clamp(float(data.get("flat_surface_ratio") or 0.0))
        normals = data.get("normals") or data.get("face_normals") or []
        if isinstance(normals, list) and normals:
            buckets: Dict[Tuple[int, int, int], int] = {}
            for normal in normals:
                if not isinstance(normal, (list, tuple)) or len(normal) < 3:
                    continue
                try:
                    length = math.sqrt(float(normal[0]) ** 2 + float(normal[1]) ** 2 + float(normal[2]) ** 2)
                    if length <= 1.0e-6:
                        continue
                    key = tuple(int(round(float(normal[i]) / length, 1) * 10) for i in range(3))
                    buckets[key] = buckets.get(key, 0) + 1
                except (TypeError, ValueError):
                    continue
            total = sum(buckets.values())
            return _clamp(max(buckets.values()) / total) if total else 0.0
        if data.get("is_box_cave"):
            return 0.58
        return 0.25

    def compute_arch_score(self, mesh: Any) -> float:
        data = _as_mapping(mesh)
        if "arch_score" in data:
            return _clamp(float(data.get("arch_score") or 0.0))
        vertices = _mesh_vertices(data)
        if len(vertices) < 4:
            return _clamp(0.35 + float(data.get("ceiling_height_variance", 0.0) or 0.0) * 0.75)
        zs = [v[2] for v in vertices]
        z_cut = sorted(zs)[int(len(zs) * 0.75)]
        top = [v for v in vertices if v[2] >= z_cut]
        if not top:
            return 0.0
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        max_radius = max(math.hypot(v[0] - cx, v[1] - cy) for v in vertices) or 1.0
        center_heights = [v[2] for v in top if math.hypot(v[0] - cx, v[1] - cy) <= max_radius * 0.35]
        edge_heights = [v[2] for v in top if math.hypot(v[0] - cx, v[1] - cy) >= max_radius * 0.65]
        if not center_heights or not edge_heights:
            return 0.45
        lift = (sum(center_heights) / len(center_heights)) - (sum(edge_heights) / len(edge_heights))
        return _clamp(0.5 + lift / max(max(zs) - min(zs), 1.0))

    def compute_roughness_spectrum(self, mesh: Any) -> Dict[str, float]:
        data = _as_mapping(mesh)
        spectrum = data.get("roughness_spectrum")
        if isinstance(spectrum, Mapping):
            return {
                "low": _clamp(float(spectrum.get("low", 0.0))),
                "mid": _clamp(float(spectrum.get("mid", 0.0))),
                "high": _clamp(float(spectrum.get("high", 0.0))),
            }
        # Try frequency-based analysis if vertex positions are available
        vertices = _mesh_vertices(data)
        if len(vertices) >= 16:
            return self._frequency_roughness(vertices)
        # Fallback: synthetic from already-computed metrics
        entropy = self.compute_curvature_entropy(data)
        flat = self.compute_flat_surface_ratio(data)
        return {
            "low": round(_clamp(entropy * 0.75 + 0.10), 3),
            "mid": round(_clamp(entropy * 0.90 + (1.0 - flat) * 0.10), 3),
            "high": round(_clamp((1.0 - flat) * 0.65 + entropy * 0.20), 3),
        }

    def _frequency_roughness(self, vertices: list) -> Dict[str, float]:
        """Compute roughness spectrum via DFT of vertex displacement signal."""
        import math
        # Compute displacement from smoothed centroid path
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
        displacements = [((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) ** 0.5 for x, y, z in vertices]
        n = len(displacements)
        # Compute DFT magnitude spectrum
        magnitudes = []
        for k in range(n // 2):
            re = sum(displacements[j] * math.cos(2 * math.pi * k * j / n) for j in range(n))
            im = sum(displacements[j] * math.sin(2 * math.pi * k * j / n) for j in range(n))
            magnitudes.append((re ** 2 + im ** 2) ** 0.5)
        total = sum(magnitudes) or 1.0
        # Band energy: low=[0,0.1], mid=[0.1,0.4], high=[0.4,1.0]
        nyq = len(magnitudes)
        low_end = max(1, int(nyq * 0.1))
        mid_end = max(low_end + 1, int(nyq * 0.4))
        low_energy = sum(magnitudes[:low_end]) / total
        mid_energy = sum(magnitudes[low_end:mid_end]) / total
        high_energy = sum(magnitudes[mid_end:]) / total
        return {
            "low": round(_clamp(low_energy), 3),
            "mid": round(_clamp(mid_energy), 3),
            "high": round(_clamp(high_energy), 3),
        }

    def compute_topology_score(self, skeleton_graph: Any) -> float:
        if isinstance(skeleton_graph, Mapping):
            branch_count = int(skeleton_graph.get("branch_count", 0) or 0)
            dead_end_count = int(skeleton_graph.get("dead_end_count", 0) or 0)
            main_path_length = float(skeleton_graph.get("main_path_length", 0.0) or 0.0)
            chamber_count = int(skeleton_graph.get("chamber_count", 0) or 0)
        else:
            branch_count = dead_end_count = chamber_count = 0
            main_path_length = 0.0
        return _clamp(
            min(branch_count, 4) / 4.0 * 0.35
            + min(dead_end_count, 3) / 3.0 * 0.20
            + min(main_path_length / 1200.0, 1.0) * 0.30
            + min(chamber_count, 4) / 4.0 * 0.15
        )

    def compute_detail_distribution_score(self, objects: Any) -> float:
        if isinstance(objects, Mapping):
            density = float(objects.get("detail_density_per_m2", 0.0) or 0.0)
            clumping = float(objects.get("clumping_score", 0.0) or 0.0)
            floating = int(objects.get("floating_object_count", 0) or 0)
        else:
            density = 0.0
            clumping = 0.0
            floating = 0
        return _clamp(min(density / 3.0, 1.0) * 0.75 + (1.0 - min(clumping, 1.0)) * 0.20 - min(floating, 10) * 0.03)

    def compute_lighting_contrast_score(self, screenshots_or_lights: Any) -> float:
        if isinstance(screenshots_or_lights, Mapping):
            contrast = float(screenshots_or_lights.get("image_contrast", 0.0) or 0.0)
            under = float(screenshots_or_lights.get("underexposed_pixel_ratio", 0.0) or 0.0)
            over = float(screenshots_or_lights.get("overexposed_pixel_ratio", 0.0) or 0.0)
            return _clamp(contrast * 0.75 + min(under / 0.25, 1.0) * 0.15 - over * 0.30 + 0.05)
        return 0.0

    def compute_walkability_score(self, navmesh: Any) -> float:
        if isinstance(navmesh, Mapping):
            if navmesh.get("walkable_path_success") is False:
                return 0.0
            width = float(navmesh.get("min_tunnel_width", 0.0) or 0.0)
            return _clamp(width / 220.0) if width else 0.65
        return 0.5

    def compute_all(self, observation_or_metrics: Any) -> Dict[str, Any]:
        if hasattr(observation_or_metrics, "metrics"):
            observation = observation_or_metrics
            metrics = dict(getattr(observation, "metrics", {}) or {})
            meshes = getattr(observation, "meshes", {}) or {}
            mesh = meshes.get("main", metrics) if isinstance(meshes, Mapping) else metrics
            actors = getattr(observation, "actors", {}) or {}
            pcg = getattr(observation, "pcg", None)
            lights = getattr(observation, "lights", None)
        else:
            observation = None
            metrics = dict(observation_or_metrics or {})
            mesh = metrics
            actors = metrics
            pcg = metrics
            lights = metrics

        pcg_dict = pcg.to_dict() if hasattr(pcg, "to_dict") else pcg
        light_dict = lights.to_dict() if hasattr(lights, "to_dict") else lights
        topology_source = {
            "branch_count": metrics.get("branch_count", 0),
            "dead_end_count": metrics.get("dead_end_count", 0),
            "main_path_length": metrics.get("depth_score", 0.0) * 1200.0,
            "chamber_count": metrics.get("chamber_count", 0),
        }
        result = {
            "flat_surface_ratio": round(self.compute_flat_surface_ratio(mesh), 3),
            "curvature_entropy": round(self.compute_curvature_entropy(mesh), 3),
            "arch_score": round(self.compute_arch_score(mesh), 3),
            "roughness_spectrum": self.compute_roughness_spectrum(mesh),
            "topology_score": round(self.compute_topology_score(topology_source), 3),
            "detail_distribution_score": round(self.compute_detail_distribution_score(pcg_dict or actors), 3),
            "lighting_contrast_score": round(self.compute_lighting_contrast_score(light_dict or metrics), 3),
            "walkability_score": round(self.compute_walkability_score(metrics), 3),
        }
        result.update({k: v for k, v in metrics.items() if k not in result})
        if observation is not None:
            result["screenshot_count"] = len(getattr(observation, "screenshots", []) or [])
        return result


def compute_cave_math_metrics(observation_or_metrics: Any) -> Dict[str, Any]:
    """Compute all cave math metrics."""
    return CaveMathMetrics().compute_all(observation_or_metrics)
