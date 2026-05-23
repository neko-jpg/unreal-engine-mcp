### Water: 8 handlers promoted (part 1/2)

- Issue: #92
- PR: codex-stubs-w3-water-part1
- Wave: W3
- Handlers promoted: 8 / 15
- New `executed: true` cases:
  - `enable_water_plugin` -- Water plugin availability check
  - `spawn_water_body_ocean` -- AWaterBodyOcean spawn
  - `spawn_water_body_lake` -- AWaterBodyLake + spline setup
  - `spawn_water_body_river` -- AWaterBodyRiver + spline setup
  - `spawn_water_body_custom` -- AWaterBodyCustom spawn
  - `configure_river_spline` -- USplineComponent configuration
  - `set_water_material` -- UWaterBodyComponent material assignment
  - `configure_water_wave` -- UWaterWaves configuration
- Approach (UE 5.7-safe): Direct AWaterBody* spawn + component configuration
- Tests added: `Python/tests/unit/test_w3_water_executed_envelope.py`
