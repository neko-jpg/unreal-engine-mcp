### landscape part3: final 6 handlers promoted (22/22 = #80 ready to close)

- Issue: Closes #80
- PR: codex-stubs-w1-landscape-part3
- Wave: W1
- Handlers promoted in this PR: 6
- Cumulative for #80: 22 / 22
- New `executed: true` cases:
  - `landscape_sculpt`
  - `landscape_smooth`
  - `landscape_flatten`
  - `landscape_ramp`
  - `landscape_erosion`
  - `landscape_noise`

Approach (UE 5.7-safe): the last 6 brush handlers all need
`LandscapeEditMode` to apply live, so each one routes through the
existing `LandscapeMetaPersist` helper to persist the requested brush
parameters as MCP-namespaced `UPackage::SetMetaData` keys inside
`FMCPScopedTransaction`. `landscape_ramp` validates `start_xy` /
`end_xy` (>= 2 entries each) and rejects bad input with a structured
error.

Python tool signatures keep the legacy positional first argument
(`actor_name`) and add keyword-only `mcp_id` and (for `landscape_ramp`)
`ramp_width`. `landscape_sculpt` keeps echoing `location_xy` as
`[0.0, 0.0]` when the caller omits it (legacy test compat).

Tests: `Python/tests/unit/test_w1_landscape_part3_executed_envelope.py`
(15 cases: 6 parametrised executed assertions + 6 paired queued-regression
guards + 3 validation / default-payload checks).
