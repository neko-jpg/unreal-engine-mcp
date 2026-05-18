# UnrealMCP Handler Split Architecture

> Source of truth for "which C++ handler class owns which JSON command"
> in the UnrealMCP plugin. Keep in sync with
> `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPRouter.cpp`
> and the registration table inside
> `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp`.

## TL;DR

- Every JSON `command` name is mapped to a small `int32 RouteId` by
  `FEpicUnrealMCPRouter::RouteCommand`.
- `UEpicUnrealMCPBridge::ExecuteCommand` dispatches that `RouteId`
  through a registry of `TFunction` closures populated once during
  construction (see Phase 4 / Issue #32 for the registry refactor).
- One handler class owns one `RouteId`. Adding a new handler is **a
  single-line edit** in `EpicUnrealMCPBridge::RegisterHandlers()`,
  plus the matching command-name -> RouteId entries in
  `EpicUnrealMCPRouter.cpp`.

## Routing table

| Route | Handler class                              | Source file (under `Plugins/UnrealMCP/Source/UnrealMCP/`) | Representative commands |
| ----: | ------------------------------------------ | --------------------------------------------------------- | ----------------------- |
|     0 | _(inline ping closure)_                    | `Private/EpicUnrealMCPBridge.cpp`                        | `ping`                  |
|     1 | `FEpicUnrealMCPActorCommands`              | `Private/Commands/EpicUnrealMCPActorCommands.cpp`        | `spawn_actor`, `clone_actor`, `apply_scene_delta`, `find_actor_by_mcp_id`, `delete_actor`, `set_actor_transform` |
|     2 | `FEpicUnrealMCPBlueprintCommands`          | `Private/Commands/EpicUnrealMCPBlueprintCommands.cpp`    | `create_blueprint`, `compile_blueprint`, `spawn_blueprint_actor`, `add_component_to_blueprint`, `set_blueprint_parent_class` |
|     3 | `FEpicUnrealMCPBlueprintGraphCommands`     | `Private/Commands/EpicUnrealMCPBlueprintGraphCommands.cpp` | `add_blueprint_node`, `connect_nodes`, `create_variable`, `create_function`, `add_event_node` |
|     4 | `FEpicUnrealMCPMaterialCommands`           | `Private/Commands/EpicUnrealMCPMaterialCommands.cpp`     | `create_material`, `create_material_instance`, `set_material_scalar_parameter`, `add_material_node` |
|     5 | `FEpicUnrealMCPProjectEditorCommands`      | `Private/Commands/EpicUnrealMCPProjectEditorCommands.cpp` | `set_default_map`, `create_level`, `start_pie`, `take_screenshot`, `enable_world_partition` |
|     6 | `FEpicUnrealMCPContentBrowserCommands`     | `Private/Commands/EpicUnrealMCPContentBrowserCommands.cpp` | `list_assets`, `move_asset`, `delete_asset`, `audit_assets`, `bulk_rename` |
|     7 | `FEpicUnrealMCPAssetImportCommands`        | `Private/Commands/EpicUnrealMCPAssetImportCommands.cpp`  | `import_fbx_mesh`, `import_texture`, `import_gltf`, `export_asset`, `export_level` |
|     8 | `FEpicUnrealMCPMeshEditingCommands`        | `Private/Commands/EpicUnrealMCPMeshEditingCommands.cpp`  | `set_nanite_settings`, `mesh_remesh`, `generate_lods`, `add_socket`, `set_collision_complexity` |
|     9 | `FEpicUnrealMCPEnhancedInputCommands`      | `Private/Commands/EpicUnrealMCPEnhancedInputCommands.cpp` | `create_input_action`, `add_enhanced_input_mapping`, `setup_enhanced_input_binding` |
|    10 | `FEpicUnrealMCPGameplayFrameworkCommands`  | `Private/Commands/EpicUnrealMCPGameplayFrameworkCommands.cpp` | `create_gamemode_blueprint`, `create_pawn`, `place_player_start`, `setup_camera_component` |
|    11 | `FEpicUnrealMCPUMGCommands`                | `Private/Commands/EpicUnrealMCPUMGCommands.cpp`          | `create_widget_blueprint`, `add_widget_to_widget_blueprint`, `bind_widget_button_on_clicked`, `compile_widget_blueprint` |
|    12 | `FEpicUnrealMCPRenderingCommands`          | `Private/Commands/EpicUnrealMCPRenderingCommands.cpp`    | `set_lumen_enabled`, `set_path_tracing`, `set_anti_aliasing`, `spawn_post_process_volume` |
|    13 | `FEpicUnrealMCPLightingAtmosphereCommands` | `Private/Commands/EpicUnrealMCPLightingAtmosphereCommands.cpp` | `set_light_intensity`, `set_sun_position`, `create_hdri_backdrop`, `build_lighting` |
|    14 | `FEpicUnrealMCPDataTableCommands`          | `Private/Commands/EpicUnrealMCPDataTableCommands.cpp`    | `create_data_table`, `import_csv_to_data_table`, `update_data_table_row` |
|    15 | `FEpicUnrealMCPAudioCommands`              | `Private/Commands/EpicUnrealMCPAudioCommands.cpp`        | `create_sound_cue`, `add_audio_component`, `spawn_ambient_sound` |
|    16 | `FEpicUnrealMCPSequencerCommands`          | `Private/Commands/EpicUnrealMCPSequencerCommands.cpp`    | `create_level_sequence`, `add_transform_track`, `add_camera_cut_track`, `add_keyframe` |
|    17 | `FEpicUnrealMCPVroidCommands`              | `Private/Commands/EpicUnrealMCPVroidCommands.cpp`        | `vroid_check_plugin`, `vroid_import_vrm`, `vroid_spawn_avatar` |
|    18 | `FEpicUnrealMCPCesiumCommands`             | `Private/Commands/EpicUnrealMCPCesiumCommands.cpp`       | `cesium_check_plugin`, `cesium_setup_georeference`, `cesium_add_tileset` |
|    19 | `FEpicUnrealMCPProceduralCommands`         | `Private/Commands/EpicUnrealMCPProceduralCommands.cpp`   | `spawn_tile_grid`, `spawn_procedural_actor_batch`, `create_spline_mesh_from_segments`, `clear_generated_group`, `request_cognitive_processing` |
|    20 | `FEpicUnrealMCPNavigationCommands`         | `Private/Commands/EpicUnrealMCPNavigationCommands.cpp`   | `create_nav_mesh_volume`, `create_patrol_route`, `create_spline_from_points`, `create_behavior_tree`, `create_blackboard` |
|    21 | _(reserved)_                               | _n/a_                                                    | Reserved for the next handler split |
|    22 | `FEpicUnrealMCPPhysicsCommands`            | `Private/Commands/EpicUnrealMCPPhysicsCommands.cpp`      | `set_actor_collision_preset`, `set_actor_physics`, `create_physical_material`, `spawn_radial_force`, `spawn_physics_constraint` |
|    23 | `FEpicUnrealMCPValidationCommands`         | `Private/Commands/EpicUnrealMCPValidationCommands.cpp`   | `compile_all_blueprints`, `run_map_check`, `find_broken_references` |
|    24 | `FEpicUnrealMCPInstanceCommands`           | `Private/Commands/EpicUnrealMCPInstanceCommands.cpp`     | `create_draft_proxy`, `update_draft_proxy`, `delete_draft_proxy`, `spawn_instance_set`, `update_instance_set`, `delete_instance_set`, `get_instance_set_state`, `list_instance_sets` |

`FEpicUnrealMCPEditorCommands` (`Private/Commands/EpicUnrealMCPEditorCommands.cpp`)
is intentionally a slim shell after Phase 1/2/3/4. It is **not** registered in
the bridge's runtime registry. New generic editor commands should go here only
if no existing handler fits and the command surface is genuinely small; see
"When to grow `EditorCommands` vs. spawn a new handler" below.

## Adding a new handler class

Use this recipe whenever a domain (physics, animation, niagara, ...)
deserves its own handler. The acceptance bar is one bullet per file the
change has to touch:

1. **Create `EpicUnrealMCP<Domain>Commands.h`** under
   `Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/`. Mirror an
   existing handler's shape (constructor, `HandleCommand`,
   `GetEditorWorld`, one private `Handle<Command>` method per command).
