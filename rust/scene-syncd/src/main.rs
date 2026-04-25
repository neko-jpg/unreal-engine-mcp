mod api;
mod config;
mod db;
mod domain;
mod error;
mod sync;
mod unreal;

use axum::routing::{get, post};
use axum::Router;
use config::Config;
use db::connect::connect_surreal;
use db::SurrealSceneRepository;
use tower_http::trace::TraceLayer;
use tower_http::cors::CorsLayer;

use api::routes::AppState;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env();

    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(&config.log_level)),
        )
        .json()
        .init();

    tracing::info!("scene-syncd starting on {}", config.bind_addr());

    let db = connect_surreal(&config).await?;
    let repo = SurrealSceneRepository::new(db.clone());

    tracing::info!("Applying schema migrations...");
    repo.ensure_schema().await?;
    tracing::info!("Schema migrations applied");

    tracing::info!("Ensuring default scene:main...");
    repo.ensure_default_scene().await?;
    tracing::info!("Default scene:main ready");

    let bind_addr = config.bind_addr();

    let state = AppState {
        db,
        config,
    };

    let app = Router::new()
        .route("/health", get(api::routes::health))
        .route("/scenes/create", post(api::routes::create_scene))
        .route("/objects/upsert", post(api::routes::upsert_object))
        .route("/objects/bulk-upsert", post(api::routes::bulk_upsert_objects))
        .route("/objects/list", post(api::routes::list_objects))
        .route("/objects/delete", post(api::routes::delete_object))
        .route("/sync/plan", post(api::routes::plan_sync_route))
        .route("/sync/apply", post(api::routes::apply_sync_route))
        .layer(TraceLayer::new_for_http())
        .layer(CorsLayer::permissive())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&bind_addr).await?;
    tracing::info!("scene-syncd listening on {}", bind_addr);

    axum::serve(listener, app).await?;

    Ok(())
}