### anim-rigging part3: final 4 handlers promoted (20/20 = #79 ready to close)

- Issue: Closes #79
- PR: codex-stubs-w1-anim-rigging-part3
- Wave: W1
- Handlers promoted in this PR: 4
- Cumulative for #79: 20 / 20
- New `executed: true` cases:
  - `create_aim_offset` (factory + metadata fallback)
  - `create_control_rig` (factory + metadata fallback)
  - `sequencer_control_rig_track` (metadata on ULevelSequence)
  - `connect_metahuman` (metadata on resolved host: USkeleton / USkeletalMesh / UBlueprint)

Approach (UE 5.7-safe): reuses `TryCreateRuntimeResolvedAsset` and
`AnimMetaFallback` from part2. For `create_control_rig`, the host
resolution falls back to `host_asset_path` → `skeleton_path` →
`skeletal_mesh_path` (first non-empty wins). `connect_metahuman` resolves
its host asset by `host_asset_path` and surfaces a warning when
`metahuman_id` is empty so the wave-close replay can branch.

Python tool signatures extended to forward all C++-side fields while
keeping the legacy positional signatures intact:
- `connect_metahuman` accepts legacy `metahuman_blueprint_path` /
  `target_actor` and forwards them as `metahuman_id` / `host_asset_path`
  respectively (existing TestRetargeting test passes unchanged).
- `sequencer_control_rig_track` validates `level_sequence_path` and
  accepts `binding_guid` / `track_name`.
- `create_control_rig` accepts `skeleton_path`, `skeletal_mesh_path`,
  and `host_asset_path`.

Tests: `Python/tests/unit/test_w1_anim_rigging_part3_executed_envelope.py`
(12 cases: 4 parametrised executed assertions + 4 paired queued-regression
guards + 2 mode-specific checks + 2 legacy-compat sanity).