2. **Create `EpicUnrealMCP<Domain>Commands.cpp`** under
   `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/`. Implement
   `HandleCommand` as a `TMap<FString, Handler>` dispatcher exactly
   like `FEpicUnrealMCPPhysicsCommands` does. Keep file-local helpers
   `static` so they do not leak.
3. **Register the handler in `EpicUnrealMCPBridge.cpp`**. Add a single
   line in `UEpicUnrealMCPBridge::RegisterHandlers()`:

   ```cpp
   RegisterHandler<FEpicUnrealMCP<Domain>Commands>(<NextRouteId>);
   ```

   ...plus the matching `#include` near the top of `Bridge.cpp`. Do
   **not** add a typed member field on the bridge -- the registry's
   captured `TSharedPtr` is the single owner.
4. **Add command-name entries to `EpicUnrealMCPRouter.cpp`**. For each
   JSON command name owned by the new handler, add
   `{TEXT("<command_name>"), <NextRouteId>},` to the `Router` map.
5. **Update this doc** (the routing table above) so contributors can
   find the new handler at a glance.
6. **(Optional) Add a smoke test** in
   `Python/tests/e2e/test_phase23_handler_split_smoke.py` so a future
   refactor that drops the route is caught immediately.

## When to grow `EditorCommands` vs. spawn a new handler

