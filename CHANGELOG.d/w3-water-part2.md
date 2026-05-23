### Water: 7 handlers promoted (part 2/2)

- Issue: #92
- PR: codex-stubs-w3-water-part2
- Wave: W3
- Handlers promoted: 7 / 15 (total: 15/15)
- New `executed: true` cases:
  - `configure_water_flow` -- UWaterBodyComponent WaterVelocity configuration
  - `configure_buoyancy` -- UBuoyancyComponent setup on an actor
  - `configure_water_mesh_actor` -- AWaterZone / UWaterMeshComponent tile size
  - `configure_underwater_post_process` -- UWaterBodyComponent post process setup
  - `configure_shoreline` -- FWaterCurveSettings shoreline shape
  - `configure_water_landscape_carving` -- bAffectsLandscape + WaterHeightmapSettings
  - `attach_floating_actor` -- UBuoyancyComponent pontoon positions
- Approach (UE 5.7-safe): Direct UWaterBodyComponent / UBuoyancyComponent / UWaterMeshComponent API calls
- Tests added: `Python/tests/unit/test_w3_water_part2_executed_envelope.py`
