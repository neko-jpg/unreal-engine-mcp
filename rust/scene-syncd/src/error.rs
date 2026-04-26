use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Database error: {0}")]
    Database(String),

    #[error("Unreal bridge error: {0}")]
    UnrealBridge(String),

    #[error("Scene syncd unavailable: {0}")]
    #[allow(dead_code)]
    Unavailable(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Conflict: {0}")]
    #[allow(dead_code)]
    Conflict(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, code) = match &self {
            AppError::Validation(_) => (axum::http::StatusCode::BAD_REQUEST, "validation_error"),
            AppError::NotFound(_) => (axum::http::StatusCode::NOT_FOUND, "not_found"),
            AppError::Conflict(_) => (axum::http::StatusCode::CONFLICT, "conflict"),
            AppError::Unavailable(_) => {
                (axum::http::StatusCode::SERVICE_UNAVAILABLE, "unavailable")
            }
            AppError::UnrealBridge(_) => {
                (axum::http::StatusCode::BAD_GATEWAY, "unreal_bridge_error")
            }
            AppError::Database(_) => (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                "database_error",
            ),
            AppError::Internal(_) => (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                "internal_error",
            ),
        };

        let body = serde_json::json!({
            "success": false,
            "data": null,
            "warnings": [],
            "error": {
                "code": code,
                "message": self.to_string(),
            }
        });

        (status, axum::Json(body)).into_response()
    }
}

impl From<surrealdb::Error> for AppError {
    fn from(err: surrealdb::Error) -> Self {
        AppError::Database(err.to_string())
    }
}
