use crate::domain::SceneObject;
use serde::{Deserialize, Serialize};

/// A set of repeated geometric instances sharing the same mesh/material.
/// Maps to Unreal ISM/HISM components for efficient rendering of repeated primitives
/// (crenellations, wall stones, floor tiles, road curbs, fences, windows, props).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InstanceSet {
    pub set_id: String,
    pub mesh: String,
    pub material: Option<String>,
    pub transforms: Vec<crate::domain::Transform>,
    pub custom_data: serde_json::Value,
    pub tags: Vec<String>,
    /// World Partition cell this instance set belongs to (if any).
    pub cell_id: Option<String>,
    /// LOD policy for this instance set.
    pub lod_policy: String,
}

/// Command to spawn or update an instance set in Unreal.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InstanceSetCommand {
    pub set_id: String,
    pub mesh: String,
    pub material: Option<String>,
    pub transforms: Vec<serde_json::Value>,
    pub cell_id: Option<String>,
}

impl InstanceSetCommand {
    pub fn from_instance_set(set: &InstanceSet) -> Self {
        let transforms: Vec<serde_json::Value> = set
            .transforms
            .iter()
            .map(|t| {
                serde_json::json!({
                    "location": [t.location.x, t.location.y, t.location.z],
                    "rotation": [t.rotation.pitch, t.rotation.yaw, t.rotation.roll],
                    "scale": [t.scale.x, t.scale.y, t.scale.z],
                })
            })
            .collect();
        Self {
            set_id: set.set_id.clone(),
            mesh: set.mesh.clone(),
            material: set.material.clone(),
            transforms,
            cell_id: set.cell_id.clone(),
        }
    }
}

/// Group objects by (mesh, material, tags) to produce instance sets.
/// Objects with actor_type StaticMeshActor and matching asset_ref are candidates.
pub fn group_into_instance_sets(objects: &[SceneObject]) -> Vec<InstanceSet> {
    use std::collections::HashMap;

    let mut groups: HashMap<(String, Option<String>, String), Vec<crate::domain::Transform>> =
        HashMap::new();

    for obj in objects {
        if obj.deleted {
            continue;
        }
        // Only StaticMeshActor with a mesh asset path is a candidate.
        let mesh = obj
            .asset_ref
            .get("mesh")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        if mesh.is_empty() {
            continue;
        }
        let material = obj
            .asset_ref
            .get("material")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());
        // Group key: mesh + material + kind (from tags)
        let kind = obj
            .tags
            .iter()
            .find_map(|t| t.strip_prefix("layout_kind:"))
            .unwrap_or("unknown")
            .to_string();
        let key = (mesh, material, kind);
        groups.entry(key).or_default().push(obj.transform.clone());
    }

    let mut result = Vec::new();
    for ((mesh, material, kind), transforms) in groups {
        let set_id = format!("{}_{}_instances", kind, mesh.replace('/', "_"));
        result.push(InstanceSet {
            set_id,
            mesh,
            material,
            transforms,
            custom_data: serde_json::json!({}),
            tags: vec![format!("layout_kind:{}", kind)],
            cell_id: None,
            lod_policy: "default".to_string(),
        });
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Rotator, Transform, Vec3};
    use serde_json::json;

    fn make_instance_object(mcp_id: &str, mesh: &str, x: f64) -> SceneObject {
        SceneObject {
            id: String::new(),
            scene: "scene:test".to_string(),
            group: None,
            mcp_id: mcp_id.to_string(),
            desired_name: mcp_id.to_string(),
            unreal_actor_name: None,
            actor_type: "StaticMeshActor".to_string(),
            asset_ref: json!({"mesh": mesh}),
            transform: Transform {
                location: Vec3 { x, y: 0.0, z: 0.0 },
                rotation: Rotator {
                    pitch: 0.0,
                    yaw: 0.0,
                    roll: 0.0,
                },
                scale: Vec3 {
                    x: 1.0,
                    y: 1.0,
                    z: 1.0,
                },
            },
            visual: json!({}),
            physics: json!({}),
            tags: vec!["layout_kind:crenellation".to_string()],
            metadata: json!({}),
            desired_hash: String::new(),
            last_applied_hash: None,
            sync_status: "pending".to_string(),
            deleted: false,
            revision: 1,
            created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
            updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        }
    }

    #[test]
    fn groups_same_mesh_into_one_set() {
        let objs = vec![
            make_instance_object("a", "/Engine/BasicShapes/Cube", 0.0),
            make_instance_object("b", "/Engine/BasicShapes/Cube", 100.0),
        ];
        let sets = group_into_instance_sets(&objs);
        assert_eq!(sets.len(), 1);
        assert_eq!(sets[0].transforms.len(), 2);
    }

    #[test]
    fn empty_for_no_mesh() {
        let mut obj = make_instance_object("a", "", 0.0);
        obj.asset_ref = json!({});
        let sets = group_into_instance_sets(&[obj]);
        assert!(sets.is_empty());
    }

    #[test]
    fn skips_deleted_objects() {
        let mut obj = make_instance_object("a", "/Engine/BasicShapes/Cube", 0.0);
        obj.deleted = true;
        let sets = group_into_instance_sets(&[obj]);
        assert!(sets.is_empty());
    }

    #[test]
    fn command_from_instance_set_has_transforms() {
        let objs = vec![make_instance_object("a", "/Engine/BasicShapes/Cube", 50.0)];
        let sets = group_into_instance_sets(&objs);
        let cmd = InstanceSetCommand::from_instance_set(&sets[0]);
        assert_eq!(cmd.transforms.len(), 1);
        assert!(cmd.transforms[0].get("location").is_some());
    }
}
