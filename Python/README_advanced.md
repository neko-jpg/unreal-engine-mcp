# Unreal MCP Advanced Server

A streamlined MCP server for Unreal Engine composition and Blueprint workflows. The entrypoint is `unreal_mcp_server_advanced.py`; implementation is split by responsibility under `server/` and reusable helpers under `helpers/`.

## What's Included

This server exposes **46 tools** across five categories.

### Actor Management (6 tools)

| Tool | Description |
|------|-------------|
| `get_actors_in_level` | List all actors in the current level |
| `find_actors_by_name(pattern)` | Find actors by name pattern (supports wildcards) |
| `spawn_actor(name, type, location, rotation, scale, static_mesh)` | Spawn a single actor |
| `batch_spawn_actors(actors, dry_run)` | Spawn multiple actors with per-actor validation and optional dry-run |
| `delete_actor(name)` | Remove an actor from the level |
| `set_actor_transform(name, location, rotation, scale)` | Modify actor position, rotation, or scale |

### Blueprint System (9 tools)

| Tool | Description |
|------|-------------|
| `create_blueprint(name, parent_class)` | Create a new Blueprint class |
| `add_component_to_blueprint(blueprint_name, component_type, component_name, ...)` | Add a component to a Blueprint |
| `set_static_mesh_properties(blueprint_name, component_name, static_mesh)` | Set mesh asset on a StaticMeshComponent |
| `set_physics_properties(blueprint_name, component_name, ...)` | Configure physics simulation parameters |
| `compile_blueprint(blueprint_name)` | Compile a Blueprint to apply changes |
| `read_blueprint_content(blueprint_path, ...)` | Read and analyze full Blueprint content |
| `analyze_blueprint_graph(blueprint_path, graph_name, ...)` | Analyze a specific graph with node and connection details |
| `get_blueprint_variable_details(blueprint_path, variable_name)` | Inspect variable type, default value, and metadata |
| `get_blueprint_function_details(blueprint_path, function_name, ...)` | Inspect function parameters, return values, and graph |

### Blueprint Graph (12 tools)

| Tool | Description |
|------|-------------|
| `add_node(blueprint_name, node_type, pos_x, pos_y, ...)` | Add a node to a Blueprint graph |
| `add_event_node(blueprint_name, event_name, ...)` | Add an event node to a Blueprint graph |
| `connect_nodes(blueprint_name, source_node_id, source_pin, target_node_id, target_pin, ...)` | Connect two pins |
| `delete_node(blueprint_name, node_id, ...)` | Delete a node from a Blueprint graph |
| `set_node_property(blueprint_name, node_id, property_name, ...)` | Set a property on a Blueprint node |
| `create_variable(blueprint_name, variable_name, variable_type, ...)` | Create a variable in a Blueprint |
| `set_blueprint_variable_properties(blueprint_name, variable_name, ...)` | Modify properties of an existing Blueprint variable |
| `create_function(blueprint_name, function_name, return_type)` | Create a new function in a Blueprint |
| `add_function_input(blueprint_name, function_name, param_name, param_type, ...)` | Add an input parameter to a function |
| `add_function_output(blueprint_name, function_name, param_name, param_type, ...)` | Add an output parameter to a function |
| `delete_function(blueprint_name, function_name)` | Delete a function from a Blueprint |
| `rename_function(blueprint_name, old_function_name, new_function_name)` | Rename a function in a Blueprint |

### Materials (6 tools)

| Tool | Description |
|------|-------------|
| `get_available_materials(search_path, include_engine_materials)` | List available materials in the project |
| `apply_material_to_actor(actor_name, material_path, material_slot)` | Apply a material to an actor |
| `apply_material_to_blueprint(blueprint_name, component_name, material_path, material_slot)` | Apply a material to a Blueprint component |
| `get_actor_material_info(actor_name)` | Get material info for an actor |
| `get_blueprint_material_info(blueprint_name, component_name)` | Get material info for a Blueprint component |
| `set_mesh_material_color(blueprint_name, component_name, color, ...)` | Set a color on a mesh component via material parameter |

### World Building (13 tools)

| Tool | Description |
|------|-------------|
| `create_pyramid(base_size, block_size, location, ..., dry_run)` | Build a stepped pyramid |
| `create_wall(length, height, block_size, location, orientation, ..., dry_run)` | Build a wall from blocks |
| `create_maze(rows, cols, cell_size, wall_height, location)` | Generate a solvable maze |
| `create_tower(height, base_size, block_size, location, ..., tower_style)` | Build a tower (cylindrical/square/tapered) |
| `create_staircase(steps, step_size, location, ...)` | Build a staircase |
| `create_arch(radius, segments, location, ...)` | Build an arch from blocks |
| `construct_house(width, depth, height, location, ..., house_style)` | Build a house (modern/cottage/mansion) |
| `construct_mansion(mansion_scale, location, ...)` | Build a mansion with multiple wings |
| `create_town(town_size, building_density, location, ..., architectural_style)` | Build a town with infrastructure |
| `create_castle_fortress(castle_size, location, ..., architectural_style)` | Build a castle with surrounding village |
| `create_suspension_bridge(span_length, deck_width, ..., dry_run)` | Build a suspension bridge |
| `create_aqueduct(arches, arch_radius, tiers, ..., dry_run)` | Build a multi-tier aqueduct |
| `spawn_physics_blueprint_actor(name, mesh_path, location, mass, ...)` | Spawn a physics-enabled actor |

## Batch Spawning

`batch_spawn_actors` accepts a list of actor dicts and spawns them with a single tool call:

```python
batch_spawn_actors([
    {"name": "Wall_001", "type": "StaticMeshActor", "location": [0, 0, 0], "static_mesh": "/Engine/BasicShapes/Cube.Cube"},
    {"name": "Wall_002", "type": "StaticMeshActor", "location": [100, 0, 0]},
], dry_run=False)
```

- Each actor is validated individually before spawning.
- `dry_run=True` returns the planned actor list without executing.
- The batch limit is 500 actors by default (`MAX_ACTORS_PER_BATCH`).

`create_pyramid`, `create_wall`, and `create_suspension_bridge` / `create_aqueduct` also accept `dry_run=True` to preview the actor list before spawning.

## Input Validation

Tools with validation (`actor_tools`, `world_building_tools`):

- Vector3 fields (`location`, `rotation`, `scale`) check length (must be 3), type (numbers), range, NaN, and Infinity.
- String fields reject empty strings and enforce max length (256 chars).
- `validate_unreal_path` requires paths starting with `/`.
- `create_maze` rejects requests where the estimated actor count exceeds 500.

## Undo Support

All destructive C++ operations (spawn, delete, transform, Blueprint creation/editing, node manipulation, material changes) are wrapped in `FScopedTransaction`. Each operation is individually undoable in the Unreal Editor. Batch operations currently create one transaction per actor; undoing a full batch requires multiple undo actions.

## Usage

```bash
python unreal_mcp_server_advanced.py
```

The server connects to `127.0.0.1:55557` by default. Override with environment variables:

```bash
UNREAL_MCP_HOST=127.0.0.1 UNREAL_MCP_PORT=55558 python unreal_mcp_server_advanced.py
```

## Differences from Upstream

See `CHANGELOG.md` for a complete list of fork modifications, including:
- `batch_spawn_actors` and `get_blueprint_material_info` as proper MCP tools
- Input validation in `server/validation.py`
- `FScopedTransaction` undo wrappers in the C++ plugin
- Python/C++ command drift detection tests
- `dry_run` support for spawning tools