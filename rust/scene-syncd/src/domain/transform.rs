use sha2::{Digest, Sha256};
use crate::domain::SceneObject;

#[derive(serde::Serialize)]
struct DesiredHashPayload {
    actor_type: String,
    asset_ref: serde_json::Value,
    transform: TransformPayload,
    visual: serde_json::Value,
    physics: serde_json::Value,
    tags: Vec<String>,
    metadata: serde_json::Value,
}

#[derive(serde::Serialize)]
struct TransformPayload {
    location: [f64; 3],
    rotation: [f64; 3],
    scale: [f64; 3],
}

pub fn compute_desired_hash(obj: &SceneObject) -> Result<String, String> {
    let mut tags = obj.tags.clone();
    tags.sort();

    let payload = DesiredHashPayload {
        actor_type: obj.actor_type.clone(),
        asset_ref: normalize_json(&obj.asset_ref),
        transform: TransformPayload {
            location: [obj.transform.location.x, obj.transform.location.y, obj.transform.location.z],
            rotation: [obj.transform.rotation.pitch, obj.transform.rotation.yaw, obj.transform.rotation.roll],
            scale: [obj.transform.scale.x, obj.transform.scale.y, obj.transform.scale.z],
        },
        visual: normalize_json(&obj.visual),
        physics: normalize_json(&obj.physics),
        tags,
        metadata: normalize_json(&obj.metadata),
    };

    let bytes = serde_json::to_vec(&payload).map_err(|e| format!("hash serialization error: {e}"))?;
    let digest = Sha256::digest(&bytes);
    Ok(format!("{:x}", digest))
}

fn normalize_json(v: &serde_json::Value) -> serde_json::Value {
    if v.is_null() {
        serde_json::Value::Object(serde_json::Map::new())
    } else {
        v.clone()
    }
}
