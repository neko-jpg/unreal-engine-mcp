<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 03. SurrealDB Schema

## 1. Schema purpose

The schema stores the desired scene state, procedural intent, sync history, observations, and snapshots.

The minimum usable model is:

```text
scene -> scene_group -> scene_object
scene -> scene_snapshot
scene -> sync_run -> scene_operation
scene -> actor_observation
```

## 2. Identity rules

### Record IDs

Recommended deterministic IDs:

```text
scene:main
scene_group:castle_001
scene_object:castle_001_wall_north_0001
scene_snapshot:main_20260425_001
sync_run:main_20260425_153000
```

### `mcp_id`

`mcp_id` is the stable identity shared with Unreal.

Examples:

```text
wall_001
castle_001:wall:north:0001
castle_001:tower:corner_ne:level_0003
pyramid_001:block:layer_002:x_003_y_004
```

Rules:

- Unique within scene.
- Never derived from temporary Unreal actor name.
- Stored in SurrealDB.
- Stored on Unreal actor as `mcp_id:<id>` tag.
- Used for diff matching.

## 3. Table: `scene`

Purpose: one managed scene/level.

Fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `name` | string | yes | Display name. |
| `description` | string | no | Notes. |
| `status` | string | yes | `active`, `archived`, `testing`. |
| `active_revision` | int | yes | Current revision. |
| `unreal_project_path` | string | no | Optional project path. |
| `unreal_level_name` | string | no | Target Unreal level. |
| `created_at` | datetime | yes | Creation time. |
| `updated_at` | datetime | yes | Update time. |

## 4. Table: `scene_group`

Purpose: procedural intent.

Examples:

- castle
- wall
- pyramid
- bridge
- mansion
- room
- city block

Fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `scene` | record<scene> | yes | Parent scene. |
| `kind` | string | yes | Group type. |
| `tool_name` | string | no | Generator name. |
| `name` | string | yes | Display name. |
| `params` | object | no | Generator params. |
| `seed` | string | no | Deterministic seed. |
| `revision` | int | yes | Group revision. |
| `deleted` | bool | yes | Tombstone. |

## 5. Table: `scene_object`

Purpose: one desired Unreal actor/object.

Fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `scene` | record<scene> | yes | Parent scene. |
| `group` | record<scene_group> | no | Optional group. |
| `mcp_id` | string | yes | Stable logical identity. |
| `desired_name` | string | yes | Preferred Unreal actor name. |
| `unreal_actor_name` | string | no | Last known actual name. |
| `actor_type` | string | yes | `StaticMeshActor`, `BlueprintActor`. |
| `asset_ref` | object | no | Mesh or blueprint. |
| `transform` | object | yes | Location/rotation/scale. |
| `visual` | object | no | Material/color/visibility. |
| `physics` | object | no | Desired physics config. |
| `tags` | array<string> | yes | Desired tags. |
| `metadata` | object | no | Extra data. |
| `desired_hash` | string | yes | Hash of sync-relevant fields. |
| `last_applied_hash` | string | no | Last successfully applied hash. |
| `sync_status` | string | yes | `pending`, `synced`, `error`, `ignored`. |
| `deleted` | bool | yes | Tombstone. |
| `revision` | int | yes | Object revision. |

## 6. Object shapes

### Transform

```json
{
  "location": { "x": 0.0, "y": 0.0, "z": 0.0 },
  "rotation": { "pitch": 0.0, "yaw": 0.0, "roll": 0.0 },
  "scale": { "x": 1.0, "y": 1.0, "z": 1.0 }
}
```

### Asset reference

```json
{
  "kind": "static_mesh",
  "path": "/Engine/BasicShapes/Cube.Cube",
  "fallback": "/Engine/BasicShapes/Cube.Cube"
}
```

### Visual

```json
{
  "material_path": null,
  "color": { "r": 1.0, "g": 0.2, "b": 0.1, "a": 1.0 },
  "visible": true
}
```

### Physics

```json
{
  "simulate_physics": false,
  "mass": null
}
```

Important: physics observation should not automatically overwrite desired state. Otherwise the DB and physics simulation fight each other like two interns with admin rights.

## 7. Table: `scene_snapshot`

Purpose: point-in-time copy of desired state.

Fields:

| Field | Type | Required |
|---|---|---:|
| `scene` | record<scene> | yes |
| `name` | string | yes |
| `description` | string | no |
| `revision` | int | yes |
| `groups` | array<object> | yes |
| `objects` | array<object> | yes |
| `created_at` | datetime | yes |

## 8. Table: `sync_run`

Purpose: one planning/apply run.

Fields:

| Field | Type | Required |
|---|---|---:|
| `scene` | record<scene> | yes |
| `mode` | string | yes |
| `status` | string | yes |
| `summary` | object | yes |
| `started_at` | datetime | yes |
| `ended_at` | datetime | no |
| `error` | string | no |

## 9. Table: `scene_operation`

Purpose: one planned/applied operation.

Fields:

| Field | Type | Required |
|---|---|---:|
| `scene` | record<scene> | yes |
| `sync_run` | record<sync_run> | yes |
| `object` | record<scene_object> | no |
| `mcp_id` | string | no |
| `action` | string | yes |
| `reason` | string | yes |
| `desired` | object | no |
| `actual` | object | no |
| `status` | string | yes |
| `attempts` | int | yes |
| `error` | string | no |

