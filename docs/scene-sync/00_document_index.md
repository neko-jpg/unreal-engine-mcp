<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 00. Document Index

## Purpose

This document pack defines a SurrealDB + Rust SDK implementation plan for converting the current Unreal MCP workflow from direct command execution to database-backed desired-state synchronization.

Current model:

```text
AI/Python tool -> direct Unreal command -> editor changes now
```

Target model:

```text
AI/MCP tool -> SurrealDB desired state -> Rust Sync Engine -> Unreal changes only through explicit sync
```

The important change is not merely “add a database”. The important change is that **the scene state becomes the product**, and Unreal becomes the rendered/realized result of that state. Yes, software finally discovers memory. Miracles happen slowly.

## Files

| File | Role |
|---|---|
| `00_document_index.md` | Reading order and overview. |
| `01_requirements_definition.md` | Requirements, scope, acceptance criteria. |
| `02_system_architecture.md` | End-to-end architecture. |
| `03_surrealdb_schema.md` | Tables, fields, indexes, SurrealQL draft. |
| `04_rust_sdk_service_design.md` | Rust service design using SurrealDB Rust SDK. |
| `05_sync_engine_design.md` | Desired/actual diff and apply model. |
| `06_unreal_bridge_contract.md` | Required Unreal C++ bridge command contract. |
| `07_mcp_tool_api_spec.md` | Python MCP tool API. |
| `08_implementation_tasks.md` | Detailed tasks.md roadmap. |
| `09_test_plan.md` | Unit, integration, contract, E2E tests. |
| `10_operations_runbook.md` | Setup, commands, troubleshooting. |
| `11_migration_plan.md` | Migration from current immediate tools. |
| `12_adrs.md` | Architecture decision records. |
| `13_scenectl_cli.md` | CLI workflow for diagnostics, listing, tagging, planning, applying, and safe deletes. |

## Recommended reading order

1. Requirements.
2. Architecture.
3. Schema.
4. Sync Engine.
5. Rust service.
6. Unreal bridge contract.
7. MCP API.
8. Tasks.
9. Test plan.
10. Runbook.
11. Migration.
12. ADRs.
13. CLI workflow.

## Most important rules

1. `mcp_id` is the stable identity. Actor name is not identity.
2. SurrealDB stores desired state. Unreal stores actual state.
3. Sync must be idempotent. Re-running sync must not duplicate actors.
4. Manual `scene_plan_sync` comes before `scene_sync`.
5. Live autosync is later, not MVP.
6. Python MCP should be a facade. Rust owns SurrealDB and sync logic.
7. Existing immediate tools remain during migration.
8. Deletes are tombstoned in DB first, then applied through explicit sync.
9. Procedural intent must be stored separately from concrete actors.
10. Batch C++ `apply_scene_delta` is a later optimization, not the first step.

## Proposed high-level folder layout

```text
Project-MUSE/
  Python/
    server/
      scene_tools.py
      scene_client.py
  rust/
    scene-syncd/
      Cargo.toml
      src/
        main.rs
        config.rs
        api/
        db/
        domain/
        sync/
        unreal/
        watch/
  docs/
    scene-sync/
  .surreal/
```

## MVP definition

The MVP is complete when:

- SurrealDB runs locally.
- Rust `scene-syncd` connects using the SurrealDB Rust SDK.
- Python MCP can call Rust service.
- `scene_upsert_actor` writes desired state.
- `scene_plan_sync` computes create/update/delete/noop.
- `scene_sync` creates one actor in Unreal.
- Re-running sync is no-op.
- Editing DB transform moves the same actor.
- Tombstoning object deletes actor only when explicitly allowed.
- Snapshot/restore works for a small scene.
