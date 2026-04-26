<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 08. tasks.md

## Priority meanings

| Priority | Meaning |
|---|---|
| P0 | Blocks everything. Do first. |
| P1 | Required for MVP. |
| P2 | Required for first useful release. |
| P3 | Important after MVP. |
| P4 | Later enhancement. |

## Milestone 0: Repository preparation

### TASK-0001: Add documentation

Priority: P0
Status: Done

- Create `docs/scene-sync/`.
- Add this document set.
- Link from root README.

### TASK-0002: Create Rust service crate

Priority: P0
Status: Done

### TASK-0003: Add dependencies

Priority: P0
Status: Done

## Milestone 1: Local SurrealDB

### TASK-0101: Add start script

Priority: P0
Status: Done

### TASK-0102: Add `.env.example`

Priority: P0
Status: Done

Include:

```text
SCENE_SYNCD_HOST=127.0.0.1
SCENE_SYNCD_PORT=8787
SURREAL_URL=ws://127.0.0.1:8000
SURREAL_NS=unreal_mcp
SURREAL_DB=scene
SURREAL_USER=root
SURREAL_PASS=secret
UNREAL_MCP_HOST=127.0.0.1
UNREAL_MCP_PORT=55557
SCENE_SYNCD_AUTOSYNC=false
```

## Milestone 2: Rust service skeleton

### TASK-0201: Implement config loader

Priority: P0
Status: Done

### TASK-0202: Add Axum server

Priority: P0
Status: Done

### TASK-0203: Add tracing

Priority: P1
Status: Done

## Milestone 3: SurrealDB connection and migrations

### TASK-0301: Connect using Rust SDK

Priority: P0
Status: Done

### TASK-0302: Add migration runner

Priority: P0
Status: Done

Inline idempotent DDL in `ensure_schema` instead of separate runner.

### TASK-0303: Create schema

Priority: P0
Status: Done

Tables:

- `scene`
- `scene_group`
- `scene_object`
- `scene_snapshot`
- `sync_run`
- `scene_operation`
- `actor_observation`
- `schema_version`

Done when unique `(scene, mcp_id)` index exists.

## Milestone 4: Domain models

### TASK-0401: Transform types

Priority: P0
Status: Done

### TASK-0402: Scene object type

Priority: P0
Status: Done

Validate:

- required `mcp_id`
- required scene
- valid actor type
- transform defaults

### TASK-0403: Desired hash

Priority: P0
Status: Done

Hash sync-relevant fields only.

Done when timestamp changes do not alter hash, but transform changes do.

## Milestone 5: Repository API

### TASK-0501: Ensure default scene

Priority: P0
Status: Done

Create `scene:main` on startup.

### TASK-0502: Upsert object

Priority: P0
Status: Done

Endpoint:

```text
POST /objects/upsert
```

Done when repeated upsert updates same record.

### TASK-0503: Bulk upsert

Priority: P1
Status: Done

Endpoint:

```text
POST /objects/bulk-upsert
```

Done when 100 objects can be written.

### TASK-0504: Mark object deleted

Priority: P1
Status: Done

Endpoint:

```text
POST /objects/delete
```

Done when object has `deleted=true` and `sync_status=pending`.

### TASK-0505: List objects

Priority: P1
Status: Done

Endpoint:

```text
POST /objects/list
```

Done when filters work.

## Milestone 6: Unreal bridge identity

### TASK-0601: Return actor tags

Priority: P0
Status: Done

C++ actor JSON must include `tags`.

### TASK-0602: Spawn accepts `mcp_id`

Priority: P0
Status: Done

Spawned actor must receive:

```text
managed_by_mcp
mcp_id:<id>
```

### TASK-0603: Find by `mcp_id`

Priority: P1
Status: Done

Add `find_actor_by_mcp_id`.

### TASK-0604: Transform by `mcp_id`

Priority: P1
Status: Done

Add `set_actor_transform_by_mcp_id`.

### TASK-0605: Delete by `mcp_id`

Priority: P1
Status: Done

Add `delete_actor_by_mcp_id`.

