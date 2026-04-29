use crate::db::SurrealSceneRepository;
use crate::domain::SceneObject;
use crate::error::AppError;
use crate::layout::denormalizer::denormalize_layout;
use crate::layout::kind_registry::KindRegistry;

/// Preview a layout by denormalizing entities into scene_objects without persisting them.
pub async fn preview_layout(
    repo: &SurrealSceneRepository,
    scene_id: &str,
) -> Result<Vec<SceneObject>, AppError> {
    let entities = repo.list_entities(scene_id, None).await?;
    let relations = repo.list_relations(scene_id, None).await?;
    let registry = KindRegistry::default();
    denormalize_layout(scene_id, &entities, &relations, &registry)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::SurrealSceneRepository;
    use serde_json::json;
    use surrealdb::engine::any::Any;
    use surrealdb::Surreal;

    async fn setup_db() -> Surreal<Any> {
        let db: Surreal<Any> = Surreal::init();
        db.connect("memory").await.unwrap();
        db.use_ns("test").use_db("test").await.unwrap();
        db
    }

    #[tokio::test]
    async fn preview_layout_returns_objects_without_persisting() {
        let db = setup_db().await;
        let repo = SurrealSceneRepository::new(db.clone());
        let _ = repo.ensure_schema().await;

        let scene_id = format!("preview_test_{}", ulid::Ulid::new());
        let _ = repo.upsert_scene(&scene_id, "Preview Test", None).await;

        // Insert a test entity
        let _ = repo
            .upsert_entity(
                &scene_id,
                "keep_main",
                "keep",
                "Main Keep",
                json!({"location": {"x": 0.0, "y": 0.0, "z": 100.0}}),
                vec![],
                vec![],
                json!({}),
            )
            .await
            .expect("upsert entity");

        let preview = preview_layout(&repo, &scene_id).await.expect("preview");
        assert_eq!(preview.len(), 1);
        assert_eq!(preview[0].mcp_id, format!("{}_keep_main", scene_id));
        assert_eq!(preview[0].actor_type, "StaticMeshActor");

        // Verify no objects were persisted
        let persisted = repo
            .list_desired_objects(&scene_id, false, None, None)
            .await
            .expect("list");
        assert!(persisted.is_empty());
    }
}
