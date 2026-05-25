use crate::api::common::{error_response, normalize_scene_id_input, success_response, AppState};
use axum::extract::State;
use axum::routing::{get, post};
use axum::Json;
use axum::Router;
use serde::Deserialize;
use serde_json::{json, Value};
use surrealdb::sql::Datetime;

use crate::db::SurrealSceneRepository;
use crate::domain::ids::validate_mcp_id;
use crate::domain::transform::compute_desired_hash;
use crate::domain::*;
use crate::error::AppError;

pub async fn health() -> Json<Value> {
    Json(json!({
        "success": true,
        "data": { "status": "ok" },
        "warnings": [],
        "error": null
    }))
}

#[derive(Debug, Deserialize)]
pub struct CreateSceneRequest {
    pub scene_id: String,
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
}

pub async fn create_scene(
    State(state): State<AppState>,
    Json(req): Json<CreateSceneRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let display_name = req.name.unwrap_or_else(|| scene_id.clone());
    let scene = repo
        .upsert_scene(&scene_id, &display_name, req.description)
        .await?;
    Ok(Json(success_response(
        serde_json::to_value(scene)
            .map_err(|e| AppError::Internal(format!("serialize scene error: {e}")))?,
    )))
}

#[derive(Debug, Deserialize)]
pub struct ListScenesRequest {}

pub async fn list_scenes(
    State(state): State<AppState>,
    Json(_req): Json<ListScenesRequest>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());
    let scenes = repo.list_scenes().await?;
    Ok(Json(success_response(json!({ "scenes": scenes }))))
}

#[derive(Debug, Deserialize)]
pub struct UpsertObjectRequest {
    #[serde(default)]
    pub scene_id: String,
    pub mcp_id: String,
    #[serde(default)]
    pub desired_name: Option<String>,
    #[serde(default = "default_actor_type")]
    pub actor_type: String,
    #[serde(default)]
    pub asset_ref: Option<serde_json::Value>,
    #[serde(default)]
    pub transform: Option<serde_json::Value>,
    #[serde(default)]
    pub visual: Option<serde_json::Value>,
    #[serde(default)]
    pub physics: Option<serde_json::Value>,
    #[serde(default)]
    pub tags: Option<Vec<String>>,
    #[serde(default)]
    pub metadata: Option<serde_json::Value>,
    #[serde(default)]
    pub group_id: Option<String>,
}

fn default_actor_type() -> String {
    "StaticMeshActor".to_string()
}

fn object_or_empty(v: Option<serde_json::Value>) -> serde_json::Value {
    match v {
        Some(serde_json::Value::Null) | None => json!({}),
        Some(value) => value,
    }
}

