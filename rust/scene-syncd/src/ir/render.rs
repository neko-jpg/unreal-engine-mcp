use crate::ir::instance_set::InstanceSet;
use serde::{Deserialize, Serialize};

/// High-level render command sent toward the Unreal executor layer.
/// Either a single Actor or an instanced group of identical meshes.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", content = "data")]
pub enum RenderItem {
    Actor(crate::domain::SceneObject),
    InstanceSet(InstanceSet),
}
