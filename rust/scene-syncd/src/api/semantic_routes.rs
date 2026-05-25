use crate::api::common::{normalize_scene_id_input, success_response, AppState};
use axum::extract::State;
use axum::routing::post;
use axum::Json;
use axum::Router;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::db::SurrealSceneRepository;
use crate::error::AppError;

#[derive(Debug, Deserialize)]
pub struct BulkUpsertEntitiesRequest {
    pub scene_id: String,
    pub entities: Vec<EntityPayload>,
}

#[derive(Debug, Deserialize)]
pub struct EntityPayload {
    pub entity_id: String,
    pub kind: String,
    pub name: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub mcp_ids: Vec<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

pub async fn bulk_upsert_entities(
    State(state): State<AppState>,
    Json(req): Json<BulkUpsertEntitiesRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let mut created = Vec::new();
    let mut errors = Vec::new();

    for entity in req.entities {
        match repo
            .upsert_entity(
                &scene_id,
                &entity.entity_id,
                &entity.kind,
                &entity.name,
                entity.properties,
                entity.tags,
                entity.mcp_ids,
                entity.metadata,
            )
            .await
        {
            Ok(e) => created.push(serde_json::to_value(e).unwrap_or_default()),
            Err(e) => errors.push(json!({"entity_id": entity.entity_id, "error": e.to_string()})),
        }
    }

    Ok(Json(success_response(json!({
        "upserted_count": created.len(),
        "error_count": errors.len(),
        "entities": created,
        "errors": errors,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct ListEntitiesRequest {
    pub scene_id: String,
    #[serde(default)]
    pub kind: Option<String>,
}

pub async fn list_entities(
    State(state): State<AppState>,
    Json(req): Json<ListEntitiesRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let entities = repo.list_entities(&scene_id, req.kind.as_deref()).await?;
    Ok(Json(success_response(json!({ "entities": entities }))))
}

#[derive(Debug, Deserialize)]
pub struct BulkUpsertRelationsRequest {
    pub scene_id: String,
    pub relations: Vec<RelationPayload>,
}

#[derive(Debug, Deserialize)]
pub struct RelationPayload {
    pub relation_id: String,
    pub source_entity_id: String,
    pub target_entity_id: String,
    pub relation_type: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

pub async fn bulk_upsert_relations(
    State(state): State<AppState>,
    Json(req): Json<BulkUpsertRelationsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let mut created = Vec::new();
    let mut errors = Vec::new();

    for relation in req.relations {
        match repo
            .upsert_relation(
                &scene_id,
                &relation.relation_id,
                &relation.source_entity_id,
                &relation.target_entity_id,
                &relation.relation_type,
                relation.properties,
                relation.metadata,
            )
            .await
        {
            Ok(r) => created.push(serde_json::to_value(r).unwrap_or_default()),
            Err(e) => {
                errors.push(json!({"relation_id": relation.relation_id, "error": e.to_string()}))
            }
        }
    }

    Ok(Json(success_response(json!({
        "upserted_count": created.len(),
        "error_count": errors.len(),
        "relations": created,
        "errors": errors,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct ListRelationsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub relation_type: Option<String>,
}

pub async fn list_relations(
    State(state): State<AppState>,
    Json(req): Json<ListRelationsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let relations = repo
        .list_relations(&scene_id, req.relation_type.as_deref())
        .await?;
    Ok(Json(success_response(json!({ "relations": relations }))))
}

#[derive(Debug, Deserialize)]
pub struct UpsertAssetRequest {
    pub scene_id: String,
    pub asset_id: String,
    pub kind: String,
    #[serde(default = "default_asset_status")]
    pub status: String,
    #[serde(default)]
    pub fallback: String,
    #[serde(default)]
    pub semantic_tags: Vec<String>,
    #[serde(default = "default_asset_quality")]
    pub quality: String,
    #[serde(default = "default_asset_variants")]
    pub variants: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

fn default_asset_status() -> String {
    "present".to_string()
}

fn default_asset_quality() -> String {
    "prototype".to_string()
}

fn default_asset_variants() -> serde_json::Value {
    json!({})
}

pub async fn upsert_asset(
    State(state): State<AppState>,
    Json(req): Json<UpsertAssetRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let asset = repo
        .upsert_asset(
            &scene_id,
            &req.asset_id,
            &req.kind,
            &req.status,
            &req.fallback,
            req.semantic_tags,
            &req.quality,
            req.variants,
            req.metadata,
        )
        .await?;
    Ok(Json(success_response(json!({ "asset": asset }))))
}

#[derive(Debug, Deserialize)]
pub struct ListAssetsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub kind: Option<String>,
}

pub async fn list_assets(
    State(state): State<AppState>,
    Json(req): Json<ListAssetsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let assets = repo.list_assets(&scene_id, req.kind.as_deref()).await?;
    Ok(Json(success_response(json!({ "assets": assets }))))
}

// ------------------------------------------------------------------
// P6: Component, Blueprint, Realization routes
// ------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct UpsertComponentRequest {
    pub scene_id: String,
    pub entity_id: String,
    pub component_type: String,
    pub name: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

pub async fn upsert_component(
    State(state): State<AppState>,
    Json(req): Json<UpsertComponentRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let component = repo
        .upsert_component(
            &scene_id,
            &req.entity_id,
            &req.component_type,
            &req.name,
            req.properties,
            req.metadata,
        )
        .await?;
    Ok(Json(success_response(json!({ "component": component }))))
}

#[derive(Debug, Deserialize)]
pub struct ListComponentsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub entity_id: Option<String>,
    #[serde(default)]
    pub component_type: Option<String>,
    #[serde(default)]
    pub sync_status: Option<String>,
}

pub async fn list_components(
    State(state): State<AppState>,
    Json(req): Json<ListComponentsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let components = repo
        .list_components(
            &scene_id,
            req.entity_id.as_deref(),
            req.component_type.as_deref(),
            req.sync_status.as_deref(),
        )
        .await?;
    Ok(Json(success_response(json!({ "components": components }))))
}

#[derive(Debug, Deserialize)]
pub struct DeleteComponentRequest {
    pub scene_id: String,
    pub entity_id: String,
    pub component_type: String,
    pub name: String,
}

pub async fn delete_component(
    State(state): State<AppState>,
    Json(req): Json<DeleteComponentRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    repo.delete_component(&scene_id, &req.entity_id, &req.component_type, &req.name)
        .await?;
    Ok(Json(success_response(json!({ "deleted": true }))))
}

#[derive(Debug, Deserialize)]
pub struct UpsertBlueprintRequest {
    pub scene_id: String,
    pub blueprint_id: String,
    pub class_name: String,
    #[serde(default)]
    pub parent_class: String,
    #[serde(default)]
    pub components: Vec<serde_json::Value>,
    #[serde(default)]
    pub variables: Vec<serde_json::Value>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

pub async fn upsert_blueprint(
    State(state): State<AppState>,
    Json(req): Json<UpsertBlueprintRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let blueprint = repo
        .upsert_blueprint(
            &scene_id,
            &req.blueprint_id,
            &req.class_name,
            &req.parent_class,
            req.components,
            req.variables,
            req.metadata,
        )
        .await?;
    Ok(Json(success_response(json!({ "blueprint": blueprint }))))
}

#[derive(Debug, Deserialize)]
pub struct ListBlueprintsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub class_name: Option<String>,
}

pub async fn list_blueprints(
    State(state): State<AppState>,
    Json(req): Json<ListBlueprintsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let blueprints = repo
        .list_blueprints(&scene_id, req.class_name.as_deref())
        .await?;
    Ok(Json(success_response(json!({ "blueprints": blueprints }))))
}

#[derive(Debug, Deserialize)]
pub struct DeleteBlueprintRequest {
    pub scene_id: String,
    pub blueprint_id: String,
}

pub async fn delete_blueprint(
    State(state): State<AppState>,
    Json(req): Json<DeleteBlueprintRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    repo.delete_blueprint(&scene_id, &req.blueprint_id).await?;
    Ok(Json(success_response(json!({ "deleted": true }))))
}

#[derive(Debug, Deserialize)]
pub struct UpsertRealizationRequest {
    pub scene_id: String,
    pub entity_id: String,
    pub policy: String,
    #[serde(default = "default_realization_status")]
    pub status: String,
    #[serde(default)]
    pub unreal_actor_name: Option<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

fn default_realization_status() -> String {
    "pending".to_string()
}

pub async fn upsert_realization(
    State(state): State<AppState>,
    Json(req): Json<UpsertRealizationRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let realization = repo
        .upsert_realization(
            &scene_id,
            &req.entity_id,
            &req.policy,
            &req.status,
            req.unreal_actor_name,
            req.metadata,
        )
        .await?;
    Ok(Json(success_response(
        json!({ "realization": realization }),
    )))
}

#[derive(Debug, Deserialize)]
pub struct ListRealizationsRequest {
    pub scene_id: String,
    #[serde(default)]
    pub entity_id: Option<String>,
    #[serde(default)]
    pub policy: Option<String>,
}

pub async fn list_realizations(
    State(state): State<AppState>,
    Json(req): Json<ListRealizationsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let realizations = repo
        .list_realizations(&scene_id, req.entity_id.as_deref(), req.policy.as_deref())
        .await?;
    Ok(Json(success_response(
        json!({ "realizations": realizations }),
    )))
}

#[derive(Debug, Deserialize)]
pub struct UpdateRealizationStatusRequest {
    pub scene_id: String,
    pub entity_id: String,
    pub policy: String,
    pub status: String,
}

pub async fn update_realization_status(
    State(state): State<AppState>,
    Json(req): Json<UpdateRealizationStatusRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let realization = repo
        .update_realization_status(&scene_id, &req.entity_id, &req.policy, &req.status)
        .await?;
    Ok(Json(success_response(
        json!({ "realization": realization }),
    )))
}


#[derive(Debug, Deserialize)]
pub struct RecordOperationRequest {
    pub scene_id: String,
    #[serde(default)]
    pub operation_id: Option<String>,
    #[serde(default)]
    pub patch_id: Option<String>,
    #[serde(default)]
    pub capability_id: Option<String>,
    #[serde(default)]
    pub command: Option<String>,
    pub status: String,
    #[serde(default)]
    pub reason: String,
    #[serde(default)]
    pub target: serde_json::Value,
}

pub async fn record_operation_external(
    State(state): State<AppState>,
    Json(req): Json<RecordOperationRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    repo.record_external_operation(
        &scene_id,
        req.operation_id,
        req.patch_id,
        req.capability_id,
        req.command,
        &req.status,
        &req.reason,
        req.target,
    )
    .await?;
    Ok(Json(success_response(json!({ "recorded": true }))))
}

#[derive(Debug, Deserialize)]
pub struct RecentOperationsRequest {
    pub scene_id: String,
    #[serde(default = "default_recent_operations_limit")]
    pub limit: usize,
}

fn default_recent_operations_limit() -> usize { 10 }

pub async fn recent_operations(
    State(state): State<AppState>,
    Json(req): Json<RecentOperationsRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let repo = SurrealSceneRepository::new(state.db.clone());
    let limit = req.limit.clamp(1, 100);
    let operations = repo.list_recent_operations(&scene_id, limit).await?;
    Ok(Json(success_response(json!({ "operations": operations }))))
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/entities/bulk-upsert", post(bulk_upsert_entities))
        .route("/entities/list", post(list_entities))
        .route("/relations/bulk-upsert", post(bulk_upsert_relations))
        .route("/relations/list", post(list_relations))
        .route("/assets/upsert", post(upsert_asset))
        .route("/assets/list", post(list_assets))
        .route("/components/upsert", post(upsert_component))
        .route("/components/list", post(list_components))
        .route("/components/delete", post(delete_component))
        .route("/operations/record", post(record_operation_external))
        .route("/operations/recent", post(recent_operations))
        .route("/blueprints/upsert", post(upsert_blueprint))
        .route("/blueprints/list", post(list_blueprints))
        .route("/blueprints/delete", post(delete_blueprint))
        .route("/realizations/upsert", post(upsert_realization))
        .route("/realizations/list", post(list_realizations))
        .route(
            "/realizations/update-status",
            post(update_realization_status),
        )
}
