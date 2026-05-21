use crate::api::common::{normalize_scene_id_input, success_response, AppState};
use axum::extract::State;
use axum::routing::post;
use axum::Json;
use axum::Router;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::SurrealSceneRepository;
use crate::domain::transform::compute_desired_hash;
use crate::error::AppError;
use crate::layout::denormalizer::denormalize_layout;
use crate::layout::kind_registry::KindRegistry;
use crate::layout::preview::preview_layout;
use crate::layout::realization::{realize_layout, RealizationStage};

pub async fn update_layout_node_transform(
    State(state): State<AppState>,
    axum::extract::Path((scene_id, entity_id)): axum::extract::Path<(String, String)>,
    Json(req): Json<serde_json::Value>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    // Merge existing properties with new transform data
    let entities = repo.list_entities(&scene_id, None).await?;
    let entity = entities
        .into_iter()
        .find(|e| e.entity_id == entity_id)
        .ok_or_else(|| AppError::NotFound(format!("entity {entity_id} not found")))?;

    let mut properties = entity.properties.clone();
    if let Some(loc) = req.get("location") {
        properties["location"] = loc.clone();
    }
    if let Some(rot) = req.get("rotation") {
        properties["rotation"] = rot.clone();
    }
    if let Some(scl) = req.get("scale") {
        properties["scale"] = scl.clone();
    }
    if let Some(props) = req.get("properties") {
        if let Some(obj) = props.as_object() {
            for (k, v) in obj {
                properties[k] = v.clone();
            }
        }
    }

    let updated = repo
        .update_entity_transform(&scene_id, &entity_id, properties)
        .await?;
    Ok(Json(success_response(
        serde_json::to_value(updated)
            .map_err(|e| AppError::Internal(format!("serialize error: {e}")))?,
    )))
}

pub async fn approve_layout(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    // Update scene status to approved_layout
    let _scene = repo
        .update_scene_status(&scene_id, "approved_layout")
        .await?;

    // Create a snapshot for rollback
    let snapshot = repo
        .create_snapshot(
            &scene_id,
            &format!(
                "auto_approved_{}",
                chrono::Utc::now().format("%Y%m%d%H%M%S")
            ),
            Some("Auto-snapshot on layout approval".to_string()),
        )
        .await?;

    Ok(Json(success_response(json!({
        "scene_id": scene_id,
        "status": "approved_layout",
        "snapshot_id": snapshot.id,
    }))))
}

pub async fn preview_layout_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let objects = preview_layout(&repo, &scene_id).await?;

    let object_values: Vec<serde_json::Value> = objects
        .into_iter()
        .map(|o| serde_json::to_value(o).unwrap_or_default())
        .collect();

    Ok(Json(success_response(json!({
        "scene_id": scene_id,
        "object_count": object_values.len(),
        "objects": object_values,
    }))))
}

pub async fn compile_preview_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let result =
        crate::compiler::pipeline::CompilerPipeline::compile_preview(&repo, &scene_id).await?;

    Ok(Json(success_response(json!({
        "scene_id": result.scene_id,
        "stage": result.stage,
        "summary": {
            "errors": result.summary.errors,
            "warnings": result.summary.warnings,
            "infos": result.summary.infos,
            "objects": result.summary.objects,
        },
        "objects": result.objects,
        "diagnostics": result.diagnostics,
    }))))
}

// ------------------------------------------------------------------
// Realization pipeline
// ------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct RealizeLayoutRequest {
    pub stage: String,
    #[serde(default)]
    pub persist: bool,
}

pub async fn realize_layout_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
    Json(req): Json<RealizeLayoutRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let stage = RealizationStage::parse(&req.stage)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let objects = realize_layout(&repo, &scene_id, stage, req.persist).await?;

    let object_values: Vec<serde_json::Value> = objects
        .into_iter()
        .map(|o| serde_json::to_value(o).unwrap_or_default())
        .collect();

    Ok(Json(success_response(json!({
        "scene_id": scene_id,
        "stage": req.stage,
        "persisted": req.persist,
        "object_count": object_values.len(),
        "objects": object_values,
    }))))
}

// ------------------------------------------------------------------
// Layout denormalization
// ------------------------------------------------------------------

