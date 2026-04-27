use crate::config::Config;
use crate::db::SurrealSceneRepository;
use crate::error::AppError;
use crate::sync::{SyncAction, SyncOperation, SyncPlan};
use crate::unreal::client::UnrealClient;
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

/// Resolve an asset path from the `asset_ref` JSON object.
/// If `status` is `"missing"`, returns the `fallback` path and logs a warning.
fn resolve_asset_path(asset_ref: Option<&serde_json::Value>) -> String {
    let default = "/Engine/BasicShapes/Cube.Cube";
    let Some(aref) = asset_ref else {
        return default.to_string();
    };
    let status = aref.get("status").and_then(|v| v.as_str()).unwrap_or("present");
    if status == "missing" {
        let fallback = aref
            .get("fallback")
            .and_then(|v| v.as_str())
            .unwrap_or(default);
        let primary = aref.get("path").and_then(|v| v.as_str()).unwrap_or("");
        tracing::warn!(
            primary = primary,
            fallback = fallback,
            "Asset is missing, using fallback"
        );
        return fallback.to_string();
    }
    aref.get("path")
        .and_then(|v| v.as_str())
        .unwrap_or(default)
        .to_string()
}

pub async fn apply_sync(
    config: &Config,
    db: &SurrealSceneRepository,
    plan: &SyncPlan,
    mode: &str,
    allow_delete: bool,
) -> Result<SyncApplyResult, AppError> {
    if mode == "plan_only" {
        return Err(AppError::Validation(
            "plan_only is not valid for /sync/apply. Use /sync/plan instead.".to_string(),
        ));
    }

    let run_id = format!("{}_{}", plan.scene_id, ulid::Ulid::new());
    let unreal = UnrealClient::new(config);

    db.create_sync_run(&run_id, &plan.scene_id, mode, "running")
        .await?;

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

    // --- P4: Batch apply via apply_scene_delta ---------------------------
    let batch_result = apply_scene_delta_batch(db, &unreal, &run_id, &plan.scene_id, plan, mode, allow_delete).await;
    match batch_result {
        Ok(ops) => {
            for ao in ops {
                if ao.status == "success" {
                    result.summary.succeeded += 1;
                } else if ao.status == "skipped" {
                    result.summary.skipped += 1;
                } else {
                    result.summary.failed += 1;
                }
                match ao.action.as_str() {
                    "create" => result.summary.creates += 1,
                    "update_transform" => result.summary.update_transforms += 1,
                    "update_visual" => result.summary.update_visuals += 1,
                    "delete" => result.summary.deletes += 1,
                    "noop" => result.summary.noops += 1,
                    _ => {}
                }
                result.operations.push(ao);
            }
        }
        Err(e) => {
            result.summary.failed += plan.operations.len();
            result.warnings.push(format!("Batch apply failed: {e}"));
            for op in &plan.operations {
                result.operations.push(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: format!("{:?}", op.action).to_lowercase(),
                    status: "error".to_string(),
                    unreal_actor_name: None,
                    error: Some(e.to_string()),
                });
            }
        }
    }
    // ------------------------------------------------------------------

    if let Err(e) = db.finish_sync_run(&run_id, &result.summary).await {
        result.warnings.push(format!("Failed to finalize sync run: {e}"));
    }

    Ok(result)
}

