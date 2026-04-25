<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 05. Sync Engine Design

## 1. Purpose

The Sync Engine reconciles desired state in SurrealDB with actual state in Unreal.

Without this, SurrealDB is just a stylish storage box. Very modern. Very useless.

## 2. Definitions

| Term | Meaning |
|---|---|
| Desired object | `scene_object` record in SurrealDB. |
| Actual actor | Actor currently in Unreal. |
| Managed actor | Unreal actor with valid `mcp_id` tag. |
| Unmanaged actor | Unreal actor without `mcp_id`. |
| Sync plan | List of create/update/delete/noop/conflict operations. |
| Sync apply | Execution of plan against Unreal. |

## 3. Algorithm

```text
1. Load desired objects from SurrealDB.
2. Load actual actors from Unreal.
3. Extract mcp_id from actor tags.
4. Index desired by mcp_id.
5. Index actual by mcp_id.
6. For every desired object:
   - deleted + actual exists -> delete
   - deleted + actual missing -> noop
   - not deleted + actual missing -> create
   - not deleted + actual exists -> compare fields
7. For every actual managed actor missing from desired:
   - classify as orphan/conflict by policy.
8. Sort operations.
9. Return plan.
10. If apply requested, execute operations and persist results.
```

## 4. Matching rules

Primary match:

```text
desired.mcp_id == actual.mcp_id
```

Migration fallback only:

```text
desired.unreal_actor_name == actual.name
```

Never use display name as normal identity. That path leads to duplicate actors and an evening you will not get back.

## 5. Operation types

### Create

Condition:

```text
desired.deleted == false AND actual missing
```

Action:

- call `spawn_actor`
- include `mcp_id`
- include tags
- update `unreal_actor_name`
- set `last_applied_hash=desired_hash`
- set `sync_status=synced`

### Update transform

Condition:

```text
actual exists AND transform differs beyond tolerance
```

Action:

- call `set_actor_transform_by_mcp_id` if available
- fallback to name-based transform during migration
- update hash after success

### Update visual

Condition:

```text
material/color/visibility differs
```

MVP:

- Store plan operation.
- Apply only fields supported by bridge.
- Unsupported fields return `unsupported`, not silent success.

### Delete

Condition:

```text
desired.deleted == true AND actual exists
```

Action:

- require `allow_delete=true`
- call `delete_actor_by_mcp_id` if available
- fallback to name-based delete during migration
- treat missing actor as idempotent success

### Noop

Condition:

```text
desired equivalent to actual
```

Action:

- no Unreal command

### Conflict

Examples:

- duplicate desired `mcp_id`
- duplicate actual `mcp_id`
- orphan managed actor
- unsupported destructive change
- external edit with conflict policy

## 6. Operation ordering

Recommended order:

1. Creates
2. Asset/component changes
3. Transform updates
4. Visual/material updates
5. Tag/folder/name updates
6. Deletes

Deletes last by default.

## 7. Sync plan JSON

```json
{
  "scene_id": "main",
  "summary": {
    "create": 12,
    "update_transform": 3,
    "delete": 1,
    "noop": 200,
    "conflict": 0,
    "unsupported": 0
  },
  "operations": [
    {
      "action": "create",
      "mcp_id": "wall_001",
      "reason": "Desired object missing from Unreal",
      "desired": {},
      "actual": null
    }
  ],
  "warnings": []
}
```

## 8. Idempotency

### Create

Before spawning, check actual actors by `mcp_id` again if possible.

### Update

Only update changed fields.

### Delete

Deleting a missing actor is success if desired object is tombstoned.

### Retry

Successful operations should not repeat after partial failure.

## 9. Drift policy

Unreal may drift due to manual editor changes.

Policies:

| Policy | Behavior |
|---|---|
| `db_wins` | DB overwrites Unreal. |
| `unreal_wins` | Unreal updates DB. |
| `conflict` | Report and do nothing. |

MVP default:

```text
db_wins for generated managed actors
conflict for orphans and duplicate identities
```

## 10. Orphan policy

An orphan is a managed Unreal actor with `mcp_id` but no DB object.

Default:

```text
conflict
```

Other supported later:

- `ignore`
- `import`
- `delete`

Do not delete orphans automatically in MVP. “Helpful deletion” is just sabotage with a friendly tooltip.

## 11. Float tolerance

Use tolerance when comparing transforms:

```text
location epsilon: 0.01
rotation epsilon: 0.01 degrees
scale epsilon: 0.0001
```

## 12. Applier pseudo-code

```rust
pub async fn apply_plan(plan: SyncPlan, repo: &Repo, unreal: &UnrealClient) -> Result<SyncSummary> {
    let run = repo.create_sync_run(&plan).await?;
    let mut summary = SyncSummary::default();

    for op in plan.operations {
        repo.record_operation_planned(&run, &op).await?;

        let result = match op.action {
            SyncAction::Create => unreal.spawn_actor(op.to_spawn_request()?).await,
            SyncAction::UpdateTransform => unreal.set_actor_transform(op.to_transform_request()?).await,
            SyncAction::Delete => unreal.delete_actor(op.to_delete_request()?).await,
            SyncAction::Noop => Ok(CommandResult::noop()),
            _ => Ok(CommandResult::skipped("conflict or unsupported")),
        };

        match result {
            Ok(res) => {
                repo.mark_operation_success(&run, &op, &res).await?;
                repo.update_object_after_success(&op, &res).await?;
                summary.success += 1;
            }
            Err(err) => {
                repo.mark_operation_error(&run, &op, &err).await?;
                summary.failed += 1;
            }
        }
    }

    repo.finish_sync_run(&run, &summary).await?;
    Ok(summary)
}
```

## 13. Retry rules

Retry:

- socket timeout
- editor temporarily busy
- connection reset

Do not retry:

- invalid asset path
- duplicate identity
- invalid transform
- unsupported actor type

Default:

```text
max_attempts=3
initial_delay_ms=100
backoff=2.0
```

## 14. Modes

| Mode | Meaning |
|---|---|
| `plan_only` | Only compute diff. |
| `apply_safe` | Apply creates/updates, skip deletes. |
| `apply_all` | Apply creates/updates/deletes, still block conflicts. |
| `repair_identity` | Attach missing `mcp_id` tags to fallback-matched actors. |
| `import_actual` | Create DB objects from Unreal actors. |

## 15. MVP checklist

- [ ] Extract `mcp_id`.
- [ ] Detect duplicate desired IDs.
- [ ] Detect duplicate actual IDs.
- [ ] Plan create.
- [ ] Plan transform update.
- [ ] Plan delete.
- [ ] Plan no-op.
- [ ] Persist sync run.
- [ ] Persist operation.
- [ ] Apply create.
- [ ] Apply transform update.
- [ ] Apply delete with explicit flag.
- [ ] Mark object synced after success.
- [ ] Record failures.
- [ ] Re-run without duplicates.
