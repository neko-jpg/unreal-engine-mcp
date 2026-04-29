<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 07. MCP Tool API Specification

## 1. Purpose

Expose scene database operations through the existing Python MCP server. The Python layer should call Rust `scene-syncd`; it should not implement SurrealDB or sync logic.

## 2. Response format

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "error": null
}
```

Error:

```json
{
  "success": false,
  "data": null,
  "warnings": [],
  "error": {
    "code": "scene_syncd_unavailable",
    "message": "Could not reach scene-syncd at http://127.0.0.1:8787"
  }
}
```

## 3. Python facade helper

```python
# Python/server/scene_client.py
import os
import requests

SCENE_SYNCD_URL = os.getenv("SCENE_SYNCD_URL", "http://127.0.0.1:8787")

def call_scene_syncd(path: str, payload: dict) -> dict:
    response = requests.post(f"{SCENE_SYNCD_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
```

## 4. Tools

### `scene_create`

Creates or updates a scene.

Input:

```json
{
  "scene_id": "main",
  "name": "Main Scene",
  "description": "Default managed scene",
  "unreal_level_name": "ExampleMap"
}
```

### `scene_upsert_actor`

Writes desired actor state. Does not touch Unreal.

Input:

```json
{
  "scene_id": "main",
  "mcp_id": "cube_001",
  "desired_name": "Cube_001",
  "actor_type": "StaticMeshActor",
  "asset_ref": {
    "kind": "static_mesh",
    "path": "/Engine/BasicShapes/Cube.Cube"
  },
  "transform": {
    "location": { "x": 0, "y": 0, "z": 100 },
    "rotation": { "pitch": 0, "yaw": 0, "roll": 0 },
    "scale": { "x": 1, "y": 1, "z": 1 }
  },
  "tags": ["managed_by_mcp"]
}
```

Output includes:

- `object_id`
- `mcp_id`
- `desired_hash`
- `sync_status`

### `scene_upsert_actors`

Bulk upsert.

Input:

```json
{
  "scene_id": "main",
  "group_id": "wall_001",
  "objects": []
}
```

### `scene_create_layout`

Creates or updates a Semantic Layout Graph. `nodes` are written as
`scene_entity` records and `edges` are written as `scene_relation` records.
This does not touch Unreal.

Input:

```json
{
  "scene_id": "castle_001",
  "theme": "medieval_european_castle",
  "nodes": [
    {
      "entity_id": "tower_west",
      "kind": "tower",
      "name": "West Tower",
      "properties": {
        "location": { "x": -500, "y": 0, "z": 0 },
        "height": 900,
        "width": 300,
        "depth": 300
      }
    },
    {
      "entity_id": "wall_north",
      "kind": "curtain_wall",
      "name": "North Wall",
      "properties": {
        "height": 500,
        "thickness": 80,
        "segments": 8,
        "crenellations": { "enabled": true, "count": 16 }
      }
    }
  ],
  "edges": [
    {
      "relation_id": "wall_north_to_west",
      "source_entity_id": "wall_north",
      "target_entity_id": "tower_west",
      "relation_type": "connected_by",
      "properties": { "order": 0 }
    }
  ]
}
```

Layout denormalization currently supports:

- `from` / `to` spans on `curtain_wall` and `bridge`
- `connected_by`, `connects`, `spans`, `spans_between`, and `attached_to`
  relations from a span entity to endpoint entities
- `segments` or `segment_length` expansion for walls and bridges
- optional wall `crenellations` expansion into generated detail objects

Generated `scene_object` records keep semantic tags such as
`layout_kind:curtain_wall` and `layout_entity:wall_north`.

### `scene_preview_layout`

Returns denormalized objects without persisting them. Use this before approval
or to drive draft visualization.

Input:

```json
{ "scene_id": "castle_001" }
```

### `scene_show_draft_proxy`

Previews the layout in Unreal as HISM draft proxies. By default it creates one
proxy per semantic kind so reviewers can distinguish and manage walls, towers,
keeps, bridges, and generated detail independently.

Input:

```json
{
  "scene_id": "castle_001",
  "proxy_name": "draft_layout",
  "mesh_path": "/Engine/BasicShapes/Cube.Cube",
  "group_by_kind": true,
  "use_dither": true
}
```

The tool uses `/layouts/{scene_id}/preview`, then sends `create_draft_proxy`
or `update_draft_proxy` to Unreal. It does not persist `scene_object` records.

### `scene_generate_layout_objects`

Persists denormalized layout objects into `scene_object` records. After this
tool succeeds, `scene_plan_sync` and `scene_sync` can materialize the blockout
through the existing sync pipeline.

Input:

```json
{ "scene_id": "castle_001" }
```

### `scene_delete_actor`

Tombstone an actor.

Input:

```json
{
  "scene_id": "main",
  "mcp_id": "cube_001"
}
```

Important: does not delete Unreal until `scene_sync`.

### `scene_list_objects`

Input:

```json
{
  "scene_id": "main",
  "group_id": null,
  "include_deleted": false,
  "limit": 100
}
```

### `scene_plan_sync`

Input:

```json
{
  "scene_id": "main",
  "mode": "plan_only",
  "orphan_policy": "conflict"
}
```

Output:

```json
{
  "summary": {
    "create": 1,
    "update_transform": 0,
    "delete": 0,
    "noop": 0,
    "conflict": 0
  },
  "operations": []
}
```

### `scene_sync`

Input:

```json
{
  "scene_id": "main",
  "mode": "apply_safe",
  "allow_delete": false,
  "max_operations": 500
}
```

Modes:

- `apply_safe`: creates/updates only.
- `apply_all`: creates/updates/deletes.
- `plan_only`: alias for plan endpoint.

### `scene_snapshot_create`

Input:

```json
{
  "scene_id": "main",
  "name": "Before castle resize",
  "description": "Safe point before geometry changes"
}
```

### `scene_snapshot_restore`

Input:

```json
{
  "snapshot_id": "scene_snapshot:main_20260425_001",
  "restore_mode": "replace_desired"
}
```

Important: restore changes DB only. Run `scene_sync` after review.

### `scene_import_from_unreal`

Input:

```json
{
  "scene_id": "main",
  "managed_only": false,
  "attach_mcp_ids": true,
  "name_prefix": "Imported"
}
```

### `scene_create_wall`

Writes wall segments to DB.

Input:

```json
{
  "scene_id": "main",
  "group_id": "wall_001",
  "start": { "x": 0, "y": 0, "z": 0 },
  "length": 1000,
  "height": 300,
  "thickness": 50,
  "segments": 10,
  "axis": "x"
}
```

### `scene_create_pyramid`

Writes pyramid blocks to DB.

Input:

```json
{
  "scene_id": "main",
  "group_id": "pyramid_001",
  "base_location": { "x": 0, "y": 0, "z": 0 },
  "levels": 5,
  "block_size": 100
}
```

## 5. Tool safety

| Tool | DB write | Unreal mutation | Default safety |
|---|---:|---:|---|
| `scene_upsert_actor` | yes | no | safe |
| `scene_delete_actor` | yes | no | tombstone only |
| `scene_plan_sync` | optional log | no | safe |
| `scene_sync` | yes | yes | explicit |
| `scene_snapshot_restore` | yes | no | review before sync |
| `scene_import_from_unreal` | yes | optional repair | cautious |

## 6. Tool registration skeleton

```python
from typing import Any, Dict
from server.core import mcp
from server.scene_client import call_scene_syncd

@mcp.tool()
def scene_plan_sync(scene_id: str = "main", mode: str = "plan_only") -> Dict[str, Any]:
    return call_scene_syncd("/sync/plan", {"scene_id": scene_id, "mode": mode})

@mcp.tool()
def scene_sync(scene_id: str = "main", mode: str = "apply_safe", allow_delete: bool = False) -> Dict[str, Any]:
    return call_scene_syncd("/sync/apply", {
        "scene_id": scene_id,
        "mode": mode,
        "allow_delete": allow_delete,
    })
```

## 7. Migration rule

Do not silently change old tools.

Use:

```text
create_wall         -> immediate Unreal path
scene_create_wall   -> SurrealDB desired-state path
```

This avoids breaking existing workflows and tests.
