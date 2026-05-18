use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::Arc;
use surrealdb::engine::any::Any;
use surrealdb::Surreal;
use tokio::sync::Mutex;

use crate::config::Config;
use crate::error::AppError;
use crate::unreal::client::UnrealClient;

#[derive(Debug, Clone)]
pub struct AppState {
    pub db: Surreal<Any>,
    pub config: Config,
    pub scene_locks: Arc<Mutex<HashMap<String, Arc<Mutex<()>>>>>,
    pub unreal_client: UnrealClient,
    pub procedural_jobs: crate::procedural::jobs::JobRegistry,
}

pub fn success_response(data: Value) -> Value {
    json!({
        "success": true,
        "data": data,
        "warnings": [],
        "error": null
    })
}

pub fn error_response(code: &str, message: &str) -> Value {
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

pub fn normalize_scene_id_input(id: &str) -> Result<String, AppError> {
    crate::domain::ids::normalize_scene_id(id).map_err(AppError::Validation)
}