pub async fn denormalize_layout_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let entities = repo.list_entities(&scene_id, None).await?;
    let relations = repo.list_relations(&scene_id, None).await?;

    let registry = KindRegistry::default();
    let mut objects = denormalize_layout(&scene_id, &entities, &relations, &registry)?;

    // Compute desired_hash for each object and upsert
    let mut created = Vec::new();
    let mut errors = Vec::new();
    for obj in &mut objects {
        match compute_desired_hash(obj) {
            Ok(hash) => obj.desired_hash = hash,
            Err(e) => {
                errors.push(json!({
                    "mcp_id": obj.mcp_id,
                    "error": e
                }));
                continue;
            }
        }
        match repo.upsert_object(obj).await {
            Ok(saved) => created.push(serde_json::to_value(saved).unwrap_or_default()),
            Err(e) => errors.push(json!({
                "mcp_id": obj.mcp_id.clone(),
                "error": e.to_string()
            })),
        }
    }

    Ok(Json(success_response(json!({
        "upserted_count": created.len(),
        "error_count": errors.len(),
        "objects": created,
        "errors": errors,
    }))))
}

// ------------------------------------------------------------------
// Sprint F: Compiler API routes
// ------------------------------------------------------------------

pub async fn validate_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let result =
        crate::compiler::pipeline::CompilerPipeline::compile_validate_only(&repo, &scene_id)
            .await?;

    Ok(Json(success_response(json!({
        "scene_id": result.scene_id,
        "stage": result.stage,
        "summary": {
            "errors": result.summary.errors,
            "warnings": result.summary.warnings,
            "infos": result.summary.infos,
            "objects": result.summary.objects,
            "instance_sets": result.summary.instance_sets,
            "world_cells": result.summary.world_cells,
        },
        "diagnostics": result.diagnostics,
    }))))
}

pub async fn compile_plan_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    // Fetch actual state from Unreal for diff comparison.
    let actual_objects = repo
        .list_desired_objects(&scene_id, true, None, None)
        .await?;

    let result =
        crate::compiler::pipeline::CompilerPipeline::compile_plan(&repo, &scene_id, actual_objects)
            .await?;

    Ok(Json(success_response(json!({
        "scene_id": result.scene_id,
        "stage": result.stage,
        "mode": result.mode,
        "summary": {
            "errors": result.summary.errors,
            "warnings": result.summary.warnings,
            "infos": result.summary.infos,
            "objects": result.summary.objects,
            "instance_sets": result.summary.instance_sets,
            "world_cells": result.summary.world_cells,
        },
        "diagnostics": result.diagnostics,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct CompileApplyRequest {
    #[serde(default)]
    pub allow_delete: bool,
}

pub async fn compile_apply_route(
    State(state): State<AppState>,
    axum::extract::Path(scene_id): axum::extract::Path<String>,
    Json(req): Json<CompileApplyRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());

    let result = crate::compiler::pipeline::CompilerPipeline::compile_apply(
        &repo,
        &scene_id,
        req.allow_delete,
    )
    .await?;

    Ok(Json(success_response(json!({
        "scene_id": result.scene_id,
        "stage": result.stage,
        "mode": result.mode,
        "summary": {
            "errors": result.summary.errors,
            "warnings": result.summary.warnings,
            "infos": result.summary.infos,
            "objects": result.summary.objects,
            "instance_sets": result.summary.instance_sets,
            "world_cells": result.summary.world_cells,
        },
        "diagnostics": result.diagnostics,
    }))))
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route(
            "/layouts/{scene_id}/denormalize",
            post(denormalize_layout_route),
        )
        .route(
            "/layouts/{scene_id}/nodes/{entity_id}/transform",
            post(update_layout_node_transform),
        )
        .route("/layouts/{scene_id}/approve", post(approve_layout))
        .route("/layouts/{scene_id}/preview", post(preview_layout_route))
        .route(
            "/layouts/{scene_id}/compile/preview",
            post(compile_preview_route),
        )
        .route("/layouts/{scene_id}/validate", post(validate_route))
        .route("/layouts/{scene_id}/compile/plan", post(compile_plan_route))
        .route(
            "/layouts/{scene_id}/compile/apply",
            post(compile_apply_route),
        )
        .route(
            "/realizations/{scene_id}/realize",
            post(realize_layout_route),
        )
}
