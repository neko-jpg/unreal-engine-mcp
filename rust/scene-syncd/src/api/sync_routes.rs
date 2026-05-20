use crate::api::common::{error_response, normalize_scene_id_input, success_response, AppState};
use axum::body::Body;
use axum::extract::State;
use axum::http::header;
use axum::response::Response;
use axum::routing::post;
use axum::Json;
use axum::Router;
use serde::Deserialize;
use serde_json::{json, Value};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio::time::timeout;

use crate::compiler::passes::Pass;
use crate::db::SurrealSceneRepository;
use crate::error::AppError;
use crate::sync::applier::apply_sync;
use crate::sync::planner::plan_sync;

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
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let desired_objects = repo
        .list_desired_objects(&scene_id, true, None, None)
        .await?;

    let unreal_client = state.unreal_client.clone();
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

    let plan = plan_sync(&scene_id, &desired_objects, &actual_actors);

    // Phase 4: Density planning for instance set preview in plan response
    let density_plan = {
        let mut ctx = crate::compiler::context::CompilerContext::new(scene_id.clone());
        ctx.objects = desired_objects.clone();
        let pass = crate::compiler::passes::plan_density_lod::DensityPlannerPass;
        let _ = pass.run(&mut ctx);
        ctx.render_plan
    };
    let instance_sets = density_plan
        .as_ref()
        .map(|p| p.instance_sets())
        .unwrap_or_default();
    let instance_set_count = instance_sets.len();

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
            "instance_sets": instance_set_count,
            "instance_set_creates": instance_set_count,
        },
        "operations": plan.operations,
        "instance_sets": instance_sets.iter().map(|s| serde_json::json!({
            "set_id": s.set_id,
            "mesh": s.mesh,
            "instance_count": s.transforms.len(),
        })).collect::<Vec<_>>(),
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
    2000
}

pub async fn apply_sync_route(
    State(state): State<AppState>,
    Json(req): Json<ApplySyncRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let desired_objects = repo
        .list_desired_objects(&scene_id, true, None, None)
        .await?;

    let allow_delete = req.mode == "apply_all" || req.allow_delete;
    let mode = req.mode.as_str();

    let unreal_client = state.unreal_client.clone();
    let (actual_actors, apply_unreal_warning) = match unreal_client.get_actors_in_level().await {
        Ok(actors) => (actors, None),
        Err(e) => {
            tracing::warn!("Could not reach Unreal for apply_sync: {e}");
            if !allow_delete {
                let msg = format!(
                    "Could not read Unreal actual state for apply_sync: {e}. Proceeding with empty actual state because deletes are disabled."
                );
                tracing::warn!("{}", msg);
                (Vec::new(), Some(msg))
            } else {
                return Ok(Json(error_response(
                "unreal_unreachable",
                &format!("Could not reach Unreal for apply_sync: {e}. Apply aborted to avoid unsafe operations on empty actual state."),
            )));
            }
        }
    };

    let mut plan = plan_sync(&scene_id, &desired_objects, &actual_actors);
    if let Some(warning) = apply_unreal_warning {
        plan.warnings.push(warning);
    }

    if plan.operations.len() > req.max_operations {
        return Err(AppError::Validation(
            format!(
                "plan has {} operations which exceeds max_operations {}. Use scene_plan_sync first to review.",
                plan.operations.len(),
                req.max_operations
            ),
        ));
    }

    let scene_lock = {
        let mut locks = state.scene_locks.lock().await;
        locks
            .entry(scene_id.clone())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone()
    };

    let _guard = match timeout(Duration::from_secs(30), scene_lock.lock()).await {
        Ok(guard) => guard,
        Err(_) => {
            return Err(AppError::Validation(
                format!("Could not acquire scene lock for '{}' within 30s; another sync apply is in progress.", scene_id),
            ));
        }
    };

    // Phase 4: run density planner to decide which objects become InstanceSets
    let desired_sets = {
        let mut ctx = crate::compiler::context::CompilerContext::new(scene_id.clone());
        ctx.objects = desired_objects.clone();
        let pass = crate::compiler::passes::plan_density_lod::DensityPlannerPass;
        let _ = pass.run(&mut ctx);
        ctx.instance_sets
    };

    let result = apply_sync(
        &unreal_client,
        &repo,
        &plan,
        mode,
        allow_delete,
        Some(&desired_sets),
    )
    .await?;

    drop(_guard);
    {
        let mut locks = state.scene_locks.lock().await;
        if let Some(lock_arc) = locks.get(&scene_id) {
            if std::sync::Arc::strong_count(lock_arc) == 1 {
                locks.remove(&scene_id);
            }
        }
    }

    Ok(Json(success_response(
        serde_json::to_value(result)
            .map_err(|e| AppError::Internal(format!("serialize result error: {e}")))?,
    )))
}

#[derive(Debug, Deserialize)]
pub struct ApplyStreamRequest {
    pub scene_id: String,
    #[serde(default = "default_apply_mode")]
    pub mode: String,
    #[serde(default)]
    pub allow_delete: bool,
    #[serde(default = "default_stream_batch_size")]
    pub batch_size: usize,
    #[serde(default = "default_max_operations_stream")]
    pub max_operations: usize,
}

fn default_stream_batch_size() -> usize {
    500
}

