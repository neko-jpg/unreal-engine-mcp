# React for Unreal Engine v3.0 - Architecture & Usage

> This file is the canonical entry-point for the React-for-UE v3.0
> implementation that ships under PR1-PR9. Read it together with the original
> plan at `docs/dev/plans/react_for_ue_v_3_implementation_plan.md`.

## Overview

React for UE v3.0 turns natural-language scene intents into a structured
**DesignPatch**, persists it as desired state in the scene-syncd database,
applies it through a **Hybrid** path (Rust applier for material/light,
Python `PatchExecutor` for fog/atmosphere/audio/vfx), and offers a vision
feedback loop with deterministic metrics plus an optional VLM rubric.

```
intent  ->  IntentResolver  ->  TargetResolver  ->  Experts (5)  ->  DesignPatch
                                                                          |
                                                                          v
                                                                  PatchCompiler
                                                                          |
                                                +-------------------------+--------------------------+
                                                v                                                    v
                              scene_component upsert (DB authority)                  direct UE commands (Python executor)
                                                |                                                    |
                                                v                                                    v
                                Rust component_applier (material/light)         set_height_fog_properties / spawn_ambient_sound / ...
```

## Public MCP Tools

| Tool | Purpose |
|---|---|
| `scene_edit(intent, mode=...)` | Plan or apply a natural-language scene edit. |
| `scene_refine(intent, ref_patch_id=...)` | Iterative refine; inherits target/mood from prior patch. |
| `scene_preview(scene_id)` | Screenshot + visual metrics + (optional) VLM score. |
| `scene_describe(scene_id)` | Compact SceneContextPack for the model. |
| `scene_explain_plan(patch_id)` | Markdown + JSON walkthrough of a stored DesignPatch. |
| `scene_snapshot_restore_by_name(name)` | Restore latest snapshot matching a name. |
| `scene_snapshot_create_v3(name)` | Snapshot the current desired state (v3 wrapper). |
| `scene_list_snapshots_v3()` | List snapshots for a scene (v3 wrapper). |

## scene_edit modes

- `dry_run` - build and store a DesignPatch, do **not** touch UE or the DB.
- `apply_safe` - rejects destructive patches; takes a snapshot first, then runs.
- `apply_all` - same as `apply_safe` but accepts destructive patches when `approve=True`.

## Risk levels

- `safe` - no approval required.
- `review` - apply_safe accepts; UI may surface a confirmation.
- `destructive` - requires `approve=True` AND `mode="apply_all"`.

## CapabilityRegistry

Experts never hardcode UE command names. They look up a `capability_id`
through `server.planning.capability_registry.get_default_registry()` which
returns `Capability(domain, transport, command, durable_model, risk)`.

The curated registry lives in `Python/server/planning/capability_registry.py`.
The script `python -m scripts.dump_capabilities` writes
`docs/dev/capabilities.json` with the full surface: curated capabilities, the
list of every `@mcp.tool()` decorated function, and the 42 C++ bridge routes.

## Hybrid apply path

| component_type | transport      | applier                                  |
|----------------|----------------|------------------------------------------|
| material       | component_apply | Rust `sync::component_applier::apply_pending` |
| light          | component_apply | Rust `sync::component_applier::apply_pending` |
| atmosphere     | direct_ue       | Python `PatchExecutor`                  |
| audio          | direct_ue       | Python `PatchExecutor`                  |
| vfx            | direct_ue       | Python `PatchExecutor`                  |
| navmesh / ai_* | scene_syncd     | DB only (existing behaviour)            |

Unsupported types in the Rust applier return
`ApplyOutcome::UnsupportedHandledExternally` so the Python executor takes
over without any extra wiring.

## scene_component schema additions (PR7)

```
desired_hash:       string                (computed by compute_desired_hash)
last_applied_hash:  option<string>
sync_status:        string DEFAULT 'pending'
deleted:            bool   DEFAULT false
revision:           int    DEFAULT 1
last_operation_id:  option<string>
updated_by:         option<string>
```

Two new indexes: `(scene, component_type)` and `(scene, sync_status)`.

Migration is forward-compatible (`DEFINE FIELD OVERWRITE`). On startup call
`SurrealSceneRepository::backfill_component_desired_hashes()` to fill the
desired_hash for any pre-v3.0 rows. The legacy component_types
(`navmesh`, `ai_patrol`, `ai_behavior`) keep working unchanged.

## Vision

- `scene_preview` always returns metrics (`Pillow` + `NumPy`).
- VLM provider is selected via `MCP_VLM_PROVIDER` (`openai`, `anthropic`, `null`).
- Without `OPENAI_API_KEY` the analyzer falls back to `NullProvider` and the
  preview tool returns `vlm_status="disabled"` or `vlm_status="null_provider"`.
- CI should set `MCP_VLM_PROVIDER=null`.
- VLM results are cached to `MCP_VLM_CACHE_DIR` keyed by
  `(screenshot_sha1, rubric_id, model)` with a default 24h TTL.

## Snapshot restore by name

`POST /snapshots/restore_by_name { scene_id, name, restore_mode }` resolves
the latest snapshot with that name (by `created_at`). If multiple snapshots
match, `warnings` lists the candidate snapshot ids.

## PR sequence

The implementation lands in 9 PRs over 6 weeks following the plan in
`docs/dev/plans/react_for_ue_v_3_implementation_plan.md`:

1. PR1 - planning (DesignPatch + CapabilityRegistry + dump script)
2. PR2 - intent (SceneContextPack + scene_summarizer + scene_describe)
3. PR3 - intent_resolver + target_resolver + 50-fixture regression
4. PR4 - 5 domain experts + 5 mood profiles
5. PR5 - scene_edit(dry_run) + scene_explain_plan + safety
6. PR6 - PatchCompiler + PatchExecutor + apply_safe + FakeUnrealConnection
7. PR7 - Rust scene_component schema, component_planner, component_applier, restore_by_name
8. PR8 - vision/screenshot, visual_metrics, vision_analyzer, scene_preview, scene_refine
9. PR9 - E2E (cave, osaka, refine 100x, restore by name) + 1000-component idempotency + telemetry + demo

## UE 5.7 compliance

Any C++ change touched by this stack must:

1. Verify the call against UE 5.7 public docs / GitHub before merging.
2. Use `TryUpdateDefaultConfigFile()` (the v5.7 replacement for the
   deprecated `UpdateDefaultConfigFile()`).
3. Add UE-required test coverage.

React-for-UE v3.0 deliberately ships **zero new C++ commands** so the AGENTS
constraints stay satisfied. The only Rust shim added to `unreal/client.rs` is
the public `send_command_value` wrapper that funnels through the existing
TCP transport.


## Production-readiness checklist (v1.0)

- [x] Backfill desired_hash on scene-syncd startup (`backfill_component_desired_hashes`)
- [x] PatchExecutor structured-log telemetry (`patch.apply start` / `patch.apply done`)
- [x] Ambiguous target -> `requires_approval=True` + warning
- [x] VLM image resized to 1024px long edge before encoding
- [x] OPENAI_API_KEY missing -> auto NullProvider, CI safe
- [x] Operation log via `/operations/record`, recent via `/operations/recent`
- [x] scene_component `sync_status` filter (`pending_external` for Python handoff)
- [x] Rust+Python desired_hash parity (SHA1 over canonical JSON)
- [x] Snapshot restore_by_name via `find_snapshot_by_name`
- [x] Contract tests for legacy/v3 component_upsert payload coexistence
- [x] KPI tests for dry_run < 2s and 100 actor apply < 2s (CI relaxed)