async fn apply_scene_delta_batch(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    plan: &SyncPlan,
    mode: &str,
    allow_delete: bool,
) -> Result<Vec<AppliedOperation>, AppError> {
    let mut creates: Vec<serde_json::Value> = Vec::new();
    let mut updates: Vec<serde_json::Value> = Vec::new();
    let mut deletes: Vec<serde_json::Value> = Vec::new();
    let mut pre_results: Vec<AppliedOperation> = Vec::new();

    for op in &plan.operations {
        match op.action {
            SyncAction::Create => {
                if let Some(desired) = &op.desired {
                    let mcp_id = op.mcp_id.as_str();
                    let desired_name = desired
                        .get("desired_name")
                        .and_then(|v| v.as_str())
                        .unwrap_or(mcp_id);
                    let actor_type = desired
                        .get("actor_type")
                        .and_then(|v| v.as_str())
                        .unwrap_or("StaticMeshActor");
                    let asset_path = resolve_asset_path(desired.get("asset_ref"));
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
                    creates.push(json!({
                        "name": desired_name,
                        "type": actor_type,
                        "mcp_id": mcp_id,
                        "location": loc,
                        "rotation": rot,
                        "scale": scl,
                        "static_mesh": asset_path,
                        "tags": tags,
                    }));
                }
            }
            SyncAction::UpdateTransform => {
                if mode == "plan_only" {
                    pre_results.push(AppliedOperation {
                        mcp_id: op.mcp_id.clone(),
                        action: "update_transform".to_string(),
                        status: "skipped".to_string(),
                        unreal_actor_name: None,
                        error: Some("plan_only mode".to_string()),
                    });
                    continue;
                }
                if let Some(desired) = &op.desired {
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
                    updates.push(json!({
                        "mcp_id": mcp_id,
                        "location": loc,
                        "rotation": rot,
                        "scale": scl,
                    }));
                }
            }
            SyncAction::UpdateVisual => {
                if mode == "plan_only" {
                    pre_results.push(AppliedOperation {
                        mcp_id: op.mcp_id.clone(),
                        action: "update_visual".to_string(),
                        status: "skipped".to_string(),
                        unreal_actor_name: None,
                        error: Some("plan_only mode".to_string()),
                    });
                    continue;
                }
                // Visual updates still handled individually (bridge limitation)
                let applied = apply_visual_update(db, unreal, run_id, scene_id, op).await;
                pre_results.push(applied?);
            }
            SyncAction::Delete => {
                if mode == "plan_only" {
                    pre_results.push(AppliedOperation {
                        mcp_id: op.mcp_id.clone(),
                        action: "delete".to_string(),
                        status: "skipped".to_string(),
                        unreal_actor_name: None,
                        error: Some("plan_only mode".to_string()),
                    });
                    continue;
                }
                if !allow_delete {
                    db.record_operation(
                        run_id, scene_id, &op.mcp_id, "delete", "skipped", "allow_delete not enabled",
                    )
                    .await?;
                    pre_results.push(AppliedOperation {
                        mcp_id: op.mcp_id.clone(),
                        action: "delete".to_string(),
                        status: "skipped".to_string(),
                        unreal_actor_name: None,
                        error: Some("allow_delete not enabled".to_string()),
                    });
                    continue;
                }
                deletes.push(json!({ "mcp_id": op.mcp_id }));
            }
            SyncAction::Noop => {
                db.record_operation(
                    run_id, scene_id, &op.mcp_id, "noop", "success", "no changes needed",
                )
                .await?;
                pre_results.push(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "noop".to_string(),
                    status: "success".to_string(),
                    unreal_actor_name: None,
                    error: None,
                });
            }
            SyncAction::Conflict => {
                db.record_operation(
                    run_id, scene_id, &op.mcp_id, "conflict", "skipped", "conflict not auto-resolved",
                )
                .await?;
                pre_results.push(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "conflict".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("conflict not auto-resolved".to_string()),
                });
            }
            SyncAction::Unsupported => {
                db.record_operation(
                    run_id, scene_id, &op.mcp_id, "unsupported", "skipped", "unsupported action",
                )
                .await?;
                pre_results.push(AppliedOperation {
                    mcp_id: op.mcp_id.clone(),
                    action: "unsupported".to_string(),
                    status: "skipped".to_string(),
                    unreal_actor_name: None,
                    error: Some("unsupported action".to_string()),
                });
            }
        }
    }

    // --- Send batch delta if any creates/updates/deletes exist ------------
    if !creates.is_empty() || !updates.is_empty() || !deletes.is_empty() {
        let delta_result = unreal.apply_scene_delta(
            &format!("{run_id}_batch"),
            creates.clone(),
            updates.clone(),
            deletes.clone(),
        ).await;

        match delta_result {
            Ok(response) => {
                let success = response.get("success").and_then(|v| v.as_bool()).unwrap_or(false);
                if success {
                    let created_count = response.get("created_count").and_then(|v| v.as_i64()).unwrap_or(0) as usize;
                    let updated_count = response.get("updated_count").and_then(|v| v.as_i64()).unwrap_or(0) as usize;
                    let deleted_count = response.get("deleted_count").and_then(|v| v.as_i64()).unwrap_or(0) as usize;

                    tracing::info!(
                        created = created_count,
                        updated = updated_count,
                        deleted = deleted_count,
                        "apply_scene_delta succeeded"
                    );

                    // Mark created objects as synced
                    for create in &creates {
                        if let Some(mcp_id) = create.get("mcp_id").and_then(|v| v.as_str()) {
                            let desired = plan.operations.iter()
                                .find(|op| op.mcp_id == mcp_id)
                                .and_then(|op| op.desired.as_ref());
                            let desired_hash = desired
                                .and_then(|d| d.get("desired_hash"))
                                .and_then(|v| v.as_str())
                                .unwrap_or("");
                            db.mark_object_synced(scene_id, mcp_id, desired_hash, None).await?;
                            db.record_operation(run_id, scene_id, mcp_id, "create", "success", "actor created in Unreal (batch)").await?;
                        }
                    }
                    // Mark updated objects as synced
                    for update in &updates {
                        if let Some(mcp_id) = update.get("mcp_id").and_then(|v| v.as_str()) {
                            let desired = plan.operations.iter()
                                .find(|op| op.mcp_id == mcp_id)
                                .and_then(|op| op.desired.as_ref());
                            let desired_hash = desired
                                .and_then(|d| d.get("desired_hash"))
                                .and_then(|v| v.as_str())
                                .unwrap_or("");
                            db.mark_object_synced(scene_id, mcp_id, desired_hash, None).await?;
                            db.record_operation(run_id, scene_id, mcp_id, "update_transform", "success", "transform updated (batch)").await?;
                        }
                    }
                    // Mark deleted objects as synced
                    for delete in &deletes {
                        if let Some(mcp_id) = delete.get("mcp_id").and_then(|v| v.as_str()) {
                            db.mark_object_deleted_applied(scene_id, mcp_id).await?;
                            db.record_operation(run_id, scene_id, mcp_id, "delete", "success", "actor deleted (batch)").await?;
                        }
                    }

                    // Build per-operation results from batch response
                    let mut batch_results = Vec::new();
                    for create in &creates {
                        if let Some(mcp_id) = create.get("mcp_id").and_then(|v| v.as_str()) {
                            batch_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "create".to_string(),
                                status: "success".to_string(),
                                unreal_actor_name: None,
                                error: None,
                            });
                        }
                    }
                    for update in &updates {
                        if let Some(mcp_id) = update.get("mcp_id").and_then(|v| v.as_str()) {
                            batch_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "update_transform".to_string(),
                                status: "success".to_string(),
                                unreal_actor_name: None,
                                error: None,
                            });
                        }
                    }
                    for delete in &deletes {
                        if let Some(mcp_id) = delete.get("mcp_id").and_then(|v| v.as_str()) {
                            batch_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "delete".to_string(),
                                status: "success".to_string(),
                                unreal_actor_name: None,
                                error: None,
                            });
                        }
                    }
                    pre_results.extend(batch_results);
                } else {
                    let err_msg = response.get("error").and_then(|e| e.as_str()).unwrap_or("unknown batch error");
                    tracing::warn!(error = err_msg, "apply_scene_delta failed");
                    for create in &creates {
                        if let Some(mcp_id) = create.get("mcp_id").and_then(|v| v.as_str()) {
                            db.record_operation(run_id, scene_id, mcp_id, "create", "error", err_msg).await?;
                            pre_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "create".to_string(),
                                status: "error".to_string(),
                                unreal_actor_name: None,
                                error: Some(err_msg.to_string()),
                            });
                        }
                    }
                    for update in &updates {
                        if let Some(mcp_id) = update.get("mcp_id").and_then(|v| v.as_str()) {
                            db.record_operation(run_id, scene_id, mcp_id, "update_transform", "error", err_msg).await?;
                            pre_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "update_transform".to_string(),
                                status: "error".to_string(),
                                unreal_actor_name: None,
                                error: Some(err_msg.to_string()),
                            });
                        }
                    }
                    for delete in &deletes {
                        if let Some(mcp_id) = delete.get("mcp_id").and_then(|v| v.as_str()) {
                            db.record_operation(run_id, scene_id, mcp_id, "delete", "error", err_msg).await?;
                            pre_results.push(AppliedOperation {
                                mcp_id: mcp_id.to_string(),
                                action: "delete".to_string(),
                                status: "error".to_string(),
                                unreal_actor_name: None,
                                error: Some(err_msg.to_string()),
                            });
                        }
                    }
                }
            }
            Err(e) => {
                let err_msg = e.to_string();
                tracing::warn!(error = %err_msg, "apply_scene_delta bridge error");
                for create in &creates {
                    if let Some(mcp_id) = create.get("mcp_id").and_then(|v| v.as_str()) {
                        db.record_operation(run_id, scene_id, mcp_id, "create", "error", &err_msg).await?;
                        pre_results.push(AppliedOperation {
                            mcp_id: mcp_id.to_string(),
                            action: "create".to_string(),
                            status: "error".to_string(),
                            unreal_actor_name: None,
                            error: Some(err_msg.clone()),
                        });
                    }
                }
                for update in &updates {
                    if let Some(mcp_id) = update.get("mcp_id").and_then(|v| v.as_str()) {
                        db.record_operation(run_id, scene_id, mcp_id, "update_transform", "error", &err_msg).await?;
                        pre_results.push(AppliedOperation {
                            mcp_id: mcp_id.to_string(),
                            action: "update_transform".to_string(),
                            status: "error".to_string(),
                            unreal_actor_name: None,
                            error: Some(err_msg.clone()),
                        });
                    }
                }
                for delete in &deletes {
                    if let Some(mcp_id) = delete.get("mcp_id").and_then(|v| v.as_str()) {
                        db.record_operation(run_id, scene_id, mcp_id, "delete", "error", &err_msg).await?;
                        pre_results.push(AppliedOperation {
                            mcp_id: mcp_id.to_string(),
                            action: "delete".to_string(),
                            status: "error".to_string(),
                            unreal_actor_name: None,
                            error: Some(err_msg.clone()),
                        });
                    }
                }
            }
        }
    }

    Ok(pre_results)
}

