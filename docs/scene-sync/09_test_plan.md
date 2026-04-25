<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 09. Test Plan

## 1. Purpose

Verify the SurrealDB + Rust sync system is deterministic, safe, and compatible with Unreal.

The most important tests are identity and idempotency. If those fail, congratulations, you built a duplicate actor generator.

## 2. Test layers

| Layer | Tooling | Purpose |
|---|---|---|
| Rust unit | `cargo test` | Hashing, validation, planning. |
| Rust integration | `cargo test` + SurrealDB | Repository/schema behavior. |
| API | HTTP client | Axum endpoints. |
| Unreal contract | mock + real bridge | JSON command compatibility. |
| Python facade | pytest | MCP tool behavior. |
| E2E | local Unreal | DB -> sync -> editor. |

## 3. Rust unit tests

### TEST-UNIT-001: `mcp_id` validation

Valid:

```text
wall_001
castle_001:wall:north:0001
```

Invalid:

```text
""
"has space"
"contains/slash"
```

### TEST-UNIT-002: Hash stability

Changing `updated_at` must not change `desired_hash`.

### TEST-UNIT-003: Hash changes on transform

Changing location must change `desired_hash`.

### TEST-UNIT-004: Tags sorted in hash

Different tag order must produce same hash.

### TEST-UNIT-005: Plan create

Desired has one object; actual empty -> one create.

### TEST-UNIT-006: Plan noop

Desired and actual match -> one noop.

### TEST-UNIT-007: Plan transform update

Actual transform differs -> update_transform.

### TEST-UNIT-008: Plan delete

Desired tombstone and actual exists -> delete.

### TEST-UNIT-009: Duplicate desired ID

Duplicate desired `mcp_id` -> conflict/error.

### TEST-UNIT-010: Duplicate actual ID

Two actual actors with same `mcp_id` -> conflict.

## 4. SurrealDB integration tests

### TEST-DB-001: Connect

Rust connects, signs in, selects namespace/database.

### TEST-DB-002: Migrations idempotent

Running migrations twice succeeds.

### TEST-DB-003: Default scene

`scene:main` exists after startup.

### TEST-DB-004: Upsert object

Same `mcp_id` updates one object, not two.

### TEST-DB-005: Unique index

Duplicate `(scene, mcp_id)` is rejected.

### TEST-DB-006: Tombstone delete

`deleted=true`, `sync_status=pending`.

### TEST-DB-007: Snapshot

Snapshot stores current groups/objects.

### TEST-DB-008: Restore

Restore modifies desired state only.

## 5. API tests

### TEST-API-001: Health

`GET /health` returns success.

### TEST-API-002: Upsert endpoint

`POST /objects/upsert` writes object and returns hash.

### TEST-API-003: Plan endpoint with mock Unreal

DB one object, mock actual empty -> create count 1.

### TEST-API-004: Apply endpoint with mock Unreal

Create operation succeeds and object becomes synced.

## 6. Unreal bridge contract tests

### TEST-UE-001: Spawn accepts `mcp_id`

Actor gets `mcp_id:<id>` tag.

### TEST-UE-002: Actor listing returns tags

`get_actors_in_level` includes tags array.

### TEST-UE-003: Find by `mcp_id`

Correct actor returned.

### TEST-UE-004: Transform by `mcp_id`

Actor moves, identity remains.

### TEST-UE-005: Delete by `mcp_id`

Actor deleted. Second delete handled safely.

## 7. Python facade tests

### TEST-PY-001: Calls Rust

Mock Rust endpoint and verify payload.

### TEST-PY-002: Rust unavailable

Tool returns structured error.

### TEST-PY-003: Existing tools still import

Adding `scene_tools.py` does not break startup.

## 8. End-to-end tests

### TEST-E2E-001: One cube lifecycle

1. Start SurrealDB.
2. Start Rust.
3. Start Python MCP.
4. Start Unreal.
5. `scene_upsert_actor(cube_001)`.
6. `scene_plan_sync`.
7. Expect create=1.
8. `scene_sync`.
9. Actor appears.
10. `scene_sync` again.
11. Expect noop=1, create=0.

### TEST-E2E-002: Move cube

1. Create cube.
2. Sync.
3. Upsert same `mcp_id` with new location.
4. Plan update.
5. Sync.
6. Same actor moves.

### TEST-E2E-003: Delete cube

1. Create cube.
2. Tombstone cube.
3. Plan with delete.
4. Sync with `allow_delete=false`, skip.
5. Sync with `allow_delete=true`, delete.

### TEST-E2E-004: Snapshot restore

1. Create 10 objects.
2. Snapshot.
3. Move/delete some.
4. Restore snapshot.
5. Plan and sync.
6. Scene returns to snapshot desired state.

### TEST-E2E-005: Wall generator

1. `scene_create_wall` with 10 segments.
2. Plan create=10.
3. Sync.
4. Re-sync noop=10.

## 9. Performance tests

### TEST-PERF-001: Plan 1,000 objects

Target: under 2 seconds.

### TEST-PERF-002: No-op sync 1,000 objects

Target: no Unreal mutation calls.

### TEST-PERF-003: Create 1,000 objects

MVP may be slower. Record baseline before optimizing.

## 10. Failure tests

### TEST-FAIL-001: Unreal offline

Plan/apply returns structured error.

### TEST-FAIL-002: SurrealDB offline

Rust health reports degraded or startup fails.

### TEST-FAIL-003: Invalid asset

Operation fails, object status error, other ops continue.

### TEST-FAIL-004: Partial failure

9/10 succeed, 1 fails, retry does not duplicate 9.

## 11. CI commands

Rust:

```bash
cd rust/scene-syncd && cargo fmt --check && cargo clippy -- -D warnings && cargo test
```

Python:

```bash
cd Python && python -m pytest tests/unit
```

Do not require Unreal in normal CI. Unreal tests belong in local/manual or dedicated heavy workflow.

## 12. Fixture files

```text
tests/fixtures/desired/one_cube.json
tests/fixtures/desired/wall_10_segments.json
tests/fixtures/actual/empty.json
tests/fixtures/actual/one_cube.json
tests/fixtures/plans/create_one_cube.json
tests/fixtures/plans/noop_one_cube.json
```