`FEpicUnrealMCPEditorCommands` was intentionally trimmed to a shell during
Phases 1-4. Use the rules below before adding code to it:

- **Keep it small.** Only add commands that genuinely belong on a
  generic "editor utility" surface (e.g. a single console-style helper
  that does not cluster with anything else).
- **One or two handlers max.** If a feature warrants more than one or
  two `Handle<Command>` methods, create a new
  `FEpicUnrealMCP<Domain>Commands` class instead. This is what
  prevented `EditorCommands.cpp` from regrowing past 3000 lines after
  Phase 1.
- **No domain entanglement.** If the new commands depend on a third-
  party module (Cesium, VRM, Niagara, modeling tools), spin up a new
  handler so the dependency stays scoped.
- **Hot-spot avoidance.** Anything that touches `World->SpawnActor`,
  `UPackage`, asset import, blueprint compilation, or large data
  structures should land in a domain handler, not in `EditorCommands`.

If the answer to "where does this command go?" is "nowhere obvious",
that is the strongest signal you need a new handler class.

## Refactor history

| Phase | Commit prefix             | Outcome |
| :---- | :------------------------ | :------ |
| 1     | `refactor: complete Phase 1 - extract ProceduralCommands + Router` | Lifted the original switch-based dispatcher into `FEpicUnrealMCPRouter` and split out `FEpicUnrealMCPProceduralCommands` (route 19), bringing along Physics, Validation, Cognitive, Draft and InstanceSet handlers. |
| 2     | `refactor(Phase 2): extract Actor CRUD into FEpicUnrealMCPActorCommands` | Moved every `spawn_actor` / `delete_actor` / `apply_scene_delta` / `clone_actor` / `find_*_by_mcp_id` handler into `FEpicUnrealMCPActorCommands` (route 1, kept stable for backward compat). |
| 3     | `refactor(Phase 3): extract NavAI + Spline into FEpicUnrealMCPNavigationCommands` | Moved NavMesh, NavModifier, NavLink, BehaviorTree, Blackboard, PatrolRoute and SplineFromPoints handlers into `FEpicUnrealMCPNavigationCommands` (route 20). `FEpicUnrealMCPEditorCommands` became a slim shell. |
| 4     | _Issue #31_               | Split `FEpicUnrealMCPProceduralCommands` again. Physics commands moved to `FEpicUnrealMCPPhysicsCommands` (route 22), Validation to `FEpicUnrealMCPValidationCommands` (route 23), Draft + InstanceSet to `FEpicUnrealMCPInstanceCommands` (route 24). `request_cognitive_processing` stayed on route 19 because it is currently a single command. |
| 4b    | _Issue #32_               | Replaced the 22-`case` switch in `UEpicUnrealMCPBridge::ExecuteCommand` with a runtime registry of `TFunction` closures. Adding a new handler now requires editing exactly one location in `Bridge.cpp` (plus `Router.cpp`). |

## Pointers

- Registry implementation: `UEpicUnrealMCPBridge::RegisterHandlers()` in
  `Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp`.
- Command-name -> RouteId mapping:
  `FEpicUnrealMCPRouter::RouteCommand` in
  `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPRouter.cpp`.
- Smoke tests for the post-Phase-4 routing:
  `Python/tests/e2e/test_phase23_handler_split_smoke.py`.
- Issues that drove the current architecture: #31 (Phase 4 split), #32
  (registry refactor), #36 (this document), and #35 (E2E safety net).