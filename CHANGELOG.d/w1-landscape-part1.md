### landscape part1: 8 handlers promoted to executed envelope

- Issue: Refs #80
- PR: codex-stubs-w1-landscape-part1
- Wave: W1
- Handlers promoted: 8 / 22
- New `executed: true` cases:
  - `set_landscape_size`
  - `set_landscape_collision`
  - `set_landscape_grass_output`
  - `add_landscape_hole`
  - `apply_landscape_material`
  - `attach_landscape_rvt`
  - `set_landscape_nanite`
  - `set_landscape_world_partition`
- Build verified: scripted-only (no self-hosted UE 5.7 runner in this environment)

Approach (UE 5.7-safe): introduces `ResolveLandscapeActor()` which finds the
target `ALandscape` by `mcp_id`, `actor_name`, or `actor_label` (falling back
to "the only ALandscape in the world" when none of the keys are given), and a
`LandscapeMetaPersist()` helper that wraps each mutation in
`FMCPScopedTransaction`, calls `Actor->Modify()`, writes the change into both
the public ALandscape property (where possible) AND
`UPackage::SetMetaData()` so the requested state survives editor restart.

Where the property is fully public in 5.7 we set it directly (`bEnableNanite`,
`CollisionMipLevel`, `bIncludeGridSizeInNameForLandscapeActors`,
`LandscapeMaterial`, `RuntimeVirtualTextures.AddUnique`). Where the change
needs `LandscapeEditMode` (sculpt / hole punch / paint) we persist the
requested action as metadata so the wave-close PR can replay it.

`set_landscape_grass_output` and `attach_landscape_rvt` resolve assets via
`LoadObject<...>` and reject missing paths with structured errors.

Python tool signatures keep `actor_name` as the first positional argument
(legacy callers untouched) and gain keyword-only fields (`mcp_id`,
`collision_mip_level`, `simple_collision_mip_level`,
`generate_overlap_events`, `shape`, `x/y/width/height`,
`include_grid_size_in_name`, `layer_name`, `rvt_path`). The Python payload
also keeps echoing the legacy field names (`rvt_asset_path`, `enable`,
`grid_size`) so existing scripts keep working.

Tests added: `Python/tests/unit/test_w1_landscape_executed_envelope.py`
(19 cases: each handler asserted with `utils.envelope.assert_executed`, a
paired queued-regression guard, signature-compat sanity checks, and a
structured-error path that surfaces `available_landscape_labels`).
