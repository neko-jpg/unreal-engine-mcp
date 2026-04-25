use crate::db::SurrealSceneRepository;
use crate::error::AppError;
use crate::sync::{SyncAction, SyncOperation, SyncPlan};
use crate::unreal::client::UnrealClient;
use crate::config::Config;
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SyncApplyResult {
    pub run_id: String,
    pub scene_id: String,
    pub mode: String,
    pub summary: SyncApplySummary,
    pub operations: Vec<AppliedOperation>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SyncApplySummary {
    pub total: usize,
    pub succeeded: usize,
    pub failed: usize,
    pub skipped: usize,
    pub creates: usize,
    pub update_transforms: usize,
    pub update_visuals: usize,
    pub deletes: usize,
    pub noops: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppliedOperation {
    pub mcp_id: String,
    pub action: String,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unreal_actor_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

pub async fn apply_sync(
    config: &Config,
    db: &SurrealSceneRepository,
    plan: &SyncPlan,
    mode: &str,
    allow_delete: bool,
) -> Result<SyncApplyResult, AppError> {
    let run_id = format!("{}_{:04}", plan.scene_id, chrono::Utc::now().timestamp_millis() % 10000);
    let unreal = UnrealClient::new(config);

    db.create_sync_run(&run_id, &plan.scene_id, mode, "running").await?;

    let mut result = SyncApplyResult {
        run_id: run_id.clone(),
        scene_id: plan.scene_id.clone(),
        mode: mode.to_string(),
        ..Default::default()
    };

    result.summary.total = plan.operations.len();

    for warning in &plan.warnings {
        result.warnings.push(warning.clone());
    }

    for op in &plan.operations {
        let applied = apply_operation(
            db,
            &unreal,
            &run_id,
            &plan.scene_id,
            op,
            mode,
            allow_delete,
        ).await;

        match &applied {
            Ok(ao) => {
                if ao.status == "success" {
                    result.summary.succeeded += 1;
                } else if ao.status == "skipped" {
                    result.summary.skipped += 1;
                } else {
                    result.summary.failed += 1;
                }
                match op.action {
                    SyncAction::Create => result.summary.creates += 1,
                    SyncAction::UpdateTransform => result.summary.update_transforms += 1,
                    SyncAction::UpdateVisual => result.summary.update_visuals += 1,
                    SyncAction::Delete => result.summary.deletes += 1,
                    SyncAction::Noop => result.summary.noops += 1,
                    _ => {}
                }
            }
            Err(e) => {
                result.summary.failed += 1;
                result.operations.push(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: format!("{:?}", op.action).to_lowercase(),
                    status: "error".to_string(),
                    unreal_actor_name: None,
                    error: Some(e.to_string()),
                });
            }
        }

        if let Ok(ao) = applied {
            result.operations.push(ao);
        }
    }

    db.finish_sync_run(&run_id, &result.summary).await?;

    Ok(result)
}

async fn apply_operation(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    op: &SyncOperation,
    mode: &str,
    allow_delete: bool,
) -> Result<AppliedOperation, AppError> {
    match op.action {
        SyncAction::Create => {
            apply_create(db, unreal, run_id, scene_id, op).await
        }
        SyncAction::UpdateTransform => {
            if mode == "plan_only" {
                return Ok(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "update_transform".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("plan_only mode".to_string()),
                });
            }
            apply_transform_update(db, unreal, run_id, scene_id, op).await
        }
        SyncAction::UpdateVisual => {
            if mode == "plan_only" {
                return Ok(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "update_visual".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("plan_only mode".to_string()),
                });
            }
            Ok(AppliedOperation {
                mcp_id: op.mcp_id.clone(),
                action: "update_visual".to_string(),
                status: "skipped".to_string(),
                unreal_actor_name: None,
                error: Some("visual updates not yet implemented in bridge".to_string()),
            })
        }
        SyncAction::Delete => {
            if mode == "plan_only" {
                return Ok(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "delete".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("plan_only mode".to_string()),
                });
            }
            if !allow_delete {
                db.record_operation(run_id, scene_id, &op.mcp_id, "delete", "skipped", "allow_delete not enabled").await?;
                return Ok(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "delete".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("allow_delete not enabled".to_string()),
                });
            }
            apply_delete(db, unreal, run_id, scene_id, op).await
        }
        SyncAction::Noop => {
            db.record_operation(run_id, scene_id, &op.mcp_id, "noop", "success", "no changes needed").await?;
            Ok(AppliedOperation {
                mcp_id: op.mcp_id.clone(),
                action: "noop".to_string(),
                status: "success".to_string(),
                unreal_actor_name: None,
                error: None,
            })
        }
        SyncAction::Conflict => {
            db.record_operation(run_id, scene_id, &op.mcp_id, "conflict", "skipped", "conflict not auto-resolved").await?;
            Ok(AppliedOperation {
                mcp_id: op.mcp_id.clone(),
                action: "conflict".to_string(),
                status: "skipped".to_string(),
                unreal_actor_name: None,
                error: Some("conflict not auto-resolved".to_string()),
            })
        }
        SyncAction::Unsupported => {
            db.record_operation(run_id, scene_id, &op.mcp_id, "unsupported", "skipped", "unsupported action").await?;
            Ok(AppliedOperation {
                mcp_id: op.mcp_id.clone(),
                action: "unsupported".to_string(),
                status: "skipped".to_string(),
                unreal_actor_name: None,
                error: Some("unsupported action".to_string()),
            })
        }
    }
}

