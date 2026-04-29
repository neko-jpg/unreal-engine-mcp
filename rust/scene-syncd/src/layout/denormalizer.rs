use crate::domain::{SceneEntity, SceneObject, SceneRelation};
use crate::error::AppError;
use crate::layout::kind_registry::KindRegistry;
use crate::layout::scene_object_builder::entity_to_scene_objects;
use std::collections::HashMap;

/// Denormalize a full semantic layout graph into scene objects.
pub fn denormalize_layout(
    scene_id: &str,
    entities: &[SceneEntity],
    relations: &[SceneRelation],
    registry: &KindRegistry,
) -> Result<Vec<SceneObject>, AppError> {
    let entity_by_id: HashMap<&str, &SceneEntity> = entities
        .iter()
        .map(|entity| (entity.entity_id.as_str(), entity))
        .collect();
    let mut objects = Vec::with_capacity(entities.len());
    for entity in entities {
        if entity.deleted {
            continue;
        }
        let mut entity_objects =
            entity_to_scene_objects(scene_id, entity, relations, registry, &entity_by_id)?;
        objects.append(&mut entity_objects);
    }
    Ok(objects)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::layout::kind_registry::KindRegistry;
    use serde_json::json;

    fn make_entity(kind: &str, name: &str, props: serde_json::Value) -> SceneEntity {
        SceneEntity {
            id: String::new(),
            scene: "scene:test".to_string(),
            entity_id: format!("ent_{}", name.to_lowercase().replace(' ', "_")),
            kind: kind.to_string(),
            name: name.to_string(),
            properties: props,
            tags: vec![],
            mcp_ids: vec![],
            metadata: json!({}),
            deleted: false,
            revision: 1,
            created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
            updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        }
    }

    fn make_relation(
        relation_id: &str,
        source: &SceneEntity,
        target: &SceneEntity,
        order: i64,
    ) -> SceneRelation {
        SceneRelation {
            id: String::new(),
            scene: "scene:test".to_string(),
            relation_id: relation_id.to_string(),
            source_entity_id: source.entity_id.clone(),
            target_entity_id: target.entity_id.clone(),
            relation_type: "connected_by".to_string(),
            properties: json!({"order": order}),
            metadata: json!({}),
            created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
            updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        }
    }

    #[test]
    fn denormalize_keep_entity() {
        let registry = KindRegistry::default();
        let entity = make_entity(
            "keep",
            "Main Keep",
            json!({
                "location": {"x": 0.0, "y": 0.0, "z": 1000.0},
                "size": {"x": 8.0, "y": 8.0, "z": 20.0}
            }),
        );
        let obj = crate::layout::scene_object_builder::entity_to_scene_object(
            "castle_001",
            &entity,
            &[],
            &registry,
        )
        .unwrap();
        assert_eq!(obj.mcp_id, "castle_001_ent_main_keep");
        assert_eq!(obj.actor_type, "StaticMeshActor");
        assert_eq!(
            obj.asset_ref,
            json!({"path": "/Engine/BasicShapes/Cube.Cube"})
        );
        assert_eq!(obj.transform.location.z, 2000.0);
        assert_eq!(obj.transform.scale.x, 8.0);
        assert!(obj.tags.contains(&"castle".to_string()));
        assert!(obj.tags.contains(&"keep".to_string()));
        assert!(obj.tags.contains(&"layout_kind:keep".to_string()));
    }

    #[test]
    fn denormalize_curtain_wall_from_to() {
        let registry = KindRegistry::default();
        let entity = make_entity(
            "curtain_wall",
            "North Wall",
            json!({
                "from": {"x": -4500.0, "y": -4500.0, "z": 0.0},
                "to": {"x": 4500.0, "y": -4500.0, "z": 0.0},
                "height": 800.0,
                "thickness": 50.0
            }),
        );
        let obj = crate::layout::scene_object_builder::entity_to_scene_object(
            "castle_001",
            &entity,
            &[],
            &registry,
        )
        .unwrap();
        assert_eq!(obj.transform.location.x, 0.0);
        assert_eq!(obj.transform.location.y, -4500.0);
        assert!(obj.transform.scale.x > 80.0);
        assert_eq!(obj.transform.scale.y, 0.5);
        assert_eq!(obj.transform.scale.z, 8.0);
        assert_eq!(obj.transform.rotation.yaw, 0.0);
    }

    #[test]
    fn curtain_wall_can_resolve_span_from_connected_towers() {
        let registry = KindRegistry::default();
        let west = make_entity(
            "tower",
            "West Tower",
            json!({"location": {"x": -500.0, "y": 0.0, "z": 0.0}}),
        );
        let east = make_entity(
            "tower",
            "East Tower",
            json!({"location": {"x": 500.0, "y": 500.0, "z": 0.0}}),
        );
        let wall = make_entity(
            "curtain_wall",
            "Diagonal Wall",
            json!({"height": 500.0, "thickness": 80.0}),
        );
        let relations = vec![
            make_relation("wall_west", &wall, &west, 0),
            make_relation("wall_east", &wall, &east, 1),
        ];
        let entities = vec![west, east, wall];
        let objects = denormalize_layout("castle_001", &entities, &relations, &registry).unwrap();
        let wall_object = objects
            .iter()
            .find(|obj| obj.tags.contains(&"layout_kind:curtain_wall".to_string()))
            .unwrap();
        assert_eq!(wall_object.transform.location.x, 0.0);
        assert_eq!(wall_object.transform.location.y, 250.0);
        assert!((wall_object.transform.rotation.yaw - 26.565).abs() < 0.01);
    }

    #[test]
    fn curtain_wall_segments_and_crenellations_expand_to_multiple_objects() {
        let registry = KindRegistry::default();
        let wall = make_entity(
            "curtain_wall",
            "North Wall",
            json!({
                "from": {"x": 0.0, "y": 0.0, "z": 0.0},
                "to": {"x": 1000.0, "y": 0.0, "z": 0.0},
                "height": 400.0,
                "thickness": 50.0,
                "segments": 4,
                "crenellations": {"enabled": true, "count": 5}
            }),
        );
        let objects = denormalize_layout("castle_001", &[wall], &[], &registry).unwrap();
        let segments = objects
            .iter()
            .filter(|obj| obj.mcp_id.contains("_seg_"))
            .count();
        let crenellations = objects
            .iter()
            .filter(|obj| obj.tags.contains(&"crenellation".to_string()))
            .count();
        assert_eq!(segments, 4);
        assert_eq!(crenellations, 5);
    }

    #[test]
    fn denormalize_ground_entity() {
        let registry = KindRegistry::default();
        let entity = make_entity("ground", "Castle Ground", json!({}));
        let obj = crate::layout::scene_object_builder::entity_to_scene_object(
            "castle_001",
            &entity,
            &[],
            &registry,
        )
        .unwrap();
        assert_eq!(
            obj.asset_ref,
            json!({"path": "/Engine/BasicShapes/Plane.Plane"})
        );
        assert_eq!(obj.transform.scale.x, 100.0);
    }

    #[test]
    fn unknown_kind_errors() {
        let registry = KindRegistry::default();
        let entity = make_entity("dragon", "Smaug", json!({}));
        assert!(crate::layout::scene_object_builder::entity_to_scene_object(
            "castle_001",
            &entity,
            &[],
            &registry
        )
        .is_err());
    }

    #[test]
    fn denormalize_skips_deleted_entities() {
        let registry = KindRegistry::default();
        let mut entity = make_entity("tower", "NW Tower", json!({}));
        entity.deleted = true;
        let objs = denormalize_layout("castle_001", &[entity], &[], &registry).unwrap();
        assert!(objs.is_empty());
    }

    #[test]
    fn denormalize_moat_entity() {
        let registry = KindRegistry::default();
        let entity = make_entity(
            "moat",
            "Castle Moat",
            json!({
                "width": 12000.0,
                "depth": 12000.0,
            }),
        );
        let obj = crate::layout::scene_object_builder::entity_to_scene_object(
            "castle_001",
            &entity,
            &[],
            &registry,
        )
        .unwrap();
        assert_eq!(obj.actor_type, "StaticMeshActor");
        assert_eq!(
            obj.asset_ref,
            json!({"path": "/Engine/BasicShapes/Plane.Plane"})
        );
        assert_eq!(obj.transform.scale.x, 120.0);
        assert_eq!(obj.transform.scale.y, 120.0);
        assert!(obj.tags.contains(&"moat".to_string()));
        assert!(obj.tags.contains(&"water".to_string()));
    }
}
