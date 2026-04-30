use serde::{Deserialize, Serialize};

/// Rust-side protocol structs for C++ ISM/HISM commands.
/// Defined in Rust first as serde structs to avoid drift with C++ side.

/// Command to spawn or update an Instanced Static Mesh component.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct IsmCommand {
    pub scene_id: String,
    pub set_id: String,
    pub mesh: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub material: Option<String>,
    pub transforms: Vec<TransformData>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cell_id: Option<String>,
    /// ISM for <= 100 instances, HISM for > 100.
    pub component_type: IsmComponentType,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum IsmComponentType {
    Ism,
    Hism,
}

/// Transform data sent to Unreal for each instance.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TransformData {
    pub location: [f64; 3],
    pub rotation: [f64; 3],
    pub scale: [f64; 3],
}

impl TransformData {
    pub fn from_transform(t: &crate::domain::Transform) -> Self {
        Self {
            location: [t.location.x, t.location.y, t.location.z],
            rotation: [t.rotation.pitch, t.rotation.yaw, t.rotation.roll],
            scale: [t.scale.x, t.scale.y, t.scale.z],
        }
    }
}

/// Response from Unreal after an ISM/HISM operation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct IsmResponse {
    pub success: bool,
    pub set_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    pub instance_count: usize,
}

/// Choose ISM vs HISM based on instance count threshold.
pub fn choose_component_type(instance_count: usize) -> IsmComponentType {
    if instance_count <= 100 {
        IsmComponentType::Ism
    } else {
        IsmComponentType::Hism
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ism_for_small_count() {
        assert!(matches!(choose_component_type(50), IsmComponentType::Ism));
    }

    #[test]
    fn hism_for_large_count() {
        assert!(matches!(choose_component_type(150), IsmComponentType::Hism));
    }

    #[test]
    fn hism_at_threshold() {
        assert!(matches!(choose_component_type(101), IsmComponentType::Hism));
    }

    #[test]
    fn transform_data_roundtrip() {
        let t = crate::domain::Transform::default();
        let data = TransformData::from_transform(&t);
        let json = serde_json::to_string(&data).unwrap();
        assert!(json.contains("location"));
    }
}