fn extract_verified_actor_name(verify_response: &serde_json::Value, mcp_id: &str) -> Result<Option<String>, String> {
    let verified = verify_response.get("success").and_then(|v| v.as_bool()).unwrap_or(false);
    if !verified {
        let err_msg = verify_response.get("error")
            .and_then(|e| e.as_str())
            .unwrap_or("created actor could not be verified by mcp_id");
        return Err(format!("created actor was not verifiable by mcp_id: {err_msg}"));
    }

    match verify_response.get("actor").and_then(|a| a.as_object()) {
        Some(actor_obj) => {
            Ok(actor_obj.get("name")
                .and_then(|n| n.as_str())
                .map(|s| s.to_string()))
        }
        None => {
            Err(format!(
                "created actor was not verifiable by mcp_id: find_actor_by_mcp_id returned success but no actor body (plugin may be missing mcp_id support for {})",
                mcp_id
            ))
        }
    }
}

async fn apply_create(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    op: &SyncOperation,
) -> Result<AppliedOperation, AppError> {
    let desired = op.desired.as_ref()
        .ok_or_else(|| AppError::Validation("create operation missing desired data".to_string()))?;

    let mcp_id = op.mcp_id.as_str();
    let desired_name = desired.get("desired_name")
        .and_then(|v| v.as_str())
        .unwrap_or(mcp_id);
    let actor_type = desired.get("actor_type")
        .and_then(|v| v.as_str())
        .unwrap_or("StaticMeshActor");

    let asset_path = desired.get("asset_ref")
        .and_then(|v| v.get("path"))
        .and_then(|v| v.as_str())
        .unwrap_or("/Engine/BasicShapes/Cube.Cube");

    let transform = desired.get("transform");
    let location = transform.and_then(|t| t.get("location"));
    let rotation = transform.and_then(|t| t.get("rotation"));
    let scale = transform.and_then(|t| t.get("scale"));

    let loc_x = location.and_then(|l| l.get("x")).and_then(|v| v.as_f64()).unwrap_or(0.0);
    let loc_y = location.and_then(|l| l.get("y")).and_then(|v| v.as_f64()).unwrap_or(0.0);
    let loc_z = location.and_then(|l| l.get("z")).and_then(|v| v.as_f64()).unwrap_or(0.0);

    let rot_pitch = rotation.and_then(|r| r.get("pitch")).and_then(|v| v.as_f64()).unwrap_or(0.0);
    let rot_yaw = rotation.and_then(|r| r.get("yaw")).and_then(|v| v.as_f64()).unwrap_or(0.0);
    let rot_roll = rotation.and_then(|r| r.get("roll")).and_then(|v| v.as_f64()).unwrap_or(0.0);

    let scl_x = scale.and_then(|s| s.get("x")).and_then(|v| v.as_f64()).unwrap_or(1.0);
    let scl_y = scale.and_then(|s| s.get("y")).and_then(|v| v.as_f64()).unwrap_or(1.0);
    let scl_z = scale.and_then(|s| s.get("z")).and_then(|v| v.as_f64()).unwrap_or(1.0);

    let mut tags = vec!["managed_by_mcp".to_string(), format!("mcp_id:{}", mcp_id)];
    if let Some(tags_val) = desired.get("tags").and_then(|v| v.as_array()) {
        for tag in tags_val {
            if let Some(tag_str) = tag.as_str() {
                let tag_string = tag_str.to_string();
                if !tags.contains(&tag_string) {
                    tags.push(tag_string);
                }
            }
        }
    }

    let spawn_params = json!({
        "name": desired_name,
        "type": actor_type,
        "mcp_id": mcp_id,
        "location": [loc_x, loc_y, loc_z],
        "rotation": [rot_pitch, rot_yaw, rot_roll],
        "scale": [scl_x, scl_y, scl_z],
        "static_mesh": asset_path,
        "tags": tags,
    });

    tracing::info!(mcp_id = mcp_id, "Spawning actor in Unreal");

    let spawn_result = unreal.spawn_actor(spawn_params).await;

    match spawn_result {
        Ok(response) => {
            let success = response.get("success").and_then(|v| v.as_bool()).unwrap_or(false);

            if success {
                let unreal_actor_name = response.get("actor")
                    .and_then(|a| a.get("name"))
                    .and_then(|n| n.as_str())
                    .or_else(|| response.get("name").and_then(|n| n.as_str()))
                    .map(|s| s.to_string());

                let verification = unreal.find_actor_by_mcp_id(mcp_id).await;
                let verified_actor_name = match verification {
                    Ok(verify_response) => {
                        match extract_verified_actor_name(&verify_response, mcp_id) {
                            Ok(name) => name,
                            Err(full_msg) => {
                                db.record_operation(run_id, scene_id, mcp_id, "create", "error", &full_msg).await?;
                                tracing::warn!(mcp_id = mcp_id, error = full_msg, "Create verification failed");
                                return Ok(AppliedOperation {
                                    mcp_id: mcp_id.to_string(),
                                    action: "create".to_string(),
                                    status: "error".to_string(),
                                    unreal_actor_name,
                                    error: Some(full_msg),
                                });
                            }
                        }
                    }
                    Err(e) => {
                        let full_msg = format!("created actor was not verifiable by mcp_id: {e}");
                        db.record_operation(run_id, scene_id, mcp_id, "create", "error", &full_msg).await?;
                        tracing::warn!(mcp_id = mcp_id, error = full_msg, "Create verification failed");
                        return Ok(AppliedOperation {
                            mcp_id: mcp_id.to_string(),
                            action: "create".to_string(),
                            status: "error".to_string(),
                            unreal_actor_name,
                            error: Some(full_msg),
                        });
                    }
                };

                let unreal_actor_name = verified_actor_name.or(unreal_actor_name);

                let desired_hash = desired.get("desired_hash")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                db.mark_object_synced(scene_id, mcp_id, desired_hash, unreal_actor_name.as_deref()).await?;
                db.record_operation(run_id, scene_id, mcp_id, "create", "success", "actor created in Unreal").await?;

                tracing::info!(mcp_id = mcp_id, actor_name = ?unreal_actor_name, "Create succeeded");

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "create".to_string(),
                    status: "success".to_string(),
                    unreal_actor_name,
                    error: None,
                })
            } else {
                let err_msg = response.get("error")
                    .and_then(|e| e.as_str())
                    .unwrap_or("unknown Unreal spawn error");

                db.record_operation(run_id, scene_id, mcp_id, "create", "error", err_msg).await?;

                tracing::warn!(mcp_id = mcp_id, error = err_msg, "Create failed");

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "create".to_string(),
                    status: "error".to_string(),
                    unreal_actor_name: None,
                    error: Some(err_msg.to_string()),
                })
            }
        }
        Err(e) => {
            db.record_operation(run_id, scene_id, mcp_id, "create", "error", &e.to_string()).await?;

            tracing::warn!(mcp_id = mcp_id, error = %e, "Create failed (bridge error)");

            Ok(AppliedOperation {
                mcp_id: mcp_id.to_string(),
                action: "create".to_string(),
                status: "error".to_string(),
                unreal_actor_name: None,
                error: Some(e.to_string()),
            })
        }
    }
}

