<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 11. Migration Plan

## 1. Goal

Migrate from direct Python -> Unreal commands to SurrealDB desired-state sync without breaking existing tools.

## 2. Migration principle

Add new `scene_` tools beside old tools.

Do not silently change old tool behavior. Silent behavior changes are where debugging goes to become a ghost story.

## 3. Current model

```text
Python MCP tool -> UnrealConnection -> C++ bridge -> Unreal
```

Current limitations:

- No durable state.
- No stable actor identity.
- No diff planning.
- No snapshot/restore.
- Large generation is command-heavy.
- Existing “batch” behavior may still call many single operations.

## 4. Target model

```text
Python scene tool -> Rust scene-syncd -> SurrealDB
scene_sync -> Rust planner/applier -> Unreal bridge -> Unreal
```

## 5. Phase 0: Docs and skeleton

Add:

- docs
- Rust crate
- `.env.example`
- SurrealDB start script
- Rust `/health`

No existing behavior changes.

Risk: low.

## 6. Phase 1: Unreal identity support

Add:

- tags in actor listing
- `mcp_id` accepted by spawn
- `managed_by_mcp` tag
- `mcp_id:<id>` tag

Risk: medium.

Rollback: existing tools can ignore new fields.

## 7. Phase 2: SurrealDB CRUD

Implement:

- create scene
- upsert object
- bulk upsert
- list objects
- mark deleted

No Unreal mutation yet.

Risk: low.

## 8. Phase 3: Plan-only sync

Implement:

- read desired from SurrealDB
- read actual from Unreal
- match by `mcp_id`
- produce plan

No mutation.

Risk: low.

## 9. Phase 4: Create-only sync

Implement:

- create missing actors
- attach `mcp_id`
- mark synced
- re-sync no-op

Risk: medium.

This is the first major proof.

## 10. Phase 5: Transform updates

Implement:

- desired transform changes
- plan update
- apply update
- mark synced

Risk: medium.

## 11. Phase 6: Deletes

Implement:

- tombstone in DB
- plan delete
- require `allow_delete=true`
- delete by `mcp_id`

Risk: high if identity is not solid.

## 12. Phase 7: Snapshot/restore

Implement:

- snapshot current desired state
- restore desired state
- sync restored state

Risk: medium.

## 13. Phase 8: Simple procedural tools

Add:

- `scene_create_wall`
- `scene_create_pyramid`

These should write DB objects, not directly spawn actors.

Risk: medium.

## 14. Phase 9: `ActorSink` abstraction

Current style:

```python
safe_spawn_actor(unreal, params)
```

Target style:

```python
sink.spawn(params)
```

Sinks:

- `UnrealActorSink`
- `SceneDbActorSink`
- `DryRunActorSink`

This lets one generator target direct Unreal, DB desired state, or dry-run. Fancy? No. Necessary? Painfully yes.

## 15. Phase 10: Complex generators

Migrate:

- tower
- castle
- mansion
- bridge/aqueduct
- city/village generators

Only after `ActorSink` is stable.

## 16. Phase 11: Batch delta

Add Unreal command:

```text
apply_scene_delta
```

Move from one command per operation to grouped operations.

Risk: medium/high.

Do after correctness is proven.

## 17. Phase 12: Live query autosync

Use SurrealDB live query watcher.

Default:

```text
SCENE_SYNCD_AUTOSYNC=false
SCENE_SYNCD_AUTOSYNC_ALLOW_DELETE=false
```

Risk: high.

Do not enable before manual sync is boringly reliable.

## 18. Existing level import

Modes:

### Managed-only

Import actors already having `mcp_id`.

Safe.

### Name-pattern import

Import actors matching name prefix.

Example:

```text
Castle_*
Wall_*
Pyramid_*
```

Generate `mcp_id` from name once, then attach tags.

### Full import

Import all actors.

Use only in clean test level. Production levels are not a junk drawer to scrape blindly.

## 19. Compatibility matrix

| Existing behavior | Migration behavior |
|---|---|
| `spawn_actor` works | Still works. |
| `create_wall` direct | Still works. |
| `scene_create_wall` | New DB path. |
| Actor name used | Still display name, not identity. |
| `mcp_id` | New stable identity for managed path. |
| Python sends commands | Python scene tools call Rust. |

## 20. Rollback strategy

If Rust/SurrealDB path breaks:

- Stop using `scene_` tools.
- Keep existing immediate tools.
- Ignore SurrealDB state.
- Clean actors by `managed_by_mcp` tag if needed.

If C++ identity support breaks:

- Revert tag additions.
- Immediate tools still run without `mcp_id`.

## 21. Success metrics

- One cube lifecycle works.
- Re-sync is no-op.
- 100-segment wall works.
- Snapshot restore works.
- Existing immediate tools still work.
- No duplicate actors under normal sync.
- Plan explains every operation.
