### anim-rigging part1: 8 handlers promoted to executed envelope

- Issue: Refs #79
- PR: codex-stubs-w1-anim-rigging-part1
- Wave: W1
- Handlers promoted: 8 / 20
- New `executed: true` cases:
  - `add_control_rig_bone`
  - `add_control_rig_control`
  - `add_ik_goal`
  - `add_ik_solver`
  - `set_retarget_chain`
  - `set_retarget_manager`
  - `set_facial_animation`
  - `set_morph_target`
- Build verified: scripted-only (no self-hosted UE 5.7 runner in this environment)

Approach (UE 5.7-safe): the 7 handlers above route through a new
`AnimMetaPersist` helper that writes MCP-namespaced `UPackage::SetMetaData`
keys onto the resolved asset, calls `UObject::Modify()` /
`UPackage::MarkPackageDirty()` and emits `{success:true, data:{executed:true,
asset_path, asset_class, mcp_metadata_keys_persisted, ...}}`. This sidesteps
the `IKRigEditor` / `ControlRigEditor` private symbol problem because the
metadata layer is fully linkable from `Core` / `CoreUObject`.

`set_morph_target` goes one step deeper and validates the morph target name
against `USkeletalMesh::FindMorphTarget`, returning the available list when
the lookup fails so callers can self-correct.

Python tool signatures for `set_facial_animation` and `set_retarget_manager`
were extended with the new fields (`curve_name`, `weight`, `rig_type`,
`rig_mode`, `preview_mesh`) while keeping legacy kwargs (`anim_sequence_path`,
`rig_bp_path`) optional.

Tests added: `Python/tests/unit/test_w1_anim_rigging_executed_envelope.py`
(17 cases: each handler asserted with `utils.envelope.assert_executed` and
a paired queued-regression guard).
