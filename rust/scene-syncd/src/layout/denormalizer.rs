use crate::domain::{Rotator, SceneEntity, SceneObject, SceneRelation, Transform, Vec3};
use crate::error::AppError;
use serde_json::json;
use std::collections::HashMap;

/// Default actor specification for a semantic layout entity kind.
#[derive(Debug, Clone)]
pub struct KindSpec {
    pub actor_type: &'static str,
    pub asset_path: &'static str,
    pub default_tags: Vec<&'static str>,
    pub draft_color: [f64; 4],
}

/// Registry mapping entity kinds to their default realization specifications.
pub struct KindRegistry {
    map: HashMap<String, KindSpec>,
}

impl Default for KindRegistry {
    fn default() -> Self {
        let mut map = HashMap::new();
        map.insert(
            "keep".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Cube.Cube",
                default_tags: vec!["castle", "keep"],
                draft_color: [0.65, 0.78, 1.0, 0.35],
            },
        );
        map.insert(
            "curtain_wall".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Cube.Cube",
                default_tags: vec!["castle", "wall"],
                draft_color: [0.55, 0.72, 1.0, 0.3],
            },
        );
        map.insert(
            "tower".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Cube.Cube",
                default_tags: vec!["castle", "tower"],
                draft_color: [0.8, 0.68, 1.0, 0.34],
            },
        );
        map.insert(
            "gatehouse".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Cube.Cube",
                default_tags: vec!["castle", "gate"],
                draft_color: [1.0, 0.78, 0.45, 0.36],
            },
        );
        map.insert(
            "ground".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Plane.Plane",
                default_tags: vec!["castle", "ground"],
                draft_color: [0.42, 0.7, 0.5, 0.22],
            },
        );
        map.insert(
            "bridge".to_string(),
            KindSpec {
                actor_type: "StaticMeshActor",
                asset_path: "/Engine/BasicShapes/Cube.Cube",
                default_tags: vec!["castle", "bridge"],
                draft_color: [0.74, 0.84, 0.92, 0.32],
            },
        );
        Self { map }
    }
}

impl KindRegistry {
    pub fn get(&self, kind: &str) -> Option<&KindSpec> {
        self.map.get(kind)
    }
}

#[derive(Debug, Clone)]
struct Span {
    from: Vec3,
    to: Vec3,
}

impl Span {
    fn midpoint(&self) -> Vec3 {
        Vec3 {
            x: (self.from.x + self.to.x) / 2.0,
            y: (self.from.y + self.to.y) / 2.0,
            z: (self.from.z + self.to.z) / 2.0,
        }
    }

    fn length(&self) -> f64 {
        let dx = self.to.x - self.from.x;
        let dy = self.to.y - self.from.y;
        let dz = self.to.z - self.from.z;
        (dx * dx + dy * dy + dz * dz).sqrt()
    }

    fn yaw_degrees(&self) -> f64 {
        (self.to.y - self.from.y)
            .atan2(self.to.x - self.from.x)
            .to_degrees()
    }

    fn point_at(&self, t: f64) -> Vec3 {
        Vec3 {
            x: self.from.x + (self.to.x - self.from.x) * t,
            y: self.from.y + (self.to.y - self.from.y) * t,
            z: self.from.z + (self.to.z - self.from.z) * t,
        }
    }

    fn segment(&self, index: usize, count: usize) -> Span {
        Span {
            from: self.point_at(index as f64 / count as f64),
            to: self.point_at((index + 1) as f64 / count as f64),
        }
    }
}

fn extract_vec3(value: &serde_json::Value, field: &str) -> Option<Vec3> {
    let obj = value.get(field)?;
    Some(Vec3 {
        x: obj.get("x")?.as_f64()?,
        y: obj.get("y")?.as_f64()?,
        z: obj.get("z")?.as_f64()?,
    })
}

fn explicit_span(properties: &serde_json::Value) -> Option<Span> {
    Some(Span {
        from: extract_vec3(properties, "from")?,
        to: extract_vec3(properties, "to")?,
    })
}