## 10. Table: `actor_observation`

Purpose: store actual Unreal actor snapshots for debugging.

Fields:

| Field | Type | Required |
|---|---|---:|
| `scene` | record<scene> | yes |
| `sync_run` | record<sync_run> | no |
| `mcp_id` | string | no |
| `unreal_actor_name` | string | yes |
| `class_name` | string | yes |
| `transform` | object | yes |
| `tags` | array<string> | yes |
| `raw` | object | no |
| `observed_at` | datetime | yes |

## 11. Draft SurrealQL schema

Exact syntax should be checked against the pinned SurrealDB version.

```sql
DEFINE TABLE scene SCHEMAFULL;
DEFINE FIELD name ON TABLE scene TYPE string;
DEFINE FIELD description ON TABLE scene TYPE option<string>;
DEFINE FIELD status ON TABLE scene TYPE string DEFAULT "active";
DEFINE FIELD active_revision ON TABLE scene TYPE int DEFAULT 1;
DEFINE FIELD unreal_project_path ON TABLE scene TYPE option<string>;
DEFINE FIELD unreal_level_name ON TABLE scene TYPE option<string>;
DEFINE FIELD created_at ON TABLE scene TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE scene TYPE datetime DEFAULT time::now();

DEFINE TABLE scene_group SCHEMAFULL;
DEFINE FIELD scene ON TABLE scene_group TYPE record<scene>;
DEFINE FIELD kind ON TABLE scene_group TYPE string;
DEFINE FIELD tool_name ON TABLE scene_group TYPE option<string>;
DEFINE FIELD name ON TABLE scene_group TYPE string;
DEFINE FIELD params ON TABLE scene_group TYPE object DEFAULT {};
DEFINE FIELD seed ON TABLE scene_group TYPE option<string>;
DEFINE FIELD revision ON TABLE scene_group TYPE int DEFAULT 1;
DEFINE FIELD deleted ON TABLE scene_group TYPE bool DEFAULT false;
DEFINE FIELD created_at ON TABLE scene_group TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE scene_group TYPE datetime DEFAULT time::now();

DEFINE TABLE scene_object SCHEMAFULL;
DEFINE FIELD scene ON TABLE scene_object TYPE record<scene>;
DEFINE FIELD group ON TABLE scene_object TYPE option<record<scene_group>>;
DEFINE FIELD mcp_id ON TABLE scene_object TYPE string;
DEFINE FIELD desired_name ON TABLE scene_object TYPE string;
DEFINE FIELD unreal_actor_name ON TABLE scene_object TYPE option<string>;
DEFINE FIELD actor_type ON TABLE scene_object TYPE string;
DEFINE FIELD asset_ref ON TABLE scene_object TYPE object DEFAULT {};
DEFINE FIELD transform ON TABLE scene_object TYPE object;
DEFINE FIELD visual ON TABLE scene_object TYPE object DEFAULT {};
DEFINE FIELD physics ON TABLE scene_object TYPE object DEFAULT {};
DEFINE FIELD tags ON TABLE scene_object TYPE array<string> DEFAULT [];
DEFINE FIELD metadata ON TABLE scene_object TYPE object DEFAULT {};
DEFINE FIELD desired_hash ON TABLE scene_object TYPE string;
DEFINE FIELD last_applied_hash ON TABLE scene_object TYPE option<string>;
DEFINE FIELD sync_status ON TABLE scene_object TYPE string DEFAULT "pending";
DEFINE FIELD deleted ON TABLE scene_object TYPE bool DEFAULT false;
DEFINE FIELD revision ON TABLE scene_object TYPE int DEFAULT 1;
DEFINE FIELD created_at ON TABLE scene_object TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE scene_object TYPE datetime DEFAULT time::now();

DEFINE INDEX scene_object_scene_mcp_id ON TABLE scene_object COLUMNS scene, mcp_id UNIQUE;
DEFINE INDEX scene_object_scene_group ON TABLE scene_object COLUMNS scene, group;
DEFINE INDEX scene_object_sync_status ON TABLE scene_object COLUMNS scene, sync_status;
```

## 12. Optional graph relations

Use these later, not in the first MVP if they slow implementation.

```sql
DEFINE TABLE contains TYPE RELATION FROM scene TO scene_group;
DEFINE TABLE owns TYPE RELATION FROM scene_group TO scene_object;
DEFINE TABLE depends_on TYPE RELATION FROM scene_object TO scene_object;
```

Example:

```sql
RELATE scene:main->contains->scene_group:castle_001;
RELATE scene_group:castle_001->owns->scene_object:castle_001_wall_north_0001;
```

## 13. Desired hash policy

Include:

- actor type
- asset ref
- transform
- visual fields supported by sync
- physics fields supported by sync
- sorted tags
- sync-relevant metadata

Exclude:

- timestamps
- `sync_status`
- `last_applied_hash`
- `unreal_actor_name`
- revision if it does not change UE

## 14. Sync status lifecycle

```text
pending -> synced
pending -> error
error -> pending
synced -> pending when desired_hash changes
synced -> pending when deleted=true
```

Never set `synced` unless the Unreal operation actually succeeded.
