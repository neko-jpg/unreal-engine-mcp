use axum::extract::State;
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};
use surrealdb::engine::any::Any;
use surrealdb::sql::Datetime;
use surrealdb::Surreal;

use crate::config::Config;
use crate::db::SurrealSceneRepository;
use crate::domain::ids::validate_mcp_id;
use crate::domain::transform::compute_desired_hash;
use crate::domain::*;
use crate::error::AppError;
use crate::sync::applier::apply_sync;
use crate::sync::planner::plan_sync;
use crate::unreal::client::UnrealClient;

#[derive(Debug, Clone)]
pub struct AppState {
    pub db: Surreal<Any>,
    pub config: Config,
}

fn success_response(data: Value) -> Value {
    json!({
        "success": true,
        "data": data,
        "warnings": [],
        "error": null
    })
}

fn error_response(code: &str, message: &str) -> Value {
    json!({
        "success": false,
        "data": null,
        "warnings": [],
        "error": {
            "code": code,
            "message": message
        }
    })
}

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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let display_name = req.name.unwrap_or_else(|| req.scene_id.clone());
    let scene = repo
        .upsert_scene(&req.scene_id, &display_name, req.description)
        .await?;
    Ok(Json(success_response(
        serde_json::to_value(scene).unwrap_or_default(),
    )))
}

#[derive(Debug, Deserialize)]
pub struct UpsertObjectRequest {
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
    if let Err(e) = validate_mcp_id(&req.mcp_id) {
        return Err(AppError::Validation(e));
    }

    let transform = parse_transform(req.transform);
    let desired_name = req.desired_name.unwrap_or_else(|| req.mcp_id.clone());

    let mut obj = SceneObject {
        id: format!("scene_object:{}:{}", req.scene_id, req.mcp_id),
        scene: format!("scene:{}", req.scene_id),
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
        metadata: json!({}),
        desired_hash: String::new(),
        last_applied_hash: None,
        sync_status: "pending".to_string(),
        deleted: false,
        revision: 1,
        created_at: Datetime::from(chrono::Utc::now()),
        updated_at: Datetime::from(chrono::Utc::now()),
    };

    obj.desired_hash = compute_desired_hash(&obj).map_err(|e| AppError::Internal(e))?;

    let repo = SurrealSceneRepository::new(state.db.clone());
    let saved = repo.upsert_object(&obj).await?;

    Ok(Json(success_response(
        serde_json::to_value(saved).unwrap_or_default(),
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let objects = repo
        .list_desired_objects(
            &req.scene_id,
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    repo.mark_object_deleted(&req.scene_id, &req.mcp_id).await?;
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let group = repo
        .create_group(&req.scene_id, &req.kind, &req.name, req.tool_name, req.params, req.seed)
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let groups = repo.list_groups(&req.scene_id, req.include_deleted).await?;
    Ok(Json(success_response(json!({
        "groups": groups,
        "count": groups.len(),
    }))))
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let snapshot = repo
        .create_snapshot(&req.scene_id, &req.name, req.description)
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
    let repo = SurrealSceneRepository::new(state.db.clone());
    let snapshots = repo.list_snapshots(&req.scene_id).await?;
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
pub struct BulkUpsertRequest {
    pub scene_id: String,
    #[serde(default)]
    pub group_id: Option<String>,
    pub objects: Vec<UpsertObjectRequest>,
}

pub async fn bulk_upsert_objects(
    State(state): State<AppState>,
    Json(req): Json<BulkUpsertRequest>,
) -> Result<Json<Value>, AppError> {
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
            id: format!("scene_object:{}:{}", req.scene_id, obj_req.mcp_id),
            scene: format!("scene:{}", req.scene_id),
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
            metadata: json!({}),
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

    Ok(Json(success_response(json!({
        "upserted_count": created.len(),
        "error_count": errors.len(),
        "objects": created,
        "errors": errors,
    }))))
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct PlanSyncRequest {
    pub scene_id: String,
    #[serde(default = "default_plan_mode")]
    pub mode: String,
    #[serde(default)]
    pub orphan_policy: Option<String>,
}

fn default_plan_mode() -> String {
    "plan_only".to_string()
}

pub async fn plan_sync_route(
    State(state): State<AppState>,
    Json(req): Json<PlanSyncRequest>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());

    let desired_objects = repo.list_desired_objects(&req.scene_id, true, None, None).await?;

    let unreal_client = UnrealClient::new(&state.config);
    let (actual_actors, plan_unreal_warning) = match unreal_client.get_actors_in_level().await {
        Ok(actors) => (actors, None),
        Err(e) => {
            let msg = format!(
                "Could not reach Unreal for plan_sync: {e}. Proceeding with empty actual state."
            );
            tracing::warn!("{}", msg);
            (Vec::new(), Some(msg))
        }
    };

    let plan = plan_sync(&req.scene_id, &desired_objects, &actual_actors);

    let mut warnings = plan.warnings.clone();
    if let Some(w) = plan_unreal_warning {
        warnings.push(w);
    }

    Ok(Json(success_response(json!({
        "scene_id": plan.scene_id,
        "summary": {
            "create": plan.summary.create,
            "update_transform": plan.summary.update_transform,
            "update_visual": plan.summary.update_visual,
            "delete": plan.summary.delete,
            "noop": plan.summary.noop,
            "conflict": plan.summary.conflict,
            "unsupported": plan.summary.unsupported,
        },
        "operations": plan.operations,
        "warnings": warnings,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct ApplySyncRequest {
    pub scene_id: String,
    #[serde(default = "default_apply_mode")]
    pub mode: String,
    #[serde(default)]
    pub allow_delete: bool,
    #[serde(default = "default_max_operations")]
    pub max_operations: usize,
}

fn default_apply_mode() -> String {
    "apply_safe".to_string()
}

fn default_max_operations() -> usize {
    500
}

pub async fn apply_sync_route(
    State(state): State<AppState>,
    Json(req): Json<ApplySyncRequest>,
) -> Result<Json<Value>, AppError> {
    let repo = SurrealSceneRepository::new(state.db.clone());

    let desired_objects = repo.list_desired_objects(&req.scene_id, true, None, None).await?;

    let unreal_client = UnrealClient::new(&state.config);
    let actual_actors = match unreal_client.get_actors_in_level().await {
        Ok(actors) => actors,
        Err(e) => {
            tracing::warn!("Could not reach Unreal for apply_sync: {e}");
            return Ok(Json(error_response(
                "unreal_unreachable",
                &format!("Could not reach Unreal for apply_sync: {e}. Apply aborted to avoid unsafe operations on empty actual state."),
            )));
        }
    };

    let plan = plan_sync(&req.scene_id, &desired_objects, &actual_actors);

    if plan.operations.len() > req.max_operations {
        return Err(AppError::Validation(
            format!(
                "plan has {} operations which exceeds max_operations {}. Use scene_plan_sync first to review.",
                plan.operations.len(),
                req.max_operations
            ),
        ));
    }

    let allow_delete = req.mode == "apply_all" || req.allow_delete;
    let mode = req.mode.as_str();

    let result = apply_sync(&state.config, &repo, &plan, mode, allow_delete).await?;

    Ok(Json(success_response(
        serde_json::to_value(result).unwrap_or_default(),
    )))
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
