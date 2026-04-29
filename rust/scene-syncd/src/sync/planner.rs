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
    let mut unsafe_for_delete: std::collections::HashSet<&str> = std::collections::HashSet::new();

    for obj in desired_objects {
        if desired_index.contains_key(obj.mcp_id.as_str()) {
            warnings.push(format!("duplicate desired mcp_id: {}", obj.mcp_id));
            continue;
        }
        desired_index.insert(&obj.mcp_id, obj);
    }

    for actor in actual_actors {
        if let Some(mcp_id) = actor.mcp_id() {
            if actual_index.contains_key(mcp_id) {
                warnings.push(format!("duplicate actual mcp_id: {mcp_id}"));
                unsafe_for_delete.insert(mcp_id);
            }
            actual_index.insert(mcp_id, actor);
        }
    }

    let mut operations: Vec<SyncOperation> = Vec::new();
    let mut summary = SyncPlanSummary::default();

    for (mcp_id, desired) in &desired_index {
        if desired.deleted {
            if unsafe_for_delete.contains(mcp_id) {
                operations.push(SyncOperation {
                    action: SyncAction::Conflict,
                    mcp_id: mcp_id.to_string(),
                    reason: "Desired object tombstoned but duplicate mcp_id in Unreal makes delete unsafe".to_string(),
                    desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                    actual: None,
                });
                summary.conflict += 1;
            } else if actual_index.contains_key(mcp_id) {
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
                } else if tags_diff(desired, actual) {
                    operations.push(SyncOperation {
                        action: SyncAction::UpdateVisual,
                        mcp_id: mcp_id.to_string(),
                        reason: "Tags differ between desired and actual".to_string(),
                        desired: Some(serde_json::to_value(desired).unwrap_or_default()),
                        actual: Some(serde_json::to_value(actual).unwrap_or_default()),
                    });
                    summary.update_visual += 1;
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
                reason: "Managed actor found in Unreal but not in desired state (orphan)"
                    .to_string(),
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

fn tags_diff(desired: &SceneObject, actual: &UnrealActorObservation) -> bool {
    fn is_system_tag(tag: &str) -> bool {
        tag == "managed_by_mcp" || tag.starts_with("mcp_id:")
    }
    let mut desired_tags: Vec<&str> = desired
        .tags
        .iter()
        .map(|s| s.as_str())
        .filter(|t| !is_system_tag(t))
        .collect();
    let mut actual_tags: Vec<&str> = actual
        .tags
        .iter()
        .map(|s| s.as_str())
        .filter(|t| !is_system_tag(t))
        .collect();
    desired_tags.sort_unstable();
    actual_tags.sort_unstable();
    desired_tags != actual_tags
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::transform::compute_desired_hash;
    use crate::domain::{Rotator, Transform, Vec3};
    use surrealdb::sql::Datetime;

    fn make_object(mcp_id: &str, x: f64, y: f64, z: f64) -> SceneObject {
        let mut obj = SceneObject {
            id: String::new(),
            scene: "scene:main".to_string(),
            group: None,
            mcp_id: mcp_id.to_string(),
            desired_name: mcp_id.to_string(),
            unreal_actor_name: None,
            actor_type: "StaticMeshActor".to_string(),
            asset_ref: serde_json::json!({"path": "/Engine/BasicShapes/Cube.Cube"}),
            transform: Transform {
                location: Vec3 { x, y, z },
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
            visual: serde_json::json!({}),
            physics: serde_json::json!({}),
            tags: vec![],
            metadata: serde_json::json!({}),
            desired_hash: String::new(),
            last_applied_hash: None,
            sync_status: "pending".to_string(),
            deleted: false,
            revision: 1,
            created_at: Datetime::from(chrono::Utc::now()),
            updated_at: Datetime::from(chrono::Utc::now()),
        };
        obj.desired_hash = compute_desired_hash(&obj).unwrap_or_default();
        obj
    }

    fn make_actor(mcp_id: &str, x: f64, y: f64, z: f64) -> UnrealActorObservation {
        UnrealActorObservation {
            name: mcp_id.to_string(),
            class: "StaticMeshActor".to_string(),
            location: [x, y, z],
            rotation: [0.0, 0.0, 0.0],
            scale: [1.0, 1.0, 1.0],
            tags: vec!["managed_by_mcp".to_string(), format!("mcp_id:{mcp_id}")],
        }
    }

    #[test]
    fn plan_create_when_desired_not_in_actual() {
        let desired = vec![make_object("obj_1", 0.0, 0.0, 0.0)];
        let plan = plan_sync("main", &desired, &[]);
        assert_eq!(plan.summary.create, 1);
        assert_eq!(plan.operations.len(), 1);
        assert_eq!(plan.operations[0].action, SyncAction::Create);
    }

    #[test]
    fn plan_noop_when_desired_matches_actual() {
        let obj = make_object("obj_1", 10.0, 20.0, 30.0);
        let obj_hash = obj.desired_hash.clone();
        let mut desired_obj = obj.clone();
        desired_obj.last_applied_hash = Some(obj_hash);
        let actors = vec![make_actor("obj_1", 10.0, 20.0, 30.0)];
        let plan = plan_sync("main", &[desired_obj], &actors);
        assert_eq!(plan.summary.noop, 1);
    }

    #[test]
    fn plan_update_transform_when_location_differs() {
        let obj = make_object("obj_1", 10.0, 20.0, 30.0);
        let mut desired_obj = obj.clone();
        desired_obj.last_applied_hash = Some(obj.desired_hash.clone());
        let actors = vec![make_actor("obj_1", 99.0, 20.0, 30.0)]; // different x
        let plan = plan_sync("main", &[desired_obj], &actors);
        assert_eq!(plan.summary.update_transform, 1);
    }

    #[test]
    fn plan_delete_when_desired_tombstoned() {
        let mut obj = make_object("obj_1", 0.0, 0.0, 0.0);
        obj.deleted = true;
        let actors = vec![make_actor("obj_1", 0.0, 0.0, 0.0)];
        let plan = plan_sync("main", &[obj], &actors);
        assert_eq!(plan.summary.delete, 1);
    }

    #[test]
    fn plan_conflict_for_orphan_actor() {
        let actors = vec![make_actor("orphan_1", 0.0, 0.0, 0.0)];
        let plan = plan_sync("main", &[], &actors);
        assert_eq!(plan.summary.conflict, 1);
    }

    #[test]
    fn plan_update_visual_when_hash_differs_but_transform_matches() {
        let obj = make_object("obj_1", 10.0, 20.0, 30.0);
        let mut desired_obj = obj.clone();
        // Change asset_ref to produce a different hash
        desired_obj.asset_ref = serde_json::json!({"path": "/Engine/BasicShapes/Sphere.Sphere"});
        desired_obj.desired_hash = compute_desired_hash(&desired_obj).unwrap_or_default();
        desired_obj.last_applied_hash = Some(obj.desired_hash.clone());
        let actors = vec![make_actor("obj_1", 10.0, 20.0, 30.0)];
        let plan = plan_sync("main", &[desired_obj], &actors);
        assert_eq!(plan.summary.update_visual, 1);
    }

    #[test]
    fn duplicate_desired_mcp_id_produces_warning_and_skips() {
        let obj1 = make_object("dup_1", 0.0, 0.0, 0.0);
        let obj2 = make_object("dup_1", 10.0, 0.0, 0.0);
        let plan = plan_sync("main", &[obj1, obj2], &[]);
        assert!(plan
            .warnings
            .iter()
            .any(|w| w.contains("duplicate desired mcp_id")));
        // Only 1 operation should be generated (not 2)
        assert_eq!(plan.operations.len(), 1);
        assert_eq!(plan.summary.create, 1);
    }
}