#[allow(dead_code)]
fn extract_verified_actor_name(
    verify_response: &serde_json::Value,
    mcp_id: &str,
) -> Result<Option<String>, String> {
    let verified = verify_response
        .get("success")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if !verified {
        let err_msg = verify_response
            .get("error")
            .and_then(|e| e.as_str())
            .unwrap_or("created actor could not be verified by mcp_id");
        return Err(format!(
            "created actor was not verifiable by mcp_id: {err_msg}"
        ));
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

async fn apply_visual_update(
    db: &SurrealSceneRepository,
    unreal: &UnrealClient,
    run_id: &str,
    scene_id: &str,
    op: &SyncOperation,
) -> Result<AppliedOperation, AppError> {
    let desired = op.desired.as_ref().ok_or_else(|| {
        AppError::Validation("update_visual operation missing desired data".to_string())
    })?;

    let mcp_id = op.mcp_id.as_str();
    let mut applied_count = 0usize;
    let mut skip_reasons: Vec<String> = Vec::new();

    // Resolve the Unreal actor name from the operation's actual data or via lookup
    let actor_name = op
        .actual
        .as_ref()
        .and_then(|a| a.get("name"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    // Apply material color if visual contains color info
    if let Some(visual) = desired.get("visual").and_then(|v| v.as_object()) {
        if let (Some(r), Some(g), Some(b)) = (
            visual.get("color_r").and_then(|v| v.as_f64()),
            visual.get("color_g").and_then(|v| v.as_f64()),
            visual.get("color_b").and_then(|v| v.as_f64()),
        ) {
            if let Some(ref name) = actor_name {
                tracing::info!(mcp_id = mcp_id, "Setting material color in Unreal");
                let result = unreal.set_mesh_material_color(name, r, g, b).await;
                match result {
                    Ok(response) => {
                        let success = response
                            .get("success")
                            .and_then(|v| v.as_bool())
                            .unwrap_or(false);
                        if success {
                            applied_count += 1;
                        } else {
                            let err = response
                                .get("error")
                                .and_then(|e| e.as_str())
                                .unwrap_or("unknown material color error");
                            skip_reasons.push(format!("material color failed: {err}"));
                        }
                    }
                    Err(e) => {
                        skip_reasons.push(format!("material color bridge error: {e}"));
                    }
                }
            } else {
                skip_reasons.push("material color skipped: actor name not resolved".to_string());
            }
        }
    }

    // Asset/mesh changes require delete+create (bridge limitation)
    if desired.get("asset_ref").is_some()
        && op
            .actual
            .as_ref()
            .and_then(|a| a.get("static_mesh"))
            .is_some()
    {
        let desired_path = desired
            .get("asset_ref")
            .and_then(|v| v.get("path"))
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let actual_path = op
            .actual
            .as_ref()
            .and_then(|a| a.get("static_mesh"))
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if desired_path != actual_path && !desired_path.is_empty() {
            skip_reasons.push(
                "asset change requires delete+create (bridge has no mesh swap command)".to_string(),
            );
        }
    }

    // Tag changes are set at spawn time only (bridge limitation)
    if desired.get("tags").is_some() {
        // Tags are already applied on create; updating them requires re-spawn
    }

    let desired_hash = desired
        .get("desired_hash")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if applied_count > 0 {
        db.mark_object_synced(scene_id, mcp_id, desired_hash, None)
            .await?;
        db.record_operation(
            run_id,
            scene_id,
            mcp_id,
            "update_visual",
            "success",
            &format!("visual update applied ({applied_count} changes)"),
        )
        .await?;
        Ok(AppliedOperation {
            mcp_id: mcp_id.to_string(),
            action: "update_visual".to_string(),
            status: "success".to_string(),
            unreal_actor_name: None,
            error: None,
        })
    } else {
        let reason = if skip_reasons.is_empty() {
            "visual hash differs but no applicable bridge command exists"
        } else {
            &skip_reasons.join("; ")
        };
        db.record_operation(
            run_id,
            scene_id,
            mcp_id,
            "update_visual",
            "skipped",
            reason,
        )
        .await?;
        Ok(AppliedOperation {
            mcp_id: mcp_id.to_string(),
            action: "update_visual".to_string(),
            status: "skipped".to_string(),
            unreal_actor_name: None,
            error: Some(reason.to_string()),
        })
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