async fn apply_transform_update(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    op: &SyncOperation,
) -> Result<AppliedOperation, AppError> {
    let desired = op.desired.as_ref()
        .ok_or_else(|| AppError::Validation("update_transform operation missing desired data".to_string()))?;

    let mcp_id = op.mcp_id.as_str();

    let transform = desired.get("transform");
    let location = transform.and_then(|t| t.get("location"));
    let rotation = transform.and_then(|t| t.get("rotation"));
    let scale = transform.and_then(|t| t.get("scale"));

    let loc: [f64; 3] = [
        location.and_then(|l| l.get("x")).and_then(|v| v.as_f64()).unwrap_or(0.0),
        location.and_then(|l| l.get("y")).and_then(|v| v.as_f64()).unwrap_or(0.0),
        location.and_then(|l| l.get("z")).and_then(|v| v.as_f64()).unwrap_or(0.0),
    ];
    let rot: [f64; 3] = [
        rotation.and_then(|r| r.get("pitch")).and_then(|v| v.as_f64()).unwrap_or(0.0),
        rotation.and_then(|r| r.get("yaw")).and_then(|v| v.as_f64()).unwrap_or(0.0),
        rotation.and_then(|r| r.get("roll")).and_then(|v| v.as_f64()).unwrap_or(0.0),
    ];
    let scl: [f64; 3] = [
        scale.and_then(|s| s.get("x")).and_then(|v| v.as_f64()).unwrap_or(1.0),
        scale.and_then(|s| s.get("y")).and_then(|v| v.as_f64()).unwrap_or(1.0),
        scale.and_then(|s| s.get("z")).and_then(|v| v.as_f64()).unwrap_or(1.0),
    ];

    tracing::info!(mcp_id = mcp_id, "Updating actor transform in Unreal");

    let result = unreal.set_actor_transform_by_mcp_id(mcp_id, loc, rot, scl).await;

    match result {
        Ok(response) => {
            let success = response.get("success").and_then(|v| v.as_bool()).unwrap_or(false);

            if success {
                let desired_hash = desired.get("desired_hash")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                db.mark_object_synced(scene_id, mcp_id, desired_hash, None).await?;
                db.record_operation(run_id, scene_id, mcp_id, "update_transform", "success", "transform updated").await?;

                tracing::info!(mcp_id = mcp_id, "Transform update succeeded");

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "update_transform".to_string(),
                    status: "success".to_string(),
                    unreal_actor_name: None,
                    error: None,
                })
            } else {
                let err_msg = response.get("error")
                    .and_then(|e| e.as_str())
                    .unwrap_or("unknown Unreal transform error");

                db.record_operation(run_id, scene_id, mcp_id, "update_transform", "error", err_msg).await?;

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "update_transform".to_string(),
                    status: "error".to_string(),
                    unreal_actor_name: None,
                    error: Some(err_msg.to_string()),
                })
            }
        }
        Err(e) => {
            db.record_operation(run_id, scene_id, mcp_id, "update_transform", "error", &e.to_string()).await?;

            Ok(AppliedOperation {
                mcp_id: mcp_id.to_string(),
                action: "update_transform".to_string(),
                status: "error".to_string(),
                unreal_actor_name: None,
                error: Some(e.to_string()),
            })
        }
    }
}

