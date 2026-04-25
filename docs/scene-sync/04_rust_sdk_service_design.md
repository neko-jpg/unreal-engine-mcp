<!--
Project: Unreal MCP Scene Database / Sync System
DB: SurrealDB
Core: Rust SDK
Created: 2026-04-25
Scope: Design documents for a SurrealDB-backed desired-state sync architecture integrated with the existing Python MCP + Unreal C++ bridge codebase.
-->
# 04. Rust SDK Service Design

## 1. Service name

```text
scene-syncd
```

## 2. Purpose

`scene-syncd` owns SurrealDB access and synchronization logic. Python MCP calls it. Unreal C++ bridge executes editor operations. Rust is the brain in the middle, because somebody has to be.

## 3. Responsibilities

- Load config.
- Connect to SurrealDB using Rust SDK.
- Apply/check schema migrations.
- Validate scene object payloads.
- Normalize transform data.
- Compute desired hashes.
- Upsert desired objects.
- Create snapshots and restore them.
- Read Unreal actual state.
- Plan sync.
- Apply sync.
- Store sync logs.
- Provide local HTTP JSON API.
- Later, watch live queries.

## 4. Non-responsibilities

- Do not render.
- Do not replace Unreal plugin.
- Do not own high-level creative decisions.
- Do not expose public network API in MVP.
- Do not autosync destructive changes by default.

## 5. Crate layout

```text
rust/scene-syncd/
  Cargo.toml
  src/
    main.rs
    config.rs
    error.rs
    api/
      mod.rs
      routes.rs
      dto.rs
      state.rs
    db/
      mod.rs
      surreal.rs
      migrations.rs
      repo.rs
    domain/
      mod.rs
      ids.rs
      transform.rs
      scene.rs
      scene_group.rs
      scene_object.rs
      snapshot.rs
      sync.rs
      unreal.rs
    sync/
      mod.rs
      planner.rs
      applier.rs
      hashing.rs
      ordering.rs
      retry.rs
    unreal/
      mod.rs
      client.rs
      protocol.rs
      mapper.rs
    watch/
      mod.rs
      live_query.rs
      debounce.rs
    telemetry/
      mod.rs
      logging.rs
```

## 6. Cargo dependencies

Draft:

```toml
[dependencies]
anyhow = "1"
axum = "0.8"
chrono = { version = "0.4", features = ["serde"] }
futures = "0.3"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sha2 = "0.10"
surrealdb = "2"
thiserror = "2"
tokio = { version = "1", features = ["macros", "rt-multi-thread", "net", "time"] }
tower-http = { version = "0.6", features = ["trace", "cors"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
uuid = { version = "1", features = ["v4", "serde"] }
```

If using embedded mode later, add exact SurrealDB features such as `kv-mem` or `kv-rocksdb` according to the pinned version.

## 7. Config

Environment variables:

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
SCENE_SYNCD_LOG=info
```

Rust struct:

```rust
#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub surreal_url: String,
    pub surreal_ns: String,
    pub surreal_db: String,
    pub surreal_user: String,
    pub surreal_pass: String,
    pub unreal_host: String,
    pub unreal_port: u16,
    pub autosync: bool,
}
```

## 8. SurrealDB connection example

```rust
use surrealdb::engine::any::{connect, Any};
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;

pub async fn connect_surreal(config: &Config) -> surrealdb::Result<Surreal<Any>> {
    let db = connect(&config.surreal_url).await?;
    db.signin(Root {
        username: config.surreal_user.clone(),
        password: config.surreal_pass.clone(),
    }).await?;
    db.use_ns(&config.surreal_ns).use_db(&config.surreal_db).await?;
    Ok(db)
}
```

Alternative direct WebSocket style can use `Surreal::new::<Ws>(...)` after version pinning.

## 9. HTTP API

Endpoints:

```text
GET  /health
POST /scenes/create
POST /objects/upsert
POST /objects/bulk-upsert
POST /objects/delete
POST /objects/list
POST /sync/plan
POST /sync/apply
POST /snapshots/create
POST /snapshots/restore
POST /unreal/import
```

## 10. API response convention

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
    "code": "validation_error",
    "message": "mcp_id is required"
  }
}
```