fn compute_location(kind: &str, properties: &serde_json::Value, span: Option<&Span>) -> Vec3 {
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
    if kind == "ground" {
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

fn compute_rotation(properties: &serde_json::Value, span: Option<&Span>) -> Rotator {
    if let Some(rot) = properties.get("rotation") {
        return Rotator {
            pitch: rot.get("pitch").and_then(|v| v.as_f64()).unwrap_or(0.0),
            yaw: rot.get("yaw").and_then(|v| v.as_f64()).unwrap_or(0.0),
            roll: rot.get("roll").and_then(|v| v.as_f64()).unwrap_or(0.0),
        };
    }
    if let Some(span) = span {
        return Rotator {
            pitch: 0.0,
            yaw: span.yaw_degrees(),
            roll: 0.0,
        };
    }
    Rotator {
        pitch: 0.0,
        yaw: 0.0,
        roll: 0.0,
    }
}

fn compute_scale(kind: &str, properties: &serde_json::Value, span: Option<&Span>) -> Vec3 {
    match kind {
        "ground" => Vec3 {
            x: properties
                .get("width")
                .and_then(|v| v.as_f64())
                .unwrap_or(10000.0)
                / 100.0,
            y: properties
                .get("depth")
                .and_then(|v| v.as_f64())
                .unwrap_or(10000.0)
                / 100.0,
            z: 1.0,
        },
        "curtain_wall" => {
            let height = properties
                .get("height")
                .and_then(|v| v.as_f64())
                .unwrap_or(400.0);
            let thickness = properties
                .get("thickness")
                .and_then(|v| v.as_f64())
                .unwrap_or(50.0);
            if let Some(span) = span {
                Vec3 {
                    x: span.length() / 100.0,
                    y: thickness / 100.0,
                    z: height / 100.0,
                }
            } else {
                Vec3 {
                    x: 10.0,
                    y: thickness / 100.0,
                    z: height / 100.0,
                }
            }
        }
        "bridge" => {
            let width = properties
                .get("width")
                .and_then(|v| v.as_f64())
                .unwrap_or(400.0);
            let height = properties
                .get("height")
                .and_then(|v| v.as_f64())
                .unwrap_or(20.0);
            if let Some(span) = span {
                Vec3 {
                    x: span.length() / 100.0,
                    y: width / 100.0,
                    z: height / 100.0,
                }
            } else {
                Vec3 {
                    x: 10.0,
                    y: width / 100.0,
                    z: height / 100.0,
                }
            }
        }
        _ => {
            if let Some(size) = extract_vec3(properties, "size") {
                size
            } else if let (Some(w), Some(h), Some(d)) = (
                properties.get("width").and_then(|v| v.as_f64()),
                properties.get("height").and_then(|v| v.as_f64()),
                properties.get("depth").and_then(|v| v.as_f64()),
            ) {
                Vec3 {
                    x: w / 100.0,
                    y: d / 100.0,
                    z: h / 100.0,
                }
            } else {
                Vec3 {
                    x: 1.0,
                    y: 1.0,
                    z: 1.0,
                }
            }
        }
    }
}

fn entity_location(entity: &SceneEntity) -> Vec3 {
    compute_location(
        &entity.kind,
        &entity.properties,
        explicit_span(&entity.properties).as_ref(),
    )
}

fn relation_order(relation: &SceneRelation) -> i64 {
    relation
        .properties
        .get("order")
        .and_then(|v| v.as_i64())
        .unwrap_or(0)
}

fn relation_span(
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

fn resolve_span(
    entity: &SceneEntity,
    relations: &[SceneRelation],
    entity_by_id: &HashMap<&str, &SceneEntity>,
) -> Option<Span> {
    explicit_span(&entity.properties).or_else(|| relation_span(entity, relations, entity_by_id))
}

fn build_mcp_id(scene_id: &str, entity: &SceneEntity) -> String {
    if let Some(first) = entity.mcp_ids.first() {
        return first.clone();
    }
    format!("{}_{}", scene_id, entity.entity_id)
}

fn make_transform(kind: &str, properties: &serde_json::Value, span: Option<&Span>) -> Transform {
    Transform {
        location: compute_location(kind, properties, span),
        rotation: compute_rotation(properties, span),
        scale: compute_scale(kind, properties, span),
    }
}

fn build_scene_object(
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

fn should_generate_crenellations(entity: &SceneEntity) -> bool {
    entity
        .properties
        .get("crenellations")
        .and_then(|v| {
            if let Some(enabled) = v.as_bool() {
                Some(enabled)
            } else {
                v.get("enabled").and_then(|enabled| enabled.as_bool())
            }
        })
        .unwrap_or(false)
}

fn crenellation_count(properties: &serde_json::Value, span: &Span) -> usize {
    if let Some(count) = properties
        .get("crenellations")
        .and_then(|v| v.get("count"))
        .and_then(|v| v.as_u64())
    {
        return count.clamp(1, 512) as usize;
    }
    let spacing = properties
        .get("crenellations")
        .and_then(|v| v.get("spacing"))
        .and_then(|v| v.as_f64())
        .unwrap_or(300.0);
    if spacing <= 0.0 {
        return 1;
    }
    (span.length() / spacing).floor().max(1.0).min(512.0) as usize
}

fn crenellation_scale(properties: &serde_json::Value) -> Vec3 {
    if let Some(size) = properties
        .get("crenellations")
        .and_then(|v| v.get("size"))
        .and_then(|v| {
            Some(Vec3 {
                x: v.get("x")?.as_f64()?,
                y: v.get("y")?.as_f64()?,
                z: v.get("z")?.as_f64()?,
            })
        })
    {
        return size;
    }
    Vec3 {
        x: 0.6,
        y: properties
            .get("thickness")
            .and_then(|v| v.as_f64())
            .unwrap_or(50.0)
            / 100.0,
        z: 0.8,
    }
}

fn generate_crenellations(
    scene_id: &str,
    entity: &SceneEntity,
    spec: &KindSpec,
    base_mcp_id: &str,
    span: &Span,
) -> Result<Vec<SceneObject>, AppError> {
    if entity.kind != "curtain_wall" || !should_generate_crenellations(entity) {
        return Ok(vec![]);
    }

    let count = crenellation_count(&entity.properties, span);
    let height = entity
        .properties
        .get("height")
        .and_then(|v| v.as_f64())
        .unwrap_or(400.0);
    let scale = crenellation_scale(&entity.properties);
    let mut objects = Vec::with_capacity(count);

    for i in 0..count {
        let mut location = span.point_at((i as f64 + 0.5) / count as f64);
        location.z += height + (scale.z * 50.0);
        let transform = Transform {
            location,
            rotation: Rotator {
                pitch: 0.0,
                yaw: span.yaw_degrees(),
                roll: 0.0,
            },
            scale: scale.clone(),
        };
        let mut object = build_scene_object(
            scene_id,
            entity,
            spec,
            format!("{base_mcp_id}_crenel_{:03}", i + 1),
            format!("{} Crenellation {:03}", entity.name, i + 1),
            transform,
            "crenellation",
        )?;
        for tag in ["crenellation", "detail"] {
            if !object.tags.contains(&tag.to_string()) {
                object.tags.push(tag.to_string());
            }
        }
        object.visual["draft"]["proxy_group"] = json!("crenellation");
        objects.push(object);
    }

    Ok(objects)
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
                make_transform(&entity.kind, &entity.properties, Some(&segment)),
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
            make_transform(&entity.kind, &entity.properties, span.as_ref()),
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
        let obj = entity_to_scene_object("castle_001", &entity, &[], &registry).unwrap();
        assert_eq!(obj.mcp_id, "castle_001_ent_main_keep");
        assert_eq!(obj.actor_type, "StaticMeshActor");
        assert_eq!(
            obj.asset_ref,
            json!({"path": "/Engine/BasicShapes/Cube.Cube"})
        );
        assert_eq!(obj.transform.location.z, 1000.0);
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
        let obj = entity_to_scene_object("castle_001", &entity, &[], &registry).unwrap();
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
        let obj = entity_to_scene_object("castle_001", &entity, &[], &registry).unwrap();
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
        assert!(entity_to_scene_object("castle_001", &entity, &[], &registry).is_err());
    }

    #[test]
    fn denormalize_skips_deleted_entities() {
        let registry = KindRegistry::default();
        let mut entity = make_entity("tower", "NW Tower", json!({}));
        entity.deleted = true;
        let objs = denormalize_layout("castle_001", &[entity], &[], &registry).unwrap();
        assert!(objs.is_empty());
    }
}
