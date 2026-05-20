use crate::ir::instance_set::InstanceSet;
use serde::{Deserialize, Serialize};

/// High-level render command sent toward the Unreal executor layer.
/// Either a single Actor or an instanced group of identical meshes.
///
/// `large_enum_variant` is allowed because the Actor variant intentionally
/// owns a full `SceneObject` to avoid a heap allocation per render item in
/// the density-LOD planner hot path.
#[allow(clippy::large_enum_variant)]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", content = "data")]
pub enum RenderItem {
    Actor(crate::domain::SceneObject),
    InstanceSet(InstanceSet),
}