## 11. Domain model sketch

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Vec3 { pub x: f64, pub y: f64, pub z: f64 }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Rotator { pub pitch: f64, pub yaw: f64, pub roll: f64 }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Transform {
    pub location: Vec3,
    pub rotation: Rotator,
    pub scale: Vec3,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneObject {
    pub scene: String,
    pub group: Option<String>,
    pub mcp_id: String,
    pub desired_name: String,
    pub unreal_actor_name: Option<String>,
    pub actor_type: String,
    pub asset_ref: serde_json::Value,
    pub transform: Transform,
    pub visual: serde_json::Value,
    pub physics: serde_json::Value,
    pub tags: Vec<String>,
    pub metadata: serde_json::Value,
    pub desired_hash: String,
    pub last_applied_hash: Option<String>,
    pub sync_status: String,
    pub deleted: bool,
    pub revision: i64,
}
```

## 12. Repository trait

```rust
#[async_trait::async_trait]
pub trait SceneRepository {
    async fn ensure_schema(&self) -> Result<()>;
    async fn create_scene(&self, req: CreateSceneRequest) -> Result<Scene>;
    async fn upsert_object(&self, obj: SceneObject) -> Result<SceneObject>;
    async fn mark_object_deleted(&self, scene: &str, mcp_id: &str) -> Result<()>;
    async fn list_desired_objects(&self, scene: &str) -> Result<Vec<SceneObject>>;
    async fn create_snapshot(&self, scene: &str, name: &str) -> Result<SceneSnapshot>;
    async fn restore_snapshot(&self, snapshot_id: &str) -> Result<RestoreSummary>;
    async fn create_sync_run(&self, req: CreateSyncRun) -> Result<SyncRun>;
    async fn record_operation(&self, op: PersistedOperation) -> Result<()>;
}
```

Use concrete `SurrealSceneRepository` first. Add mocks when tests need them. Do not worship abstraction for its own sake; that cult has enough members.

## 13. Unreal client

Rust client methods:

```rust
pub struct UnrealClient {
    host: String,
    port: u16,
}

impl UnrealClient {
    pub async fn get_actors_in_level(&self) -> Result<Vec<UnrealActorObservation>>;
    pub async fn spawn_actor(&self, req: SpawnActorRequest) -> Result<SpawnActorResponse>;
    pub async fn set_actor_transform(&self, req: SetActorTransformRequest) -> Result<()>;
    pub async fn delete_actor(&self, req: DeleteActorRequest) -> Result<()>;
}
```

MVP can call existing single-operation bridge commands. Later use batch `apply_scene_delta`.

## 14. Desired hash

```rust
pub fn desired_hash(obj: &SceneObject) -> Result<String> {
    let payload = DesiredHashPayload::from(obj);
    let bytes = serde_json::to_vec(&payload)?;
    let digest = sha2::Sha256::digest(&bytes);
    Ok(format!("{digest:x}"))
}
```

Hash excludes timestamps and sync status.

## 15. Startup sequence

1. Load config.
2. Initialize tracing.
3. Connect to SurrealDB.
4. Apply migrations.
5. Ensure `scene:main`.
6. Initialize Unreal client.
7. Start HTTP server.
8. If autosync enabled, start live watcher.

## 16. One-line dev commands

```bash
cd /home/arat2/Project-MUSE && mkdir -p rust && cargo new rust/scene-syncd --bin
```

```bash
cd /home/arat2/Project-MUSE/rust/scene-syncd && cargo add surrealdb tokio serde serde_json axum thiserror anyhow tracing tracing-subscriber sha2 uuid futures chrono
```

```bash
cd /home/arat2/Project-MUSE && mkdir -p .surreal && surreal start --user root --pass secret --bind 127.0.0.1:8000 rocksdb://.surreal/unreal_mcp.db
```

```bash
cd /home/arat2/Project-MUSE/rust/scene-syncd && SURREAL_URL=ws://127.0.0.1:8000 SURREAL_NS=unreal_mcp SURREAL_DB=scene SURREAL_USER=root SURREAL_PASS=secret cargo run
```
