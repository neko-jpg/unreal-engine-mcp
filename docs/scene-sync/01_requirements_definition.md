<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 01. Requirements Definition

## 1. Background

The existing Unreal MCP system sends Python-generated commands directly to Unreal. That works for simple actions, but breaks down when the AI needs to revise, restore, diff, or reason about a large generated scene.

The new system must use **SurrealDB** as the database and the **SurrealDB Rust SDK** as the core DB integration path.

## 2. Product vision

Create a durable scene database where AI edits desired state, not raw editor commands.

The system must support:

- Stable object identity.
- Durable scene state.
- Diff-based synchronization.
- Snapshots and restore.
- Procedural generation metadata.
- Later live query based autosync.
- Later multi-agent/multi-user scene editing.

## 3. In scope

- Rust service `scene-syncd`.
- SurrealDB schema.
- Rust repository layer using SurrealDB Rust SDK.
- Sync planner and applier.
- Python MCP facade tools.
- Unreal C++ bridge identity additions.
- Snapshot/restore.
- Migration path for existing generation tools.

## 4. Out of scope for MVP

- Full real-time multiplayer.
- Full Unreal material graph diffing.
- Full Blueprint graph state storage.
- Automatic live sync enabled by default.
- Rewriting the whole MCP server in Rust.
- Complete editor UI.

## 5. Functional requirements

### FR-001: Create scene

The system shall create or ensure a scene record.

Required fields:

- `id`
- `name`
- `description`
- `status`
- `active_revision`
- `created_at`
- `updated_at`

Acceptance:

- `scene:main` can be created automatically.
- Scene can be selected by MCP tools.

### FR-002: Upsert desired object

The system shall write a desired actor/object record to SurrealDB.

Required fields:

- `scene`
- `mcp_id`
- `desired_name`
- `actor_type`
- `asset_ref`
- `transform`
- `tags`
- `desired_hash`
- `sync_status`
- `deleted`

Acceptance:

- Same `scene + mcp_id` updates one object, not duplicates.
- Upsert does not touch Unreal.
- Desired change sets `sync_status=pending`.

### FR-003: Stable identity

The system shall use `mcp_id` as stable identity.

Rules:

- Actor display name is not identity.
- `mcp_id` must be stored in SurrealDB.
- Unreal actors must have `mcp_id:<id>` tag or equivalent metadata.
- Duplicate `mcp_id` in one scene is invalid.

Acceptance:

- Re-running sync after actor creation does not create duplicate actors.
- Actor rename does not break sync if tag remains.

### FR-004: Actual state observation

Rust shall read current Unreal actors through the bridge.

Minimum fields:

- actor name
- class
- location
- rotation
- scale
- tags
- extracted `mcp_id`

Acceptance:

- Actors without `mcp_id` are classified as unmanaged.
- Actors with duplicate `mcp_id` become conflicts.

### FR-005: Plan sync

The system shall compare desired DB state and actual Unreal state.

Actions:

- `create`
- `update_transform`
- `update_visual`
- `delete`
- `noop`
- `conflict`
- `unsupported`

Acceptance:

- Plan is deterministic.
- Plan is inspectable JSON.
- Plan does not mutate Unreal.

### FR-006: Apply sync

The system shall execute planned operations against Unreal.

Acceptance:

- Create calls spawn.
- Transform update calls transform command.
- Delete calls delete command only when allowed.
- Success updates `last_applied_hash`.
- Failure records `scene_operation` error.

### FR-007: Snapshot

The system shall snapshot desired state.

Acceptance:

- Snapshot includes groups and objects.
- Snapshot can be restored without Unreal running.
- Restore modifies DB first, Unreal only after sync.

### FR-008: Procedural groups

The system shall store generation intent.

Examples:

- wall
- pyramid
- castle
- mansion
- bridge
- room

Acceptance:

- Group stores generator name, parameters, seed, revision.
- Objects reference group.

### FR-009: Python MCP facade

The existing Python MCP server shall expose scene tools that call Rust HTTP API.

Acceptance:

- Python does not contain SurrealQL.
- Rust owns DB and sync logic.

## 6. Non-functional requirements

### NFR-001: Idempotency

Running the same sync repeatedly must not duplicate actors or keep applying unchanged transforms.

### NFR-002: Safety

Default workflow must support dry-run planning before apply.

### NFR-003: Local-first

Must run locally with:

- Unreal Editor
- Python MCP server
- Rust `scene-syncd`
- SurrealDB server

### NFR-004: Performance

MVP targets:

- Plan 1,000 objects in under 2 seconds on a normal dev machine.
- No-op sync of 1,000 objects should not issue 1,000 Unreal mutations.
- Large creation can be slower initially, then optimized through batch delta.

### NFR-005: Recoverability

System must survive restarts of Python, Rust service, Unreal, or SurrealDB without losing desired state.

### NFR-006: Observability

Every sync run must record:

- run id
- start/end timestamps
- planned/applied/failed counts
- operation logs
- warnings
- fatal errors

## 7. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Unreal actor lacks `mcp_id` | duplicate actors | Add C++ tag support first. |
| Live sync too early | accidental editor mutation | Manual sync first. |
| Duplicate IDs | corrupt plan | Unique index and planner validation. |
| Partial failure | DB/UE drift | Operation log and retry. |
| Python and Rust both own DB logic | split brain | Python is facade only. |
| Over-designed graph schema | slow start | Start object/group/snapshot/op first. |

## 8. MVP acceptance criteria

- `scene-syncd` starts.
- SurrealDB connection works.
- Schema migration works.
- `scene:main` exists.
- `scene_upsert_actor` writes object.
- `scene_plan_sync` detects create.
- `scene_sync` creates actor.
- Actor has `mcp_id` tag.
- Re-sync is no-op.
- Transform edit updates same actor.
- Tombstone + `allow_delete=true` deletes actor.
- Snapshot/restore changes desired state.
