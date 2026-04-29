use crate::db::SurrealSceneRepository;
use crate::domain::{SceneAsset, SceneObject};
use crate::error::AppError;
use crate::layout::denormalizer::denormalize_layout;
use crate::layout::kind_registry::KindRegistry;
use serde_json::json;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RealizationStage {
    Blockout,
    AssetBinding,
    DetailPass,
    Finalize,
}

impl RealizationStage {
    pub fn parse(s: &str) -> Result<Self, AppError> {
        match s {
            "blockout" => Ok(RealizationStage::Blockout),
            "assets" | "asset_binding" => Ok(RealizationStage::AssetBinding),
            "detail" | "detail_pass" => Ok(RealizationStage::DetailPass),
            "finalize" => Ok(RealizationStage::Finalize),
            _ => Err(AppError::Validation(format!(
                "unknown realization stage: {s}; expected blockout | assets | detail | finalize"
            ))),
        }
    }
}

/// Apply asset bindings from the scene_asset table to denormalized objects.
fn apply_asset_bindings(objects: &mut [SceneObject], assets: &[SceneAsset]) {
    // Build a lookup: kind -> asset path
    let mut kind_to_asset: std::collections::HashMap<String, String> =
        std::collections::HashMap::new();
    for asset in assets {
        if asset.status == "present" {
            if let Some(path) = asset.variants.get("path").and_then(|v| v.as_str()) {
                kind_to_asset.insert(asset.kind.clone(), path.to_string());
            } else if !asset.fallback.is_empty() {
                kind_to_asset.insert(asset.kind.clone(), asset.fallback.clone());
            }
        }
    }

    for obj in objects.iter_mut() {
        // Extract kind from tags (e.g. "castle", "keep")
        let entity_kind = obj.tags.iter().find_map(|t| match t.as_str() {
            "keep" => Some("keep"),
            "tower" => Some("tower"),
            "wall" => Some("curtain_wall"),
            "gate" => Some("gatehouse"),
            "ground" => Some("ground"),
            "bridge" => Some("bridge"),
            _ => None,
        });

        if let Some(kind) = entity_kind {
            if let Some(asset_path) = kind_to_asset.get(kind) {
                obj.asset_ref = json!({ "path": asset_path });
            }
        }
    }
}

/// Realize a layout at a given stage, producing scene_objects and optionally persisting them.
pub async fn realize_layout(
    repo: &SurrealSceneRepository,
    scene_id: &str,
    stage: RealizationStage,
    persist: bool,
) -> Result<Vec<SceneObject>, AppError> {
    let entities = repo.list_entities(scene_id, None).await?;
    let relations = repo.list_relations(scene_id, None).await?;

    let registry = KindRegistry::default();
    let mut objects = denormalize_layout(scene_id, &entities, &relations, &registry)?;

    match stage {
        RealizationStage::Blockout => {
            // Default cube/plane assets already applied by denormalizer
        }
        RealizationStage::AssetBinding => {
            let assets = repo.list_assets(scene_id, None).await?;
            apply_asset_bindings(&mut objects, &assets);
        }
        RealizationStage::DetailPass => {
            let assets = repo.list_assets(scene_id, None).await?;
            apply_asset_bindings(&mut objects, &assets);
            // Detail pass would apply components/blueprints; placeholder for now
        }
        RealizationStage::Finalize => {
            let assets = repo.list_assets(scene_id, None).await?;
            apply_asset_bindings(&mut objects, &assets);
        }
    }

    if persist {
        for obj in &mut objects {
            let hash =
                crate::domain::transform::compute_desired_hash(obj).map_err(AppError::Internal)?;
            obj.desired_hash = hash;
            repo.upsert_object(obj).await?;
        }
    }

    Ok(objects)
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
    async fn realize_blockout_uses_default_assets() {
        let db = setup_db().await;
        let repo = SurrealSceneRepository::new(db.clone());
        let _ = repo.ensure_schema().await;

        let scene_id = format!("realize_test_{}", ulid::Ulid::new());
        let _ = repo.upsert_scene(&scene_id, "Realize Test", None).await;

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
            .unwrap();

        let objects = realize_layout(&repo, &scene_id, RealizationStage::Blockout, false)
            .await
            .unwrap();
        assert_eq!(objects.len(), 1);
        assert_eq!(
            objects[0].asset_ref,
            json!({"path": "/Engine/BasicShapes/Cube.Cube"})
        );
    }

    #[tokio::test]
    async fn realize_asset_binding_uses_scene_assets() {
        let db = setup_db().await;
        let repo = SurrealSceneRepository::new(db.clone());
        let _ = repo.ensure_schema().await;

        let scene_id = format!("realize_test_{}", ulid::Ulid::new());
        let _ = repo.upsert_scene(&scene_id, "Realize Test", None).await;

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
            .unwrap();

        // Register a custom asset for "keep"
        let _ = repo
            .upsert_asset(
                &scene_id,
                "keep_stone_01",
                "keep",
                "present",
                "/Game/Architecture/Keep_Stone_01.Keep_Stone_01",
                vec!["stone".to_string()],
                "high",
                json!({}),
                json!({}),
            )
            .await
            .unwrap();

        let objects = realize_layout(&repo, &scene_id, RealizationStage::AssetBinding, false)
            .await
            .unwrap();
        assert_eq!(objects.len(), 1);
        assert_eq!(
            objects[0].asset_ref,
            json!({"path": "/Game/Architecture/Keep_Stone_01.Keep_Stone_01"})
        );
    }
}
