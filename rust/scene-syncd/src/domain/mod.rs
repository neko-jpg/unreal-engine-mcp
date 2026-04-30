pub mod ids;
pub mod transform;

use serde::{Deserialize, Serialize};
use surrealdb::sql::Datetime;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Rotator {
    pub pitch: f64,
    pub yaw: f64,
    pub roll: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Transform {
    pub location: Vec3,
    pub rotation: Rotator,
    pub scale: Vec3,
}

impl Default for Transform {
    fn default() -> Self {
        Self {
            location: Vec3 {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
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
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scene {
    #[serde(default, skip_serializing, skip_deserializing)]
    #[allow(dead_code)]
    pub id: String,
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub status: String,
    pub active_revision: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unreal_project_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unreal_level_name: Option<String>,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct SceneGroup {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub kind: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_name: Option<String>,
    pub name: String,
    #[serde(default)]
    pub params: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub seed: Option<String>,
    pub revision: i64,
    pub deleted: bool,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct GeneratorRun {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub kind: String,
    pub tool_name: String,
    pub name: String,
    #[serde(default)]
    pub params: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub seed: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub group_id: Option<String>,
    pub generated_count: i64,
    pub status: String,
    pub created_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SceneObject {
    #[serde(default, skip_serializing, skip_deserializing)]
    #[allow(dead_code)]
    pub id: String,
    pub scene: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub group: Option<String>,
    pub mcp_id: String,
    pub desired_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unreal_actor_name: Option<String>,
    pub actor_type: String,
    #[serde(default)]
    pub asset_ref: serde_json::Value,
    pub transform: Transform,
    #[serde(default)]
    pub visual: serde_json::Value,
    #[serde(default)]
    pub physics: serde_json::Value,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub desired_hash: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_applied_hash: Option<String>,
    pub sync_status: String,
    pub deleted: bool,
    pub revision: i64,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneSnapshot {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub revision: i64,
    #[serde(default)]
    pub groups: Vec<serde_json::Value>,
    #[serde(default)]
    pub objects: Vec<SceneObject>,
    pub created_at: Datetime,
}

// ------------------------------------------------------------------
// P3: Semantic layer domain types
// ------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneEntity {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub entity_id: String,
    pub kind: String,
    pub name: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub mcp_ids: Vec<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
    #[serde(default)]
    pub deleted: bool,
    pub revision: i64,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneRelation {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub relation_id: String,
    pub source_entity_id: String,
    pub target_entity_id: String,
    pub relation_type: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneComponent {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub entity_id: String,
    pub component_type: String,
    pub name: String,
    #[serde(default)]
    pub properties: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneAsset {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub asset_id: String,
    pub kind: String,
    pub status: String,
    #[serde(default)]
    pub fallback: String,
    #[serde(default)]
    pub semantic_tags: Vec<String>,
    pub quality: String,
    #[serde(default)]
    pub variants: serde_json::Value,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneBlueprint {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub blueprint_id: String,
    pub class_name: String,
    #[serde(default)]
    pub parent_class: String,
    #[serde(default)]
    pub components: Vec<serde_json::Value>,
    #[serde(default)]
    pub variables: Vec<serde_json::Value>,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneRealization {
    #[serde(default, skip_serializing, skip_deserializing)]
    pub id: String,
    pub scene: String,
    pub entity_id: String,
    pub policy: String,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unreal_actor_name: Option<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
    pub created_at: Datetime,
    pub updated_at: Datetime,
}
