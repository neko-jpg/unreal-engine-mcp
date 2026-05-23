### anim-rigging part2: 8 more handlers promoted (12/20 total)

- Issue: Refs #79
- PR: codex-stubs-w1-anim-rigging-part2
- Wave: W1
- Handlers promoted in this PR: 8
- Cumulative for #79: 12 / 20
- New `executed: true` cases:
  - `add_anim_graph_node`, `create_anim_state_machine`
  - `add_anim_state`, `create_anim_transition_rule`
  - `add_notify_state`
  - `set_control_rig_constraint`
  - `create_ik_rig` (factory + metadata fallback)
  - `create_ik_retargeter` (factory + metadata fallback)
- Build verified: scripted-only (no self-hosted UE 5.7 runner attached)

Approach (UE 5.7-safe):

- 6 handlers re-use the `AnimMetaPersist` helper from part1 to write
  MCP-namespaced `UPackage::SetMetaData` keys onto the resolved
  UAnimBlueprint / UAnimSequence / UControlRigBlueprint asset.
- `create_ik_rig` and `create_ik_retargeter` introduce
  `TryCreateRuntimeResolvedAsset()` which looks up the wanted asset class
  and factory class via `FindObject<UClass>` at runtime. When the
  `IKRigEditor` module ships in the engine install we materialise a real
  asset via `IAssetTools::CreateAsset`. When the editor module is absent,
  we degrade to `AnimMetaFallback()`, which persists the requested intent
  (wanted class, package, asset name, source/target IK rig paths) on a
  host asset (skeletal mesh or target IK rig) so a future IKRigEditor
  follow-up can replay it.
- Both factory and fallback paths return `executed: true` with a `mode`
  field (`factory` or `metadata_fallback`) so callers can branch on the
  shape of the response.

Python tool signatures were extended to forward the new C++ fields:
- `add_anim_state` now accepts `graph_name` (alias of legacy
  `state_machine`) and `anim_sequence_path`.
- `add_notify_state` forwards both `anim_path` (new) and
  `anim_sequence_path` (legacy), plus `notify_class` / `notify_state_class`.
- `create_ik_retargeter` forwards both `source_ik_rig_path` /
  `target_ik_rig_path` (new) and `source_ik_rig` / `target_ik_rig`
  (legacy). New optional `host_asset_path` lets callers pin the metadata
  fallback host.

Tests: `Python/tests/unit/test_w1_anim_rigging_part2_executed_envelope.py`
(17 cases: 6 parametrised executed assertions + 6 paired queued-regression
guards + 2 factory/fallback mode checks + 2 legacy-kwarg compat sanity).
