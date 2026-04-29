use crate::domain::{SceneEntity, SceneRelation, Vec3};
use crate::layout::span::Span;
use std::collections::HashMap;

pub fn extract_vec3(value: &serde_json::Value, field: &str) -> Option<Vec3> {
    let obj = value.get(field)?;
    Some(Vec3 {
        x: obj.get("x")?.as_f64()?,
        y: obj.get("y")?.as_f64()?,
        z: obj.get("z")?.as_f64()?,
    })
}

pub fn explicit_span(properties: &serde_json::Value) -> Option<Span> {
    Some(Span {
        from: extract_vec3(properties, "from")?,
        to: extract_vec3(properties, "to")?,
    })
}

fn relation_order(relation: &SceneRelation) -> i64 {
    relation
        .properties
        .get("order")
        .and_then(|v| v.as_i64())
        .unwrap_or(0)
}

fn entity_location(entity: &SceneEntity) -> Vec3 {
    compute_location(
        &entity.kind,
        &entity.properties,
        explicit_span(&entity.properties).as_ref(),
    )
}

pub fn relation_span(
    entity: &SceneEntity,
    relations: &[SceneRelation],
    entity_by_id: &HashMap<&str, &SceneEntity>,
) -> Option<Span> {
    let mut endpoints: Vec<(&SceneRelation, Vec3)> = relations
        .iter()
        .filter(|relation| {
            matches!(
                relation.relation_type.as_str(),
                "connected_by" | "connects" | "spans" | "spans_between" | "attached_to"
            ) && (relation.source_entity_id == entity.entity_id
                || relation.target_entity_id == entity.entity_id)
        })
        .filter_map(|relation| {
            let other_id = if relation.source_entity_id == entity.entity_id {
                relation.target_entity_id.as_str()
            } else {
                relation.source_entity_id.as_str()
            };
            let other = entity_by_id.get(other_id)?;
            Some((relation, entity_location(other)))
        })
        .collect();

    endpoints.sort_by_key(|(relation, _)| relation_order(relation));
    if endpoints.len() >= 2 {
        Some(Span {
            from: endpoints[0].1.clone(),
            to: endpoints[1].1.clone(),
        })
    } else {
        None
    }
}

pub fn resolve_span(
    entity: &SceneEntity,
    relations: &[SceneRelation],
    entity_by_id: &HashMap<&str, &SceneEntity>,
) -> Option<Span> {
    explicit_span(&entity.properties).or_else(|| relation_span(entity, relations, entity_by_id))
}

pub fn compute_location(kind: &str, properties: &serde_json::Value, span: Option<&Span>) -> Vec3 {
    if let Some(loc) = extract_vec3(properties, "location") {
        return loc;
    }
    if let Some(span) = span {
        return span.midpoint();
    }
    if let (Some(bbox_min), Some(bbox_max)) = (
        extract_vec3(properties, "bbox_min"),
        extract_vec3(properties, "bbox_max"),
    ) {
        return Vec3 {
            x: (bbox_min.x + bbox_max.x) / 2.0,
            y: (bbox_min.y + bbox_max.y) / 2.0,
            z: (bbox_min.z + bbox_max.z) / 2.0,
        };
    }
    if kind == "ground" || kind == "moat" {
        return Vec3 {
            x: 0.0,
            y: 0.0,
            z: 0.0,
        };
    }
    Vec3 {
        x: 0.0,
        y: 0.0,
        z: 0.0,
    }
}