fn parse_transform(v: Option<serde_json::Value>) -> Transform {
    match v {
        Some(t) => {
            let loc = t.get("location");
            let rot = t.get("rotation");
            let scl = t.get("scale");
            Transform {
                location: Vec3 {
                    x: loc
                        .and_then(|l| l.get("x"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    y: loc
                        .and_then(|l| l.get("y"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    z: loc
                        .and_then(|l| l.get("z"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                },
                rotation: Rotator {
                    pitch: rot
                        .and_then(|r| r.get("pitch"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    yaw: rot
                        .and_then(|r| r.get("yaw"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    roll: rot
                        .and_then(|r| r.get("roll"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                },
                scale: Vec3 {
                    x: scl
                        .and_then(|s| s.get("x"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(1.0),
                    y: scl
                        .and_then(|s| s.get("y"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(1.0),
                    z: scl
                        .and_then(|s| s.get("z"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(1.0),
                },
            }
        }
        None => Transform::default(),
    }
}

pub async fn upsert_object(
    State(state): State<AppState>,
    Json(req): Json<UpsertObjectRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    if let Err(e) = validate_mcp_id(&req.mcp_id) {
        return Err(AppError::Validation(e));
    }

    let transform = parse_transform(req.transform);
    let desired_name = req.desired_name.unwrap_or_else(|| req.mcp_id.clone());

    let mut obj = SceneObject {
        id: format!("scene_object:{}:{}", scene_id, req.mcp_id),
        scene: format!("scene:{}", scene_id),
        group: req.group_id.map(|g| format!("scene_group:{g}")),
        mcp_id: req.mcp_id.clone(),
        desired_name,
        unreal_actor_name: None,
        actor_type: req.actor_type,
        asset_ref: object_or_empty(req.asset_ref),
        transform,
        visual: object_or_empty(req.visual),
        physics: object_or_empty(req.physics),
        tags: req.tags.unwrap_or_default(),
        metadata: object_or_empty(req.metadata),
        desired_hash: String::new(),
        last_applied_hash: None,
        sync_status: "pending".to_string(),
        deleted: false,
        revision: 1,
        created_at: Datetime::from(chrono::Utc::now()),
        updated_at: Datetime::from(chrono::Utc::now()),
    };

    obj.desired_hash = compute_desired_hash(&obj).map_err(AppError::Internal)?;

    let repo = SurrealSceneRepository::new(state.db.clone());
    let saved = repo.upsert_object(&obj).await?;

    Ok(Json(success_response(
        serde_json::to_value(saved)
            .map_err(|e| AppError::Internal(format!("serialize object error: {e}")))?,
    )))
}

#[derive(Debug, Deserialize)]
pub struct ListObjectsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub include_deleted: bool,
    #[serde(default)]
    pub group_id: Option<String>,
    #[serde(default)]
    pub limit: Option<usize>,
}

pub async fn list_objects(
    State(state): State<AppState>,
    Json(req): Json<ListObjectsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let objects = repo
        .list_desired_objects(
            &scene_id,
            req.include_deleted,
            req.group_id.as_deref(),
            req.limit,
        )
        .await?;
    Ok(Json(success_response(json!({ "objects": objects }))))
}

#[derive(Debug, Deserialize)]
pub struct DeleteObjectRequest {
    pub scene_id: String,
    pub mcp_id: String,
}

pub async fn delete_object(
    State(state): State<AppState>,
    Json(req): Json<DeleteObjectRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    repo.mark_object_deleted(&scene_id, &req.mcp_id).await?;
    Ok(Json(success_response(
        json!({ "tombstoned": true, "mcp_id": req.mcp_id }),
    )))
}

#[derive(Debug, Deserialize)]
pub struct CreateGroupRequest {
    pub scene_id: String,
    pub kind: String,
    pub name: String,
    #[serde(default)]
    pub tool_name: Option<String>,
    #[serde(default)]
    pub params: serde_json::Value,
    #[serde(default)]
    pub seed: Option<String>,
}

pub async fn create_group(
    State(state): State<AppState>,
    Json(req): Json<CreateGroupRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let group = repo
        .create_group(
            &scene_id,
            &req.kind,
            &req.name,
            req.tool_name,
            req.params,
            req.seed,
        )
        .await?;
    Ok(Json(success_response(json!({ "group": group }))))
}

#[derive(Debug, Deserialize)]
pub struct ListGroupsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub include_deleted: bool,
}

pub async fn list_groups(
    State(state): State<AppState>,
    Json(req): Json<ListGroupsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let groups = repo.list_groups(&scene_id, req.include_deleted).await?;
    Ok(Json(success_response(json!({
        "groups": groups,
        "count": groups.len(),
    }))))
}

#[derive(Debug, Deserialize)]
pub struct CreateGeneratorRunRequest {
    pub scene_id: String,
    pub kind: String,
    pub tool_name: String,
    pub name: String,
    #[serde(default)]
    pub params: serde_json::Value,
    #[serde(default)]
    pub seed: Option<String>,
    #[serde(default)]
    pub group_id: Option<String>,
    #[serde(default)]
    pub generated_count: i64,
}

pub async fn create_generator_run(
    State(state): State<AppState>,
    Json(req): Json<CreateGeneratorRunRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let run = repo
        .create_generator_run(
            &scene_id,
            &req.kind,
            &req.tool_name,
            &req.name,
            req.params,
            req.seed,
            req.group_id,
            req.generated_count,
        )
        .await?;
    Ok(Json(success_response(json!({ "generator_run": run }))))
}

pub async fn get_generator_run(
    State(state): State<AppState>,
    axum::extract::Path(run_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());
    let run = repo.get_generator_run(&run_id).await?;
    match run {
        Some(r) => Ok(Json(success_response(json!({ "generator_run": r })))),
        None => Err(AppError::NotFound(format!(
            "generator_run {run_id} not found"
        ))),
    }
}

#[derive(Debug, Deserialize)]
pub struct CreateSnapshotRequest {
    pub scene_id: String,
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
}

pub async fn create_snapshot(
    State(state): State<AppState>,
    Json(req): Json<CreateSnapshotRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let snapshot = repo
        .create_snapshot(&scene_id, &req.name, req.description)
        .await?;
    let snapshot_id = snapshot.id.clone();
    let object_count = snapshot.objects.len();
    Ok(Json(success_response(json!({
        "snapshot": snapshot,
        "snapshot_id": snapshot_id,
        "object_count": object_count,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct ListSnapshotsRequest {
    pub scene_id: String,
}

pub async fn list_snapshots(
    State(state): State<AppState>,
    Json(req): Json<ListSnapshotsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let snapshots = repo.list_snapshots(&scene_id).await?;
    Ok(Json(success_response(json!({
        "snapshots": snapshots,
        "count": snapshots.len(),
    }))))
}

#[derive(Debug, Deserialize)]
pub struct RestoreSnapshotRequest {
    pub snapshot_id: String,
    #[serde(default = "default_restore_mode")]
    pub restore_mode: String,
}

fn default_restore_mode() -> String {
    "replace_desired".to_string()
}

pub async fn restore_snapshot(
    State(state): State<AppState>,
    Json(req): Json<RestoreSnapshotRequest>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());
    let summary = repo
        .restore_snapshot(&req.snapshot_id, &req.restore_mode)
        .await?;
    Ok(Json(success_response(summary)))
}

#[derive(Debug, Deserialize)]
pub struct RestoreSnapshotByNameRequest {
    pub scene_id: String,
    pub name: String,
    #[serde(default = "default_restore_mode")]
    pub restore_mode: String,
}

pub async fn restore_snapshot_by_name(
    State(state): State<AppState>,
    Json(req): Json<RestoreSnapshotByNameRequest>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());
    let (chosen, sorted) = repo
        .find_snapshot_by_name(&req.scene_id, &req.name)
        .await?
        .ok_or_else(|| {
            AppError::NotFound(format!(
                "snapshot named '{}' not found in scene '{}'",
                req.name, req.scene_id
            ))
        })?;
    let candidates: Vec<String> = sorted.iter().map(|s| s.id.clone()).collect();
    let warnings: Vec<String> = if sorted.len() > 1 {
        vec![format!(
            "multiple snapshots match name '{}' ({}); restored latest by created_at",
            req.name,
            sorted.len()
        )]
    } else {
        Vec::new()
    };
    let summary = repo.restore_snapshot(&chosen.id, &req.restore_mode).await?;
    Ok(Json(json!({
        "success": true,
        "data": {
            "snapshot_id": chosen.id,
            "name": chosen.name,
            "restore": summary,
            "candidates": candidates,
        },
        "warnings": warnings,
    })))
}

#[derive(Debug, Deserialize)]
pub struct BulkUpsertRequest {
    pub scene_id: String,
    #[serde(default)]
    pub group_id: Option<String>,
    pub objects: Vec<UpsertObjectRequest>,
}

const MAX_BATCH_SIZE: usize = 500;

pub async fn bulk_upsert_objects(
    State(state): State<AppState>,
    Json(req): Json<BulkUpsertRequest>,
) -> Result<Json<Value>, AppError> {
    if req.objects.len() > MAX_BATCH_SIZE {
        return Err(AppError::Validation(format!(
            "bulk upsert exceeded maximum batch size of {MAX_BATCH_SIZE}; received {} objects",
            req.objects.len()
        )));
    }

    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let mut created = Vec::new();
    let mut errors = Vec::new();

    for (i, obj_req) in req.objects.into_iter().enumerate() {
        if let Err(e) = validate_mcp_id(&obj_req.mcp_id) {
            errors.push(json!({
                "index": i,
                "mcp_id": null,
                "error": e
            }));
            continue;
        }

        let transform = parse_transform(obj_req.transform);
        let desired_name = obj_req
            .desired_name
            .unwrap_or_else(|| obj_req.mcp_id.clone());

        let mut obj = SceneObject {
            id: format!("scene_object:{}:{}", scene_id, obj_req.mcp_id),
            scene: format!("scene:{}", scene_id),
            group: obj_req
                .group_id
                .clone()
                .or_else(|| req.group_id.clone())
                .map(|g| format!("scene_group:{g}")),
            mcp_id: obj_req.mcp_id.clone(),
            desired_name,
            unreal_actor_name: None,
            actor_type: obj_req.actor_type,
            asset_ref: object_or_empty(obj_req.asset_ref),
            transform,
            visual: object_or_empty(obj_req.visual),
            physics: object_or_empty(obj_req.physics),
            tags: obj_req.tags.unwrap_or_default(),
            metadata: object_or_empty(obj_req.metadata),
            desired_hash: String::new(),
            last_applied_hash: None,
            sync_status: "pending".to_string(),
            deleted: false,
            revision: 1,
            created_at: Datetime::from(chrono::Utc::now()),
            updated_at: Datetime::from(chrono::Utc::now()),
        };

        match compute_desired_hash(&obj) {
            Ok(hash) => obj.desired_hash = hash,
            Err(e) => {
                errors.push(json!({
                    "index": i,
                    "mcp_id": obj_req.mcp_id,
                    "error": e
                }));
                continue;
            }
        }

        match repo.upsert_object(&obj).await {
            Ok(saved) => created.push(serde_json::to_value(saved).unwrap_or_default()),
            Err(e) => {
                errors.push(json!({
                    "index": i,
                    "mcp_id": obj_req.mcp_id,
                    "error": e.to_string()
                }));
            }
        }
    }

    let response_body = json!({
        "upserted_count": created.len(),
        "error_count": errors.len(),
        "objects": created,
        "errors": errors,
    });

    if errors.is_empty() {
        Ok(Json(success_response(response_body)))
    } else if created.is_empty() {
        Ok(Json(error_response(
            "BULK_UPSERT_FAILED",
            "All bulk upsert operations failed",
        )))
    } else {
        let mut body = response_body;
        body["success"] = json!(false);
        body["partial_success"] = json!(true);
        Ok(Json(body))
    }
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/scenes/create", post(create_scene))
        .route("/scenes/list", post(list_scenes))
        .route("/objects/upsert", post(upsert_object))
        .route("/objects/bulk-upsert", post(bulk_upsert_objects))
        .route("/objects/list", post(list_objects))
        .route("/objects/delete", post(delete_object))
        .route("/groups/create", post(create_group))
        .route("/groups/list", post(list_groups))
        .route("/generator-runs/create", post(create_generator_run))
        .route("/generator-runs/{run_id}", get(get_generator_run))
        .route("/snapshots/create", post(create_snapshot))
        .route("/snapshots/list", post(list_snapshots))
        .route("/snapshots/restore", post(restore_snapshot))
        .route("/snapshots/restore_by_name", post(restore_snapshot_by_name))
}

#[cfg(test)]
mod tests {
    use super::object_or_empty;
    use serde_json::json;

    #[test]
    fn object_or_empty_converts_missing_or_null_to_object() {
        assert_eq!(object_or_empty(None), json!({}));
        assert_eq!(object_or_empty(Some(serde_json::Value::Null)), json!({}));
    }

    #[test]
    fn object_or_empty_preserves_explicit_object() {
        assert_eq!(
            object_or_empty(Some(json!({ "path": "/Engine/BasicShapes/Cube.Cube" }))),
            json!({
                "path": "/Engine/BasicShapes/Cube.Cube"
            })
        );
    }
}
