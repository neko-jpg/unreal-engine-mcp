use crate::domain::SceneObject;
use crate::sync::{SyncAction, SyncOperation, SyncPlan, SyncPlanSummary, UnrealActorObservation};
use std::collections::HashMap;

const LOCATION_EPSILON: f64 = 0.01;
const ROTATION_EPSILON: f64 = 0.01;
const SCALE_EPSILON: f64 = 0.0001;

pub fn plan_sync(
    scene_id: &str,
    desired_objects: &[SceneObject],
    actual_actors: &[UnrealActorObservation],
) -> SyncPlan {
    let mut desired_index: HashMap<&str, &SceneObject> = HashMap::new();
    let mut actual_index: HashMap<&str, &UnrealActorObservation> = HashMap::new();
    let mut warnings: Vec<String> = Vec::new();

    for obj in desired_objects {
        if desired_index.contains_key(obj.mcp_id.as_str()) {
            warnings.push(format!("duplicate desired mcp_id: {}", obj.mcp_id));
        }
        desired_index.insert(&obj.mcp_id, obj);
    }

    for actor in actual_actors {
        if let Some(mcp_id) = actor.mcp_id() {
            if actual_index.contains_key(mcp_id) {
                warnings.push(format!("duplicate actual mcp_id: {mcp_id}"));
            }
            actual_index.insert(mcp_id, actor);
        }
    }

    let mut operations: Vec<SyncOperation> = Vec::new();
    let mut summary = SyncPlanSummary::default();

    for (mcp_id, desired) in &desired_index {
        if desired.deleted {
            if actual_index.contains_key(mcp_id) {
                operations.push(SyncOperation {
                    action: SyncAction::Delete,
                    mcp_id: mcp_id.to_string(),
                    reason: "Desired object tombstoned and actor exists".to_string(),
                    desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                    actual: None,
                });
                summary.delete += 1;
            } else {
                operations.push(SyncOperation {
                    action: SyncAction::Noop,
                    mcp_id: mcp_id.to_string(),
                    reason: "Desired object tombstoned and actor already absent".to_string(),
                    desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                    actual: None,
                });
                summary.noop += 1;
            }
            continue;
        }

        match actual_index.get(mcp_id) {
            None => {
                operations.push(SyncOperation {
                    action: SyncAction::Create,
                    mcp_id: mcp_id.to_string(),
                    reason: "Desired object missing from Unreal".to_string(),
                    desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                    actual: None,
                });
                summary.create += 1;
            }
            Some(actual) => {
                if transform_differs(desired, actual) {
                    operations.push(SyncOperation {
                        action: SyncAction::UpdateTransform,
                        mcp_id: mcp_id.to_string(),
                        reason: "Transform differs between desired and actual".to_string(),
                        desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                        actual: Some(serde_json::to_value(actual).unwrap_or_default()),
                    });
                    summary.update_transform += 1;
                } else {
                    let desired_hash = &desired.desired_hash;
                    let applied_hash = desired.last_applied_hash.as_deref().unwrap_or("");
                    if desired_hash != applied_hash {
                        operations.push(SyncOperation {
                            action: SyncAction::UpdateVisual,
                            mcp_id: mcp_id.to_string(),
                            reason: "Non-transform fields changed".to_string(),
                            desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                            actual: Some(serde_json::to_value(actual).unwrap_or_default()),
                        });
                        summary.update_visual += 1;
                    } else {
                        operations.push(SyncOperation {
                            action: SyncAction::Noop,
                            mcp_id: mcp_id.to_string(),
                            reason: "Desired and actual match".to_string(),
                            desired: None,
                            actual: None,
                        });
                        summary.noop += 1;
                    }
                }
            }
        }
    }

    for (mcp_id, actor) in &actual_index {
        if !desired_index.contains_key(mcp_id) {
            operations.push(SyncOperation {
                action: SyncAction::Conflict,
                mcp_id: mcp_id.to_string(),
                reason: "Managed actor found in Unreal but not in desired state (orphan)".to_string(),
                desired: None,
                actual: Some(serde_json::to_value(actor).unwrap_or_default()),
            });
            summary.conflict += 1;
        }
    }

    operations.sort_by(|a, b| {
        let order = |a: &SyncAction| match a {
            SyncAction::Create => 0,
            SyncAction::UpdateTransform => 1,
            SyncAction::UpdateVisual => 2,
            SyncAction::Delete => 3,
            SyncAction::Noop => 4,
            SyncAction::Conflict => 5,
            SyncAction::Unsupported => 6,
        };
        order(&a.action).cmp(&order(&b.action))
    });

    SyncPlan {
        scene_id: scene_id.to_string(),
        summary,
        operations,
        warnings,
    }
}

fn transform_differs(desired: &SceneObject, actual: &UnrealActorObservation) -> bool {
    let loc = &desired.transform.location;
    let rot = &desired.transform.rotation;
    let scl = &desired.transform.scale;

    (loc.x - actual.location[0]).abs() > LOCATION_EPSILON
        || (loc.y - actual.location[1]).abs() > LOCATION_EPSILON
        || (loc.z - actual.location[2]).abs() > LOCATION_EPSILON
        || (rot.pitch - actual.rotation[0]).abs() > ROTATION_EPSILON
        || (rot.yaw - actual.rotation[1]).abs() > ROTATION_EPSILON
        || (rot.roll - actual.rotation[2]).abs() > ROTATION_EPSILON
        || (scl.x - actual.scale[0]).abs() > SCALE_EPSILON
        || (scl.y - actual.scale[1]).abs() > SCALE_EPSILON
        || (scl.z - actual.scale[2]).abs() > SCALE_EPSILON
}