<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 12. Architecture Decision Records

## ADR-0001: Use SurrealDB as desired scene store

Status: Accepted

### Context

The scene needs durable object records, procedural metadata, snapshots, future relationships, and possible live updates.

### Decision

Use SurrealDB for desired scene state.

### Consequences

Positive:

- Natural document model for scene objects.
- Graph relations available later.
- Live queries available later.
- Works with Rust SDK.

Negative:

- Adds database lifecycle.
- Requires schema management.
- Does not remove need for Sync Engine.

## ADR-0002: Use Rust SDK for core DB/sync logic

Status: Accepted

### Context

The user requires Rust SDK. Sync logic benefits from typed models and async runtime.

### Decision

Implement `scene-syncd` in Rust.

### Consequences

Positive:

- Type-safe domain model.
- Clear ownership of DB/sync.
- Better concurrency and error handling.

Negative:

- Additional service process.
- Python/Rust boundary required.

## ADR-0003: Keep Python MCP as facade

Status: Accepted

### Context

Existing MCP server is Python and already registers tools.

### Decision

Add Python `scene_` tools that call Rust service.

### Consequences

Positive:

- Existing tools remain.
- Lower migration risk.
- Rust can evolve independently.

Negative:

- Two-language system.
- Need local HTTP API.

## ADR-0004: Use `mcp_id` as stable identity

Status: Accepted

### Context

Actor names can change and current naming helpers may alter names.

### Decision

Use `mcp_id` as stable logical identity in both DB and Unreal tags.

### Consequences

Positive:

- Idempotent sync possible.
- Restart-safe matching.
- Actor rename safe.

Negative:

- Requires bridge changes.
- Existing actors need migration.

## ADR-0005: Manual sync before live autosync

Status: Accepted

### Context

SurrealDB live queries are useful but risky if every DB edit instantly mutates Unreal.

### Decision

MVP uses explicit `scene_plan_sync` and `scene_sync`. Live autosync comes later and is disabled by default.

### Consequences

Positive:

- Safer.
- Plans are reviewable.
- Easier debugging.

Negative:

- Less automatic at first.

## ADR-0006: Tombstone deletes

Status: Accepted

### Context

Hard deletion loses information before Unreal sync can process it.

### Decision

`scene_delete_actor` sets `deleted=true`. Cleanup is separate.

### Consequences

Positive:

- Safe retry.
- Snapshot/history understandable.
- Delete sync idempotent.

Negative:

- Tombstones accumulate.

## ADR-0007: Store procedural intent separately

Status: Accepted

### Context

A castle is not just many cubes. It has generation parameters and meaning.

### Decision

Use `scene_group` for procedural intent and `scene_object` for concrete actors.

### Consequences

Positive:

- Group-level edits possible.
- Regeneration possible.
- AI can reason structurally.

Negative:

- More schema complexity.

## ADR-0008: Local HTTP between Python and Rust

Status: Accepted

### Context

Python must call Rust service.

### Decision

Use local HTTP JSON with Axum.

### Consequences

Positive:

- Easy from Python.
- Easy to test.
- Future UI can reuse API.

Negative:

- Another port/process.

## ADR-0009: Single-operation Unreal commands first

Status: Accepted

### Context

Existing bridge already supports individual commands. Batch delta needs C++ work.

### Decision

MVP uses existing commands. Batch `apply_scene_delta` later.

### Consequences

Positive:

- Faster MVP.
- Less C++ risk.

Negative:

- Slower for large scenes initially.

## ADR-0010: Default orphan policy is conflict

Status: Accepted

### Context

An Unreal actor with `mcp_id` but no DB record may be leftover or externally created.

### Decision

Default to conflict, not delete.

### Consequences

Positive:

- Prevents accidental deletion.
- Forces explicit decision.

Negative:

- Requires conflict workflow.

## ADR-0011: Desired hash excludes timestamps

Status: Accepted

### Context

Including timestamps would make objects appear changed all the time.

### Decision

Hash only sync-relevant desired fields.

### Consequences

Positive:

- Stable no-op detection.
- Efficient planning.

Negative:

- Hash payload must be maintained as features expand.

## ADR-0012: Snapshot restores DB first

Status: Accepted

### Context

Restore should be inspectable before Unreal changes.

### Decision

Restore modifies desired state only. Sync applies to Unreal later.

### Consequences

Positive:

- Safer.
- Plan can be reviewed.

Negative:

- Extra step required.

## ADR-0013: SurrealDB server mode for MVP

Status: Accepted

### Context

Rust can embed SurrealDB, but server mode is easier to inspect and aligns with WebSocket-based workflows.

### Decision

MVP uses local SurrealDB server at `ws://127.0.0.1:8000`.

### Consequences

Positive:

- Easier debugging.
- CLI inspection.
- Clear separation.

Negative:

- Extra process.

## ADR-0014: Add new `scene_` tools instead of changing old ones

Status: Accepted

### Context

Existing direct tools should keep working.

### Decision

Add parallel scene tools.

### Consequences

Positive:

- Lower risk.
- Side-by-side testing.

Negative:

- Temporary duplicated capability.

## ADR-0015: Use `ActorSink` to migrate generators

Status: Proposed

### Context

Many generators directly spawn actors.

### Decision

Refactor generation to output actor specs through a sink.

### Consequences

Positive:

- Same generator can target Unreal, DB, or dry-run.
- Tests become easier.

Negative:

- Refactor cost.
