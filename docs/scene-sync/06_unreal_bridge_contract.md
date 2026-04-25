<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 06. Unreal Bridge Contract

## 1. Purpose

The Unreal bridge must expose stable identity and actual state so Rust can sync safely.

The minimum bridge upgrade is:

1. `spawn_actor` accepts `mcp_id`.
2. Spawned actor receives `mcp_id:<id>` tag.
3. Actor listing returns tags.
4. Rust can find actors by `mcp_id`.

## 2. Required actor tags

Every managed actor must have:

```text
managed_by_mcp
mcp_id:<mcp_id>
```

Optional:

```text
scene:<scene_key>
group:<group_key>
kind:<object_kind>
```

Example:

```text
managed_by_mcp
mcp_id:castle_001:wall:north:0001
scene:main
group:castle_001
kind:wall_segment
```

## 3. `spawn_actor` request

```json
{
  "command": "spawn_actor",
  "params": {
    "name": "Castle_Wall_North_0001",
    "type": "StaticMeshActor",
    "mcp_id": "castle_001:wall:north:0001",
    "location": [0.0, 0.0, 0.0],
    "rotation": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
    "static_mesh": "/Engine/BasicShapes/Cube.Cube",
    "tags": ["managed_by_mcp", "castle_001"]
  }
}
```

## 4. `spawn_actor` response

```json
{
  "success": true,
  "actor": {
    "name": "Castle_Wall_North_0001",
    "class": "StaticMeshActor",
    "location": [0.0, 0.0, 0.0],
    "rotation": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
    "tags": [
      "managed_by_mcp",
      "mcp_id:castle_001:wall:north:0001",
      "castle_001"
    ]
  }
}
```

## 5. Actor listing response

`get_actors_in_level` must include tags.

```json
{
  "success": true,
  "actors": [
    {
      "name": "Wall_001",
      "class": "StaticMeshActor",
      "location": [0, 0, 0],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1],
      "tags": ["managed_by_mcp", "mcp_id:wall_001"],
      "static_mesh": "/Engine/BasicShapes/Cube.Cube"
    }
  ]
}
```

## 6. New commands

### `find_actor_by_mcp_id`

Request:

```json
{
  "command": "find_actor_by_mcp_id",
  "params": {
    "mcp_id": "wall_001"
  }
}
```

### `set_actor_transform_by_mcp_id`

Request:

```json
{
  "command": "set_actor_transform_by_mcp_id",
  "params": {
    "mcp_id": "wall_001",
    "location": [100, 0, 0],
    "rotation": [0, 0, 0],
    "scale": [1, 1, 1]
  }
}
```

### `delete_actor_by_mcp_id`

Request:

```json
{
  "command": "delete_actor_by_mcp_id",
  "params": {
    "mcp_id": "wall_001"
  }
}
```

If actor is already missing, return success with `deleted=false`. Idempotency matters more than theatrical error messages.

## 7. Future batch command: `apply_scene_delta`

Request:

```json
{
  "command": "apply_scene_delta",
  "params": {
    "scene_id": "scene:main",
    "dry_run": false,
    "creates": [],
    "updates": [],
    "deletes": []
  }
}
```

This is later. MVP can use one command per operation.

## 8. C++ pseudo-code: add tags on spawn

```cpp
if (!McpId.IsEmpty())
{
    NewActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
    NewActor->Tags.AddUnique(FName(*FString::Printf(TEXT("mcp_id:%s"), *McpId)));
}

for (const FString& Tag : Tags)
{
    NewActor->Tags.AddUnique(FName(*Tag));
}
```

## 9. C++ pseudo-code: return tags

```cpp
TArray<TSharedPtr<FJsonValue>> TagsArray;
for (const FName& Tag : Actor->Tags)
{
    TagsArray.Add(MakeShared<FJsonValueString>(Tag.ToString()));
}
JsonObject->SetArrayField(TEXT("tags"), TagsArray);
```

## 10. C++ pseudo-code: find by `mcp_id`

```cpp
AActor* FindActorByMcpId(UWorld* World, const FString& McpId)
{
    const FName TargetTag(*FString::Printf(TEXT("mcp_id:%s"), *McpId));
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->Tags.Contains(TargetTag))
        {
            return *It;
        }
    }
    return nullptr;
}
```

## 11. Error codes

| Code | Meaning |
|---|---|
| `actor_not_found` | Actor not found. |
| `duplicate_mcp_id` | Multiple actors share one `mcp_id`. |
| `invalid_asset` | Mesh/blueprint path invalid. |
| `unsupported_actor_type` | Actor type unsupported. |
| `invalid_transform` | Transform invalid. |
| `unreal_world_missing` | No editor world available. |
| `command_parse_error` | Bad JSON command. |

## 12. Bridge checklist

- [ ] Spawn accepts `mcp_id`.
- [ ] Spawn accepts `tags`.
- [ ] Spawned actor has `managed_by_mcp`.
- [ ] Spawned actor has `mcp_id:<id>`.
- [ ] Actor listing returns tags.
- [ ] Add `find_actor_by_mcp_id`.
- [ ] Add `set_actor_transform_by_mcp_id`.
- [ ] Add `delete_actor_by_mcp_id`.
- [ ] Later add `apply_scene_delta`.
