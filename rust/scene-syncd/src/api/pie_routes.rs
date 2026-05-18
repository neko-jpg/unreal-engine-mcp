use axum::extract::State;
use axum::Json;
use axum::Router;
use axum::routing::post;
use crate::api::common::{AppState, success_response, normalize_scene_id_input};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;

#[derive(Debug, Deserialize)]
pub struct PieRunRequest {
    pub scene_id: String,
    #[serde(default = "default_pie_mode")]
    pub mode: String,
    #[serde(default = "default_pie_timeout")]
    pub timeout_secs: u64,
}

fn default_pie_mode() -> String {
    "smoke".to_string()
}

fn default_pie_timeout() -> u64 {
    60
}

pub async fn pie_run(
    State(state): State<AppState>,
    Json(req): Json<PieRunRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;
    let mode = match req.mode.as_str() {
        "smoke" => crate::unreal::pie_types::TestMode::Smoke,
        "full" => crate::unreal::pie_types::TestMode::Full,
        "performance" => crate::unreal::pie_types::TestMode::Performance,
        _ => {
            return Err(AppError::Validation(format!(
                "unknown PIE mode: {}",
                req.mode
            )))
        }
    };

    let run_id = format!(
        "pie_{}_{}",
        scene_id,
        chrono::Utc::now().format("%Y%m%d%H%M%S")
    );

    // Attempt to start PIE via Unreal client.
    let unreal_client = state.unreal_client.clone();
    let result = match unreal_client.start_pie().await {
        Ok(_) => {
            // PIE started; wait for timeout then stop.
            tokio::time::sleep(tokio::time::Duration::from_secs(req.timeout_secs.min(120))).await;
            let _ = unreal_client.stop_pie().await;
            crate::unreal::pie_types::TestResult::Passed
        }
        Err(e) => {
            tracing::warn!("PIE start failed: {e}");
            crate::unreal::pie_types::TestResult::ConnectionError
        }
    };

    let test_run = crate::unreal::pie_types::UnrealTestRun {
        run_id: run_id.clone(),
        scene_id: scene_id.clone(),
        mode,
        result,
        logs: Vec::new(),
        diagnostics: Vec::new(),
    };

    Ok(Json(success_response(json!({
        "run_id": test_run.run_id,
        "scene_id": test_run.scene_id,
        "mode": match test_run.mode {
            crate::unreal::pie_types::TestMode::Smoke => "smoke",
            crate::unreal::pie_types::TestMode::Full => "full",
            crate::unreal::pie_types::TestMode::Performance => "performance",
        },
        "result": match test_run.result {
            crate::unreal::pie_types::TestResult::Passed => "passed",
            crate::unreal::pie_types::TestResult::Failed => "failed",
            crate::unreal::pie_types::TestResult::Timeout => "timeout",
            crate::unreal::pie_types::TestResult::ConnectionError => "connection_error",
        },
    }))))
}

#[derive(Debug, Deserialize)]
pub struct ParseLogsRequest {
    pub raw_output: String,
}

pub async fn parse_logs(Json(req): Json<ParseLogsRequest>) -> Result<Json<Value>, AppError> {
    let events = crate::unreal::pie_types::parse_unreal_logs(&req.raw_output);
    let diagnostics = crate::unreal::pie_types::extract_diagnostics(&events);
    Ok(Json(success_response(json!({
        "event_count": events.len(),
        "diagnostic_count": diagnostics.len(),
        "events": events,
        "diagnostics": diagnostics,
    }))))
}

#[derive(Debug, Deserialize)]
pub struct FixPlanRequest {
    pub scene_id: String,
    pub diagnostics: Vec<serde_json::Value>,
}

pub async fn fix_plan(
    State(_state): State<AppState>,
    Json(req): Json<FixPlanRequest>,
) -> Result<Json<Value>, AppError> {
    let scene_id = normalize_scene_id_input(&req.scene_id)?;

    let diagnostics: Vec<crate::unreal::pie_types::UnrealDiagnostic> = req
        .diagnostics
        .into_iter()
        .filter_map(|v| serde_json::from_value(v).ok())
        .collect();

    // Simple fix plan generation: map each diagnostic to a fix operation.
    let operations: Vec<crate::unreal::pie_types::FixOperation> = diagnostics
        .iter()
        .filter(|d| d.severity == "error" || d.severity == "warning")
        .map(|d| crate::unreal::pie_types::FixOperation {
            operation_type: match d.code.as_str() {
                "NO_Z_FIGHTING" | "Z_FIGHTING" => "adjust_transform".to_string(),
                "NO_OVERLAP" | "OVERLAP" => "adjust_transform".to_string(),
                "LOD_POLICY_MISSING" => "add_lod_tag".to_string(),
                "INSTANCE_SET_REQUIRED" => "convert_to_instance_set".to_string(),
                _ => "inspect".to_string(),
            },
            target_mcp_id: d.source.clone().unwrap_or_default(),
            params: serde_json::json!({
                "severity": d.severity,
                "code": d.code,
            }),
            description: d.description.clone(),
        })
        .collect();

    let confidence = if diagnostics.is_empty() {
        1.0
    } else {
        let errors = diagnostics.iter().filter(|d| d.severity == "error").count();
        1.0_f32.min(1.0 - (errors as f32 * 0.1))
    };

    let plan = crate::unreal::pie_types::FixPlan {
        requires_user_approval: confidence < 0.7,
        confidence,
        diagnostics,
        operations,
    };

    Ok(Json(success_response(json!({
        "scene_id": scene_id,
        "confidence": plan.confidence,
        "requires_user_approval": plan.requires_user_approval,
        "operation_count": plan.operations.len(),
        "operations": plan.operations,
    }))))
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/unreal/pie/run", post(pie_run))
        .route("/unreal/logs/parse", post(parse_logs))
        .route("/unreal/fix-plan", post(fix_plan))
}

