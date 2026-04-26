use crate::config::Config;
use crate::error::AppError;
use surrealdb::engine::any::Any;
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;

pub async fn connect_surreal(config: &Config) -> Result<Surreal<Any>, AppError> {
    let db: Surreal<Any> = Surreal::init();

    db.connect(&config.surreal_url)
        .await
        .map_err(|e| AppError::Database(format!("surrealdb connect error: {e}")))?;

    db.signin(Root {
        username: &config.surreal_user,
        password: &config.surreal_pass,
    })
    .await
    .map_err(|e| AppError::Database(format!("surrealdb signin error: {e}")))?;

    db.use_ns(&config.surreal_ns)
        .use_db(&config.surreal_db)
        .await
        .map_err(|e| AppError::Database(format!("surrealdb use_ns/use_db error: {e}")))?;

    tracing::info!(
        "Connected to SurrealDB at {} (ns: {}, db: {})",
        config.surreal_url,
        config.surreal_ns,
        config.surreal_db
    );

    Ok(db)
}
