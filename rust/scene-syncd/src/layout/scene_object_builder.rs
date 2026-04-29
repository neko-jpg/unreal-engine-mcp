use crate::domain::{SceneEntity, SceneObject, SceneRelation, Transform};
use crate::error::AppError;
use crate::layout::crenellations::generate_crenellations;
use crate::layout::entity_resolver::resolve_span;
use crate::layout::kind_registry::KindRegistry;
use crate::layout::kind_registry::KindSpec;
use crate::layout::span::Span;
use crate::layout::transform::make_transform;
use serde_json::json;
use std::collections::HashMap;

pub fn build_mcp_id(scene_id: &str, entity: &SceneEntity) -> String {
    if let Some(first) = entity.mcp_ids.first() {
        return first.clone();
    }
    format!("{}_{}", scene_id, entity.entity_id)
}

pub fn build_scene_object(
    scene_id: &str,
    entity: &SceneEntity,
    spec: &KindSpec,
    mcp_id: String,
    desired_name: String,
    transform: Transform,
    generated_part: &str,
) -> Result<SceneObject, AppError> {
    let mut tags = entity.tags.clone();
    for tag in &spec.default_tags {
        if !tags.contains(&tag.to_string()) {
            tags.push(tag.to_string());
        }
    }
    for tag in [
        "managed_by_mcp".to_string(),
        format!("mcp_id:{mcp_id}"),
        format!("layout_kind:{}", entity.kind),
        format!("layout_entity:{}", entity.entity_id),
    ] {
        if !tags.contains(&tag) {
            tags.push(tag);
        }
    }

    let mut metadata = entity.metadata.clone();
    metadata["semantic_layout"] = json!({
        "source_entity_id": entity.entity_id,
        "source_entity_kind": entity.kind,
        "generated_part": generated_part,
    });

    Ok(SceneObject {
        id: format!("scene_object:{scene_id}:{mcp_id}"),
        scene: format!("scene:{scene_id}"),
        group: None,
        mcp_id,
        desired_name,
        unreal_actor_name: None,
        actor_type: spec.actor_type.to_string(),
        asset_ref: json!({ "path": spec.asset_path }),
        transform,
        visual: json!({
            "draft": {
                "proxy_group": entity.kind,
                "color": spec.draft_color,
            }
        }),
        physics: json!({}),
        tags,
        metadata,
        desired_hash: String::new(),
        last_applied_hash: None,
        sync_status: "pending".to_string(),
        deleted: false,
        revision: 1,
        created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
    })
}

fn segment_count(properties: &serde_json::Value, span: Option<&Span>) -> usize {
    if let Some(count) = properties.get("segments").and_then(|v| v.as_u64()) {
        return count.clamp(1, 512) as usize;
    }
    let Some(segment_length) = properties.get("segment_length").and_then(|v| v.as_f64()) else {
        return 1;
    };
    let Some(span) = span else {
        return 1;
    };
    if segment_length <= 0.0 {
        return 1;
    }
    ((span.length() / segment_length).ceil() as usize).clamp(1, 512)
}

/// Convert a single semantic entity into one or more scene objects.
pub fn entity_to_scene_objects(
    scene_id: &str,
    entity: &SceneEntity,
    relations: &[SceneRelation],
    registry: &KindRegistry,
    entity_by_id: &HashMap<&str, &SceneEntity>,
) -> Result<Vec<SceneObject>, AppError> {
    let spec = registry
        .get(&entity.kind)
        .ok_or_else(|| AppError::Validation(format!("unknown entity kind: {}", entity.kind)))?;

    let base_mcp_id = build_mcp_id(scene_id, entity);
    let span = resolve_span(entity, relations, entity_by_id);
    let count = if matches!(entity.kind.as_str(), "curtain_wall" | "bridge") {
        segment_count(&entity.properties, span.as_ref())
    } else {
        1
    };

    let mut objects = Vec::new();
    if count > 1 {
        let span = span.as_ref().ok_or_else(|| {
            AppError::Validation(format!(
                "{} requires from/to or connected relations to segment",
                entity.entity_id
            ))
        })?;
        for index in 0..count {
            let segment = span.segment(index, count);
            objects.push(build_scene_object(
                scene_id,
                entity,
                spec,
                format!("{base_mcp_id}_seg_{:03}", index + 1),
                format!("{} Segment {:03}", entity.name, index + 1),
                make_transform(&entity.kind, &entity.properties, Some(&segment), registry),
                "segment",
            )?);
        }
    } else {
        objects.push(build_scene_object(
            scene_id,
            entity,
            spec,
            base_mcp_id.clone(),
            entity.name.clone(),
            make_transform(&entity.kind, &entity.properties, span.as_ref(), registry),
            "primary",
        )?);
    }

    if let Some(span) = span.as_ref() {
        objects.extend(generate_crenellations(
            scene_id,
            entity,
            spec,
            &base_mcp_id,
            span,
        )?);
    }

    Ok(objects)
}

/// Convert a single entity into its primary scene object.
pub fn entity_to_scene_object(
    scene_id: &str,
    entity: &SceneEntity,
    relations: &[SceneRelation],
    registry: &KindRegistry,
) -> Result<SceneObject, AppError> {
    let entity_by_id = HashMap::from([(entity.entity_id.as_str(), entity)]);
    entity_to_scene_objects(scene_id, entity, relations, registry, &entity_by_id)?
        .into_iter()
        .next()
        .ok_or_else(|| AppError::Internal("entity produced no scene objects".to_string()))
}