## Milestone 7: Rust Unreal client

### TASK-0701: TCP JSON command client

Priority: P0
Status: Done

Use `tokio::net::TcpStream`.

### TASK-0702: Actor listing

Priority: P0
Status: Done

Parse actual actors and extract `mcp_id`.

### TASK-0703: Spawn actor

Priority: P1
Status: Done

Send `mcp_id` and tags.

### TASK-0704: Transform actor

Priority: P1
Status: Done

Use mcp_id command if available.

### TASK-0705: Delete actor

Priority: P1
Status: Done

Idempotent missing delete.

## Milestone 8: Sync planner

### TASK-0801: Desired index

Priority: P0
Status: Done

Detect duplicate desired `mcp_id`.

### TASK-0802: Actual index

Priority: P0
Status: Done

Detect duplicate actual `mcp_id`.

### TASK-0803: Create detection

Priority: P0
Status: Done

Desired missing in Unreal -> create.

### TASK-0804: Transform diff

Priority: P0
Status: Done

Transform mismatch -> update_transform.

### TASK-0805: Delete detection

Priority: P1
Status: Done

Tombstoned desired + actual exists -> delete.

### TASK-0806: No-op detection

Priority: P1
Status: Done

Equivalent desired/actual -> noop.

### TASK-0807: Plan endpoint

Priority: P0
Status: Done

`POST /sync/plan`.

## Milestone 9: Sync applier

### TASK-0901: Create sync_run

Priority: P1
Status: Done

Every apply creates run.

### TASK-0902: Apply create

Priority: P0
Status: Done

One DB object creates one Unreal actor.

### TASK-0903: No duplicate re-sync

Priority: P0
Status: Done

Second sync is noop.

### TASK-0904: Apply transform

Priority: P1
Status: Done

DB transform edit moves actor.

### TASK-0905: Apply delete

Priority: P1
Status: Done

Requires `allow_delete=true`.

### TASK-0906: Persist operation result

Priority: P1
Status: Done

Each op records success/error.

## Milestone 10: Python MCP facade

### TASK-1001: Add `scene_client.py`

Priority: P1
Status: Done

Calls Rust HTTP API.

### TASK-1002: Add `scene_tools.py`

Priority: P1
Status: Done

Tools:

- `scene_create`
- `scene_upsert_actor`
- `scene_delete_actor`
- `scene_plan_sync`
- `scene_sync`
- `scene_snapshot_create`
- `scene_snapshot_restore`

### TASK-1003: Register tools

Priority: P1
Status: Done

Import scene tools in MCP entrypoint.

## Milestone 11: Procedural generation

### TASK-1101: `scene_create_wall`

Priority: P2
Status: Done

Writes wall segments to DB.

### TASK-1102: `scene_create_pyramid`

Priority: P2
Status: Done

Writes pyramid blocks to DB.

### TASK-1103: `ActorSink`

Priority: P2
Status: Done

Introduce output abstraction:

- `UnrealActorSink`
- `SceneDbActorSink`
- `DryRunActorSink`

### TASK-1104: Migrate castle helpers

Priority: P3

Large helper migration after simple tools work.

## Milestone 12: Snapshots

### TASK-1201: Create snapshot

Priority: P2
Status: Done

Stores groups and objects.

### TASK-1202: Restore snapshot

Priority: P2
Status: Done

Restores desired state only.

## Milestone 13: Later optimizations

### TASK-1301: `apply_scene_delta`

Priority: P3

Batch operations in C++ bridge.

### TASK-1302: Live query watcher

Priority: P4

Observe `scene_object` changes.

### TASK-1303: Autosync safety

Priority: P4

Default off. Deletes disabled unless explicit.

## MVP cutline

MVP includes:

- Rust service skeleton.
- SurrealDB connection/schema.
- Object upsert/list/delete.
- C++ `mcp_id` tag support.
- Rust Unreal client basic commands.
- Planner create/update/noop.
- Apply create and transform.
- Python facade tools.

Not MVP:

- Live autosync.
- Batch delta.
- Full castle migration.
- UI.
