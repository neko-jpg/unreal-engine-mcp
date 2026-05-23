### landscape part2: 8 more handlers promoted (16/22 total)

- Issue: Refs #80
- PR: codex-stubs-w1-landscape-part2
- Wave: W1
- Handlers promoted in this PR: 8
- Cumulative for #80: 16 / 22
- New `executed: true` cases:
  - `set_landscape_section_component`
  - `import_landscape_heightmap`
  - `export_landscape_heightmap`
  - `create_landscape_paint_layer`
  - `set_landscape_layer_blend`
  - `add_landscape_spline`
  - `add_road_spline`
  - `carve_river_terrain`

Approach (UE 5.7-safe): re-uses `LandscapeMetaPersist` + the
`ResolveLandscapeActor` helper from part1. `set_landscape_section_component`
additionally writes `ALandscape::NumSubsections` and `SubsectionSizeQuads`
directly on the actor inside `FMCPScopedTransaction` because both are
public properties in 5.7. `add_road_spline` resolves the optional
`road_mesh_path` via `StaticLoadObject` and surfaces a `mesh_resolved`
flag in the response so callers can detect typos.
`set_landscape_layer_blend` clamps the requested weight to `[0, 1]` and
returns a `weight_clamped` flag.

Python tool signatures keep the legacy positional first argument
(`actor_name`) and add new keyword-only fields (`mcp_id`, `format`,
`scale`, `blend_mode`, `bank_slope`). `add_landscape_spline` and
`add_road_spline` validate `points` (>= 2 entries) on the Python side
before sending.

Tests: `Python/tests/unit/test_w1_landscape_part2_executed_envelope.py`
(20 cases: 8 parametrised executed assertions + 8 paired queued-regression
guards + 4 targeted checks for the clamp / mesh resolution / point
validation / dual-field payload paths).

Remaining for #80 part3 / part4: `landscape_sculpt`, `landscape_smooth`,
`landscape_flatten`, `landscape_ramp`, `landscape_erosion`,
`landscape_noise` (all six need LandscapeEditMode for live application;
will follow the same metadata-on-actor pattern + brush param echo).