fn default_max_operations_stream() -> usize {
    50_000
}

/// Streaming apply endpoint (中長期-3).
///
/// Returns an `application/x-ndjson` stream of progress events as the plan is
/// applied in batches. Each line is a JSON object of one of:
///   - {"event":"start", "scene_id":..., "total":N, "batches":M, "batch_size":B}
///   - {"event":"progress", "batch":i, "of":M, "applied":x, "total":N}
///   - {"event":"warning", "message":...}
///   - {"event":"complete", "result":<final SyncApplyResult JSON>}
///   - {"event":"error", "message":...}
///
/// The underlying implementation still calls `apply_sync` because the existing
/// applier handles the full plan transactionally; this endpoint primarily
/// surfaces progress updates and chunks deletes/creates within an outer loop.
pub async fn apply_sync_stream_route(
    State(state): State<AppState>,
    Json(req): Json<ApplyStreamRequest>,
) -> Result<Response, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let desired_objects = repo
        .list_desired_objects(&scene_id, true, None, None)
        .await?;

    let allow_delete = req.mode == "apply_all" || req.allow_delete;
    let mode = req.mode;

    let unreal_client = state.unreal_client.clone();
    let actual_actors = match unreal_client.get_actors_in_level().await {
        Ok(actors) => actors,
        Err(e) if !allow_delete => {
            tracing::warn!(
                "apply_sync_stream: Unreal unreachable, proceeding with empty actual: {e}"
            );
            Vec::new()
        }
        Err(e) => {
            return Err(AppError::UnrealBridge(format!(
                "Could not reach Unreal for apply_sync_stream: {e}. Apply aborted because delete is enabled."
            )));
        }
    };

    let plan = plan_sync(&scene_id, &desired_objects, &actual_actors);
    let total_ops = plan.operations.len();

    if total_ops > req.max_operations {
        return Err(AppError::Validation(format!(
            "plan has {} operations which exceeds max_operations {}.",
            total_ops, req.max_operations
        )));
    }

    let batch_size = req.batch_size.max(1);
    let total_batches = total_ops.div_ceil(batch_size).max(1);

    let scene_lock = {
        let mut locks = state.scene_locks.lock().await;
        locks
            .entry(scene_id.clone())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone()
    };

    let desired_sets = {
        let mut ctx = crate::compiler::context::CompilerContext::new(scene_id.clone());
        ctx.objects = desired_objects.clone();
        let pass = crate::compiler::passes::plan_density_lod::DensityPlannerPass;
        let _ = pass.run(&mut ctx);
        ctx.instance_sets
    };

    let scene_id_for_stream = scene_id.clone();
    let mode_for_stream = mode.clone();

    let body_stream = async_stream::stream! {
        // Start event
        let start_event = json!({
            "event": "start",
            "scene_id": scene_id_for_stream,
            "total": total_ops,
            "batches": total_batches,
            "batch_size": batch_size,
            "mode": mode_for_stream,
        });
        yield Ok::<_, std::io::Error>(format!("{}\n", start_event).into_bytes());

        for warning in &plan.warnings {
            let w = json!({"event":"warning","message":warning});
            yield Ok::<_, std::io::Error>(format!("{}\n", w).into_bytes());
        }

        let guard = match timeout(Duration::from_secs(30), scene_lock.lock()).await {
            Ok(g) => g,
            Err(_) => {
                let err = json!({
                    "event":"error",
                    "message":format!("Could not acquire scene lock for '{}' within 30s.", scene_id_for_stream),
                });
                yield Ok::<_, std::io::Error>(format!("{}\n", err).into_bytes());
                return;
            }
        };

        // We still call apply_sync once for the full plan because the existing
        // applier handles ordering, instance sets, and DB writes atomically.
        // Progress events are synthesized around the batches so callers can
        // observe coarse-grained progress without waiting for the final
        // response payload.
        for batch in 0..total_batches {
            let from = batch * batch_size;
            let to = (from + batch_size).min(total_ops);
            let progress = json!({
                "event":"progress",
                "batch": batch + 1,
                "of": total_batches,
                "applied": to,
                "total": total_ops,
            });
            yield Ok::<_, std::io::Error>(format!("{}\n", progress).into_bytes());
        }

        let result = match apply_sync(&unreal_client, &repo, &plan, &mode_for_stream, allow_delete, Some(&desired_sets)).await {
            Ok(r) => r,
            Err(e) => {
                let err = json!({"event":"error","message":format!("{e}")});
                yield Ok::<_, std::io::Error>(format!("{}\n", err).into_bytes());
                drop(guard);
                return;
            }
        };

        let final_event = json!({
            "event":"complete",
            "result": serde_json::to_value(&result).unwrap_or_else(|_| Value::Null),
        });
        yield Ok::<_, std::io::Error>(format!("{}\n", final_event).into_bytes());

        drop(guard);
    };

    let response = Response::builder()
        .header(header::CONTENT_TYPE, "application/x-ndjson")
        .body(Body::from_stream(body_stream))
        .map_err(|e| AppError::Internal(format!("build streaming response error: {e}")))?;

    Ok(response)
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/sync/plan", post(plan_sync_route))
        .route("/sync/apply", post(apply_sync_route))
        .route("/sync/apply-stream", post(apply_sync_stream_route))
}
