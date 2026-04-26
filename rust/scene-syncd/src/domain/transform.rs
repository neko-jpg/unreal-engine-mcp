use crate::domain::SceneObject;
use sha2::{Digest, Sha256};

#[derive(serde::Serialize)]
struct DesiredHashPayload {
    actor_type: String,
    asset_ref: serde_json::Value,
    transform: TransformPayload,
    tags: Vec<String>,
}

#[derive(serde::Serialize)]
struct TransformPayload {
    location: [f64; 3],
    rotation: [f64; 3],
    scale: [f64; 3],
}

/// Compute a hash of the fields the sync applier can apply.
/// Includes actor_type, asset_ref, transform, and tags so that
/// changes to any of these fields produce a plan operation.
pub fn compute_desired_hash(obj: &SceneObject) -> Result<String, String> {
    let mut sorted_tags = obj.tags.clone();
    sorted_tags.sort();

    let payload = DesiredHashPayload {
        actor_type: obj.actor_type.clone(),
        asset_ref: obj.asset_ref.clone(),
        transform: TransformPayload {
            location: [
                obj.transform.location.x,
                obj.transform.location.y,
                obj.transform.location.z,
            ],
            rotation: [
                obj.transform.rotation.pitch,
                obj.transform.rotation.yaw,
                obj.transform.rotation.roll,
            ],
            scale: [
                obj.transform.scale.x,
                obj.transform.scale.y,
                obj.transform.scale.z,
            ],
        },
        tags: sorted_tags,
    };

    let bytes =
        serde_json::to_vec(&payload).map_err(|e| format!("hash serialization error: {e}"))?;
    let digest = Sha256::digest(&bytes);
    Ok(format!("{:x}", digest))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Rotator, SceneObject, Transform, Vec3};
    use surrealdb::sql::Datetime;

    fn make_obj() -> SceneObject {
        SceneObject {
            id: String::new(),
            scene: "scene:main".to_string(),
            group: None,
            mcp_id: "test_001".to_string(),
            desired_name: "TestObj".to_string(),
            unreal_actor_name: None,
            actor_type: "StaticMeshActor".to_string(),
            asset_ref: serde_json::json!({"path": "/Engine/BasicShapes/Cube.Cube"}),
            transform: Transform {
                location: Vec3 {
                    x: 100.0,
                    y: 200.0,
                    z: 300.0,
                },
                rotation: Rotator {
                    pitch: 0.0,
                    yaw: 90.0,
                    roll: 0.0,
                },
                scale: Vec3 {
                    x: 1.0,
                    y: 1.0,
                    z: 1.0,
                },
            },
            visual: serde_json::json!({}),
            physics: serde_json::json!({}),
            tags: vec!["wall".to_string()],
            metadata: serde_json::json!({}),
            desired_hash: String::new(),
            last_applied_hash: None,
            sync_status: "pending".to_string(),
            deleted: false,
            revision: 1,
            created_at: Datetime::from(chrono::Utc::now()),
            updated_at: Datetime::from(chrono::Utc::now()),
        }
    }

    #[test]
    fn hash_stability_same_object_same_hash() {
        let obj = make_obj();
        let h1 = compute_desired_hash(&obj).unwrap();
        let h2 = compute_desired_hash(&obj).unwrap();
        assert_eq!(h1, h2);
    }

    #[test]
    fn hash_changes_on_transform() {
        let mut obj1 = make_obj();
        let h1 = compute_desired_hash(&obj1).unwrap();
        obj1.transform.location.x = 999.0;
        let h2 = compute_desired_hash(&obj1).unwrap();
        assert_ne!(h1, h2);
    }

    #[test]
    fn hash_changes_on_asset_ref() {
        let mut obj1 = make_obj();
        let h1 = compute_desired_hash(&obj1).unwrap();
        obj1.asset_ref = serde_json::json!({"path": "/Engine/BasicShapes/Sphere.Sphere"});
        let h2 = compute_desired_hash(&obj1).unwrap();
        assert_ne!(h1, h2);
    }

    #[test]
    fn hash_changes_on_tags() {
        let mut obj1 = make_obj();
        let h1 = compute_desired_hash(&obj1).unwrap();
        obj1.tags.push("pyramid".to_string());
        let h2 = compute_desired_hash(&obj1).unwrap();
        assert_ne!(h1, h2);
    }

    #[test]
    fn hash_tag_order_independent() {
        let mut obj1 = make_obj();
        obj1.tags = vec!["b".to_string(), "a".to_string()];
        let h1 = compute_desired_hash(&obj1).unwrap();
        obj1.tags = vec!["a".to_string(), "b".to_string()];
        let h2 = compute_desired_hash(&obj1).unwrap();
        assert_eq!(h1, h2, "hash should be independent of tag order");
    }

    #[test]
    fn hash_excludes_timestamps() {
        let mut obj1 = make_obj();
        let h1 = compute_desired_hash(&obj1).unwrap();
        // Changing timestamps should not change the hash
        obj1.updated_at = Datetime::from(chrono::Utc::now() + chrono::Duration::hours(1));
        let h2 = compute_desired_hash(&obj1).unwrap();
        assert_eq!(h1, h2, "hash should not change when only timestamps change");
    }

    #[test]
    fn validate_mcp_id_rejects_empty() {
        use crate::domain::ids::validate_mcp_id;
        assert!(validate_mcp_id("").is_err());
    }

    #[test]
    fn validate_mcp_id_rejects_spaces() {
        use crate::domain::ids::validate_mcp_id;
        assert!(validate_mcp_id("has space").is_err());
    }

    #[test]
    fn validate_mcp_id_rejects_slashes() {
        use crate::domain::ids::validate_mcp_id;
        assert!(validate_mcp_id("contains/slash").is_err());
    }

    #[test]
    fn validate_mcp_id_accepts_valid() {
        use crate::domain::ids::validate_mcp_id;
        assert!(validate_mcp_id("wall_001").is_ok());
        assert!(validate_mcp_id("castle_001:wall:north:0001").is_ok());
    }
}