async fn apply_delete(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    op: &SyncOperation,
) -> Result<AppliedOperation, AppError> {
    let mcp_id = op.mcp_id.as_str();

    tracing::info!(mcp_id = mcp_id, "Deleting actor in Unreal");

    let result = unreal.delete_actor_by_mcp_id(mcp_id).await;

    match result {
        Ok(response) => {
            let success = response.get("success").and_then(|v| v.as_bool()).unwrap_or(false);

            if success {
                db.mark_object_deleted_applied(scene_id, mcp_id).await?;
                db.record_operation(run_id, scene_id, mcp_id, "delete", "success", "actor deleted").await?;

                tracing::info!(mcp_id = mcp_id, "Delete succeeded");

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "delete".to_string(),
                    status: "success".to_string(),
                    unreal_actor_name: None,
                    error: None,
                })
            } else {
                let err_msg = response.get("error")
                    .and_then(|e| e.as_str())
                    .unwrap_or("unknown Unreal delete error");

                db.record_operation(run_id, scene_id, mcp_id, "delete", "error", err_msg).await?;

                Ok(AppliedOperation {
                    mcp_id: mcp_id.to_string(),
                    action: "delete".to_string(),
                    status: "error".to_string(),
                    unreal_actor_name: None,
                    error: Some(err_msg.to_string()),
                })
            }
        }
        Err(e) => {
            db.record_operation(run_id, scene_id, mcp_id, "delete", "error", &e.to_string()).await?;

            Ok(AppliedOperation {
                mcp_id: mcp_id.to_string(),
                action: "delete".to_string(),
                status: "error".to_string(),
                unreal_actor_name: None,
                error: Some(e.to_string()),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_extract_verified_actor_name_success() {
        let response = json!({
            "success": true,
            "actor": {
                "name": "TestCube_01",
                "class": "StaticMeshActor",
                "location": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "tags": ["managed_by_mcp", "mcp_id:test_001"],
                "static_mesh": "/Engine/BasicShapes/Cube.Cube"
            }
        });
        let result = extract_verified_actor_name(&response, "test_001");
        assert_eq!(result.unwrap(), Some("TestCube_01".to_string()));
    }

    #[test]
    fn test_extract_verified_actor_name_missing_actor() {
        let response = json!({
            "success": true,
            "message": "No actor found with the given mcp_id",
            "actor": null
        });
        let result = extract_verified_actor_name(&response, "test_002");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("success but no actor body"));
        assert!(err.contains("test_002"));
    }

    #[test]
    fn test_extract_verified_actor_name_no_actor_field() {
        let response = json!({
            "success": false,
            "error": "Unknown command: find_actor_by_mcp_id"
        });
        let result = extract_verified_actor_name(&response, "test_003");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not verifiable by mcp_id"));
    }

    #[test]
    fn test_extract_verified_actor_name_success_false() {
        let response = json!({
            "success": false,
            "error": "something went wrong"
        });
        let result = extract_verified_actor_name(&response, "test_004");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not verifiable by mcp_id"));
    }
}
