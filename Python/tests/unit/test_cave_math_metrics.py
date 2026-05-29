"""Unit tests for cave math metrics."""

from __future__ import annotations

from server.quality.cave_math_metrics import CaveMathMetrics, compute_cave_math_metrics


def test_flat_box_mesh_scores_low_shape_metrics():
    metrics = compute_cave_math_metrics(
        {
            "main_mesh_exists": True,
            "is_box_cave": True,
            "flat_surface_ratio": 0.58,
            "curvature_entropy": 0.12,
            "arch_score": 0.22,
            "triangle_count": 12000,
        }
    )
    assert metrics["flat_surface_ratio"] > 0.35
    assert metrics["curvature_entropy"] < 0.45
    assert metrics["arch_score"] < 0.55


def test_varied_normals_reduce_flat_surface_ratio():
    normals = [
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.9, 0.1],
        [0.0, 0.0, 1.0],
        [0.2, 0.4, 0.9],
    ]
    ratio = CaveMathMetrics().compute_flat_surface_ratio({"normals": normals})
    assert 0.0 < ratio < 0.5


def test_roughness_spectrum_has_low_mid_high_bands():
    spectrum = CaveMathMetrics().compute_roughness_spectrum(
        {"curvature_entropy": 0.74, "flat_surface_ratio": 0.18}
    )
    assert set(spectrum) == {"low", "mid", "high"}
    assert spectrum["mid"] >= spectrum["low"]


def test_topology_score_high_for_rich_graph():
    graph = {"branch_count": 4, "dead_end_count": 3, "main_path_length": 1200.0, "chamber_count": 4}
    score = CaveMathMetrics().compute_topology_score(graph)
    assert score > 0.8


def test_topology_score_low_for_minimal_graph():
    graph = {"branch_count": 0, "dead_end_count": 0, "main_path_length": 100.0, "chamber_count": 1}
    score = CaveMathMetrics().compute_topology_score(graph)
    assert score < 0.3


def test_detail_distribution_score_dense_non_clumped():
    objects = {"detail_density_per_m2": 3.0, "clumping_score": 0.1, "floating_object_count": 0}
    score = CaveMathMetrics().compute_detail_distribution_score(objects)
    assert score > 0.8


def test_detail_distribution_score_sparse_clumped():
    objects = {"detail_density_per_m2": 0.5, "clumping_score": 0.8, "floating_object_count": 5}
    score = CaveMathMetrics().compute_detail_distribution_score(objects)
    assert score < 0.3


def test_lighting_contrast_score_high_contrast():
    lights = {"image_contrast": 0.75, "underexposed_pixel_ratio": 0.20, "overexposed_pixel_ratio": 0.01}
    score = CaveMathMetrics().compute_lighting_contrast_score(lights)
    assert score > 0.6


def test_lighting_contrast_score_overexposed():
    lights = {"image_contrast": 0.30, "underexposed_pixel_ratio": 0.05, "overexposed_pixel_ratio": 0.30}
    score = CaveMathMetrics().compute_lighting_contrast_score(lights)
    assert score < 0.3


def test_walkability_score_passable():
    navmesh = {"walkable_path_success": True, "min_tunnel_width": 200.0}
    score = CaveMathMetrics().compute_walkability_score(navmesh)
    assert score > 0.8


def test_walkability_score_impassable():
    navmesh = {"walkable_path_success": False}
    score = CaveMathMetrics().compute_walkability_score(navmesh)
    assert score == 0.0


def test_compute_all_returns_all_metrics():
    observation = {
        "main_mesh_exists": True,
        "is_box_cave": False,
        "flat_surface_ratio": 0.20,
        "curvature_entropy": 0.65,
        "arch_score": 0.70,
        "triangle_count": 40000,
        "detail_density_per_m2": 2.5,
        "clumping_score": 0.15,
        "floating_object_count": 0,
        "image_contrast": 0.55,
        "underexposed_pixel_ratio": 0.10,
        "overexposed_pixel_ratio": 0.02,
        "branch_count": 3,
        "dead_end_count": 2,
        "main_path_length": 800.0,
        "chamber_count": 4,
        "walkable_path_success": True,
        "min_tunnel_width": 180.0,
    }
    metrics = compute_cave_math_metrics(observation)
    assert "flat_surface_ratio" in metrics
    assert "curvature_entropy" in metrics
    assert "arch_score" in metrics
    assert "roughness_spectrum" in metrics
    assert "topology_score" in metrics
    assert "detail_distribution_score" in metrics
    assert "lighting_contrast_score" in metrics
    assert "walkability_score" in metrics


def test_topology_score_with_good_graph():
    graph = {"branch_count": 4, "dead_end_count": 2, "main_path_length": 1200, "chamber_count": 5}
    score = CaveMathMetrics().compute_topology_score(graph)
    assert score > 0.7


def test_topology_score_empty_graph():
    score = CaveMathMetrics().compute_topology_score({})
    assert score == 0.0


def test_detail_distribution_score_dense():
    objects = {"detail_density_per_m2": 3.5, "clumping_score": 0.1, "floating_object_count": 0}
    score = CaveMathMetrics().compute_detail_distribution_score(objects)
    assert score > 0.8


def test_detail_distribution_score_sparse_clumped():
    objects = {"detail_density_per_m2": 0.5, "clumping_score": 0.8, "floating_object_count": 5}
    score = CaveMathMetrics().compute_detail_distribution_score(objects)
    assert score < 0.5


def test_lighting_contrast_score_good():
    lights = {"image_contrast": 0.7, "underexposed_pixel_ratio": 0.15, "overexposed_pixel_ratio": 0.02}
    score = CaveMathMetrics().compute_lighting_contrast_score(lights)
    assert score > 0.5


def test_lighting_contrast_score_overexposed():
    lights = {"image_contrast": 0.3, "underexposed_pixel_ratio": 0.05, "overexposed_pixel_ratio": 0.20}
    score = CaveMathMetrics().compute_lighting_contrast_score(lights)
    assert score < 0.4


def test_walkability_score_success():
    navmesh = {"walkable_path_success": True, "min_tunnel_width": 200.0}
    score = CaveMathMetrics().compute_walkability_score(navmesh)
    assert score > 0.8


def test_walkability_score_failure():
    navmesh = {"walkable_path_success": False}
    score = CaveMathMetrics().compute_walkability_score(navmesh)
    assert score == 0.0


def test_compute_all_with_observation():
    observation = type("Obs", (), {
        "metrics": {
            "main_mesh_exists": True, "flat_surface_ratio": 0.25, "curvature_entropy": 0.6,
            "arch_score": 0.7, "detail_density_per_m2": 2.5, "image_contrast": 0.65,
            "underexposed_pixel_ratio": 0.12, "overexposed_pixel_ratio": 0.02,
        },
        "meshes": {},
        "actors": {"actor_count_by_tag": {"stalactite": 20, "rock_debris": 30}},
        "pcg": {"detail_density_per_m2": 2.5, "clumping_score": 0.15, "floating_object_count": 0},
        "lights": {"image_contrast": 0.65, "underexposed_pixel_ratio": 0.12, "overexposed_pixel_ratio": 0.02},
    })()
    result = compute_cave_math_metrics(observation)
    assert "flat_surface_ratio" in result
    assert "curvature_entropy" in result
    assert "arch_score" in result
