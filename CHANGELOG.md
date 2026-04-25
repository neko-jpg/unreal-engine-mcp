# Changelog

All notable changes in this fork, relative to the upstream [flopperam/unreal-engine-mcp](https://github.com/flopperam/unreal-engine-mcp), are documented in this file.

---

## [2026-04-25] - Unreal project cleanup and shutdown crash fix

### Fixed

- Fixed an Unreal Editor shutdown crash in `UEpicUnrealMCPBridge::StopServer()` caused by owning `FSocket` instances with `TSharedPtr` while also destroying them through `ISocketSubsystem::DestroySocket()`. The bridge and server runnable now keep socket ownership explicit and release sockets through the Unreal socket subsystem only.
- Fixed UE 5.7 build errors in undo transaction setup by passing `FText` labels to `FScopedTransaction`, and replaced the unavailable `FIPv4Address::Loopback` reference with an explicitly parsed loopback address.
- Removed the project startup action that tried to import `StarterContent.upack`; UE 5.7 installs in this environment do not include that feature pack, and this MCP project does not require Starter Content.

### Changed

- Consolidated the local Unreal project copies back to the canonical `FlopperamUnrealMCP/` tree. The duplicate `FlopperamUnrealMCP 5.7/` and `FlopperamUnrealMCP 5.7 - 2/` project copies were local untracked copies and should not be used as source trees.

### Verification

- Verified the crash reports pointed to `EpicUnrealMCPBridge::StopServer()` during `EditorExit` from the duplicate `FlopperamUnrealMCP 5.7 - 2` project path.
- Built `FlopperamUnrealMCPEditor Win64 Development` with UE 5.7 successfully.
- Launched the canonical project with UE 5.7, confirmed the MCP bridge initialized, then closed the editor process without a new crash report.

---

## [2026-04-24] - Safety, batching, and undo support

### Added

#### New MCP tools

- **`batch_spawn_actors`** (`Python/server/actor_tools.py`): Spawn multiple actors in a single call with per-actor validation, a configurable batch limit (default 500), and a `dry_run` mode that returns the planned actor list without executing. (`Python/server/actor_tools.py`)
- **`get_blueprint_material_info`** (`Python/server/material_tools.py`): Proper `@mcp.tool()`-decorated function that sends `get_blueprint_material_info` to Unreal, replacing the bare alias `get_blueprint_material_info = get_actor_material_info` that was not registered with FastMCP. A backward-compatible alias `_get_blueprint_material_info_alias` is kept for internal use.

#### Input validation layer

- **`Python/server/validation.py`**: New module providing reusable validation helpers:
  - `validate_vector3()`, `validate_color()`, `validate_string()`, `validate_float()`, `validate_int()`, `validate_positive_int()`, `validate_nonneg_int()`, `validate_unreal_path()`
  - `ValidationError` exception class with `field` and `message` attributes.
  - `make_validation_error_response()` and `make_validation_error_response_from_exception()` for uniform error responses.
  - Constants: `MAX_ACTORS_PER_BATCH = 500`, `MAX_WORLD_EXTENT = 1000000.0`.
- Validation applied to:
  - `actor_tools.py`: `find_actors_by_name`, `delete_actor`, `spawn_actor`, `set_actor_transform`
  - `world_building_tools.py`: `create_pyramid`, `create_wall`, `create_maze`
- `create_maze` now rejects requests where the estimated actor count exceeds `MAX_ACTORS_PER_BATCH` before querying Unreal.

#### Batch spawning for world-building tools

- `create_pyramid` and `create_wall` now pre-compute all actor specifications and delegate to `batch_spawn_actors()` instead of spawning actors one at a time via `safe_spawn_actor()`. Both accept a `dry_run` parameter.
- This reduces per-actor validation overhead and centralizes error handling, though each actor still uses a separate TCP command (true C++ batch command not yet implemented).

#### Undo support in C++ plugin

- Added `FScopedTransaction` wrappers to 21 C++ command handlers across three files. This enables Undo in the Unreal Editor for all destructive Blueprint, graph, and editor operations:
  - `EpicUnrealMCPEditorCommands.cpp`: `HandleSpawnActor`, `HandleDeleteActor`, `HandleSetActorTransform`
  - `EpicUnrealMCPBlueprintCommands.cpp`: `HandleCreateBlueprint`, `HandleAddComponentToBlueprint`, `HandleSetPhysicsProperties`, `HandleSetStaticMeshProperties`, `HandleSetMeshMaterialColor`, `HandleSpawnBlueprintActor`, `HandleApplyMaterialToActor`, `HandleApplyMaterialToBlueprint`
  - `EpicUnrealMCPBlueprintGraphCommands.cpp`: `HandleAddBlueprintNode`, `HandleConnectNodes`, `HandleCreateVariable`, `HandleSetVariableProperties`, `HandleAddEventNode`, `HandleDeleteNode`, `HandleSetNodeProperty`, `HandleCreateFunction`, `HandleAddFunctionInput`, `HandleAddFunctionOutput`, `HandleDeleteFunction`, `HandleRenameFunction`
- Added `Actor->Modify()` call in `HandleSetActorTransform` before modifying the transform, so the transaction records the previous state correctly.

#### Tests — Python/C++ command mapping

- Added `TestPythonToCppCommandMapping` class in `Python/tests/unit/test_tool_registration_and_mapping.py` with four tests:
  - `test_python_commands_are_handled_in_cpp`: every command that Python sends to Unreal has a matching C++ dispatcher route.
  - `test_cpp_commands_are_used_by_python`: every C++ command (except whitelisted entries like `ping`) is invoked by at least one Python tool.
  - `test_each_mcp_tool_sends_exactly_one_cpp_command`: structural check that each MCP tool (except known orchestrators) maps to a single C++ command.
  - `test_tool_name_to_command_mapping_is_complete`: verifies a hardcoded 31-entry mapping dict covers all registered tools.
- Added `get_blueprint_material_info` to the existing `TestToolCommandMapping` parameterized test entries.

### Changed

#### README

- Updated tool count from ~38 to 46.
- Added `batch_spawn_actors`, `add_event_node`, `get_actor_material_info`, `get_blueprint_material_info` to the tool table.
- Changed Python version requirement from "3.12+" to "3.10+ (3.12 recommended; 3.10–3.13 supported)" to match `pyproject.toml`.

#### `unreal_mcp_server_advanced.py`

- Re-exports `batch_spawn_actors` from `server.actor_tools`.

### Migration notes

- The bare alias `get_blueprint_material_info = get_actor_material_info` in `material_tools.py` has been replaced with a proper `@mcp.tool()` function. The old alias still works as `_get_blueprint_material_info_alias` for internal use, but MCP clients will now see `get_blueprint_material_info` as a registered tool with its own schema.
- `create_pyramid` and `create_wall` now return batch-style result objects (with `spawned_count`, `failed_count`, `actors`, and optionally `failed` keys) instead of the previous `{"success": True, "actors": [...]}` format. Callers that depend on the exact response shape should be updated.

---

## [2026-04-24] - Fork compliance update

- Added MIT license text as `LICENSE`.
- Added explicit credit to the original repository in `README.md`.
- Added a clear statement that this repository is an unofficial fork and not the official Flopperam project.
- Added a clear statement that this repository is separate from the paid Flopperam Agent product.
- Added guidance for a non-confusing fork display name: "Unreal Engine MCP Community Fork (Unofficial)".

---

## Known differences from upstream (2026-04-24)

This section summarizes all structural and behavioral differences between this fork and the upstream `flopperam/unreal-engine-mcp` repository as of this date.

### Python server

| Area | Upstream | This fork |
|------|----------|-----------|
| `material_tools.py` | `get_blueprint_material_info` is a bare alias for `get_actor_material_info`, not registered as an MCP tool | `get_blueprint_material_info` is a proper `@mcp.tool()` function that sends `get_blueprint_material_info` to Unreal |
| `actor_tools.py` | No `batch_spawn_actors` tool; no input validation on tool functions | `batch_spawn_actors` added with validation, dry_run, and batch limit; validation on `find_actors_by_name`, `delete_actor`, `spawn_actor`, `set_actor_transform` |
| `world_building_tools.py` | `create_pyramid` and `create_wall` spawn one actor at a time via `safe_spawn_actor`; `create_maze` has no actor limit guard | Both delegate to `batch_spawn_actors()` with pre-computed specs and `dry_run` parameter; `create_maze` rejects requests exceeding `MAX_ACTORS_PER_BATCH=500` |
| `validation.py` | Does not exist | New module with vector/color/string/float/int/path validators, `ValidationError`, batch limits |
| Test mapping | `TestToolCommandMapping` has 25 entries; no `TestPythonToCppCommandMapping` | 26 entries (adds `get_blueprint_material_info`); new `TestPythonToCppCommandMapping` class with 4 drift-detection tests |

### C++ plugin

| Area | Upstream | This fork |
|------|----------|-----------|
| `EpicUnrealMCPEditorCommands.cpp` | No `FScopedTransaction` on any handler | `FScopedTransaction` on `HandleSpawnActor`, `HandleDeleteActor`, `HandleSetActorTransform`; `Actor->Modify()` added before transform changes |
| `EpicUnrealMCPBlueprintCommands.cpp` | No `FScopedTransaction` | `FScopedTransaction` on 8 handlers (create blueprint, add component, set physics/mesh/material properties, spawn blueprint actor, apply material to actor/blueprint) |
| `EpicUnrealMCPBlueprintGraphCommands.cpp` | No `FScopedTransaction` | `FScopedTransaction` on 9 handlers (add node, connect nodes, create/set variable, add event node, delete node, set node property, create/rename/delete function, add function input/output) |

### Documentation

| Area | Upstream | This fork |
|------|----------|-----------|
| `README.md` | Tool count ~38; Python 3.12+; no fork notice | Tool count 46; Python 3.10+ (3.12 recommended); fork notice at top |
| `CHANGELOG.md` | Does not exist or is empty | Full fork changelog and diff table |
| `AGENTS.md` | Does not exist or is upstream version | Fork-specific with repository guidance, known risks, required checks |

### Not yet changed (planned)

The following improvements are identified but not yet implemented:

- **C++ `batch_spawn_actors` command**: Currently `batch_spawn_actors` sends individual `spawn_actor` commands over separate TCP connections. A single C++ handler accepting an actor array would eliminate per-actor connection overhead.
- **Persistent TCP connection**: `send_command()` still opens and closes a TCP socket per request. Connection reuse or pooling would reduce latency.
- **`safe_spawn_actor` N+1 name-check problem**: Each actor spawn calls `find_actors_by_name` first. Batch spawn should pre-fetch existing names once.
- **Response envelope standardization**: Responses do not yet follow a uniform `{success, data, error, warnings, duration_ms, command_id}` schema.
- **Authentication/authorization**: No auth token, no allowlist for destructive commands, defaults bind to 127.0.0.1 but does not warn on 0.0.0.0.
- **Remaining world-building tools migration**: `create_tower`, `create_staircase`, `create_town`, `create_castle_fortress`, `create_suspension_bridge`, `create_aqueduct`, `create_arch`, `construct_house`, `construct_mansion` still spawn one actor at a time.
- **Structured logging**: No JSONL audit log; no command-level duration tracking.
- **Idempotency keys**: No retry-safety mechanism for write commands.
- **Blueprint compile results**: `set_node_property`, `connect_nodes`, etc. do not return compile status.
- **C++ command registry / `list_capabilities`**: No dynamic capability query or version negotiation.
- **Pydantic input models**: Tools use raw `Dict[str, Any]` instead of typed models.
