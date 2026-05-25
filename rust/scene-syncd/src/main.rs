use axum::http::header;
use axum::http::Method;
use axum::Router;
use scene_syncd::api::common::AppState;
use scene_syncd::db::connect::connect_surreal;
use scene_syncd::db::SurrealSceneRepository;
use scene_syncd::unreal::client::UnrealClient;
use scene_syncd::Config;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;

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

    // React-for-UE v3.0: backfill desired_hash for any pre-v3 scene_component rows.
    match repo.backfill_component_desired_hashes().await {
        Ok(n) => tracing::info!("scene_component backfill completed (rows updated: {})", n),
        Err(e) => tracing::warn!("scene_component backfill failed: {}", e),
    }

    let bind_addr = config.bind_addr();

    let state = AppState {
        db,
        config: config.clone(),
        scene_locks: Arc::new(Mutex::new(HashMap::new())),
        unreal_client: UnrealClient::new(&config),
        procedural_jobs: scene_syncd::procedural::jobs::JobRegistry::new(
            scene_syncd::procedural::jobs::DEFAULT_MAX_CONCURRENCY,
        ),
    };

    let app = Router::new()
        .merge(scene_syncd::api::scene_routes::router())
        .merge(scene_syncd::api::sync_routes::router())
        .merge(scene_syncd::api::semantic_routes::router())
        .merge(scene_syncd::api::layout_routes::router())
        .merge(scene_syncd::api::pie_routes::router())
        .merge(scene_syncd::api::procedural_routes::router())
        .layer(axum::extract::DefaultBodyLimit::max(512 * 1024 * 1024))
        .layer(TraceLayer::new_for_http())
        .layer(
            CorsLayer::new()
                .allow_origin([
                    "http://localhost:3000".parse().unwrap(),
                    "http://127.0.0.1:3000".parse().unwrap(),
                ])
                .allow_methods([Method::GET, Method::POST])
                .allow_headers([header::CONTENT_TYPE]),
        )
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&bind_addr).await?;
    tracing::info!("scene-syncd listening on {}", bind_addr);

    axum::serve(listener, app).await?;

    Ok(())
}
