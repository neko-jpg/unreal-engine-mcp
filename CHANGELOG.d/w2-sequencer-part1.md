### sequencer-extension part1: 6 handlers promoted to executed envelope

- Issue: Closes #87
- PR: codex-stubs-w2-sequencer-part1
- Wave: W2
- Handlers promoted: 6 / 6
- New `executed: true` cases:
  - `spawn_camera_rail` — spline-based camera rail actor with USplineComponent
  - `spawn_camera_crane` — ACineCameraActor with height offset
  - `sequencer_render_preview` — metadata persist on ULevelSequence for render request
  - `register_take_recorder_source` — metadata persist on target actor for Take Recorder
  - `add_control_rig_track` — metadata persist on ULevelSequence for ControlRig binding
  - `spawn_level_sequence_actor` — ALevelSequenceActor spawn + sequence link

Approach (UE 5.7-safe): world-spawning handlers use GEditor + UWorld::SpawnActor.
Asset-metadata handlers use FMCPScopedTransaction + UPackage::SetMetaData.
All return `{success:true, data:{executed:true, ...}}`.

Tests added: `Python/tests/unit/test_w2_sequencer_executed_envelope.py`
