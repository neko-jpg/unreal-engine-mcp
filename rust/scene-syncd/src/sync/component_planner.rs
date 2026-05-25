//! Component planner for React-for-UE v3.0.
//!
//! Computes Create / Update / Delete / Noop / Conflict actions for the
//! `scene_component` table based on the desired_hash vs last_applied_hash
//! and the sync_status field.

use crate::domain::SceneComponent;
use serde::{Deserialize, Serialize};
use sha1::{Digest, Sha1};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ComponentAction {
    Create,
    Update,
    Delete,
    Noop,
    Conflict,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ComponentOperation {
    pub action: ComponentAction,
    pub scene_id: String,
    pub entity_id: String,
    pub component_type: String,
    pub name: String,
    pub desired_hash: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ComponentPlanSummary {
    pub create: usize,
    pub update: usize,
    pub delete: usize,
    pub noop: usize,
    pub conflict: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentPlan {
    pub scene_id: String,
    pub summary: ComponentPlanSummary,
    pub operations: Vec<ComponentOperation>,
}

/// Hash properties to a hex SHA1 string. Deterministic, schema-stable.
pub fn compute_desired_hash(properties: &serde_json::Value) -> String {
    let canonical = canonical_json(properties);
    let mut hasher = Sha1::new();
    hasher.update(canonical.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Canonical JSON serializer: keys sorted, no whitespace.
pub fn canonical_json(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let mut out = String::from("{");
            for (i, key) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('"');
                out.push_str(key);
                out.push_str("\":");
                out.push_str(&canonical_json(&map[*key]));
            }
            out.push('}');
            out
        }
        serde_json::Value::Array(items) => {
            let mut out = String::from("[");
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push_str(&canonical_json(item));
            }
            out.push(']');
            out
        }
        _ => serde_json::to_string(value).unwrap_or_default(),
    }
}

pub fn plan_component_sync(scene_id: &str, components: &[SceneComponent]) -> ComponentPlan {
    let mut plan = ComponentPlan {
        scene_id: scene_id.to_string(),
        summary: ComponentPlanSummary::default(),
        operations: Vec::new(),
    };
    for comp in components {
        let desired = if comp.desired_hash.is_empty() {
            compute_desired_hash(&comp.properties)
        } else {
            comp.desired_hash.clone()
        };
        let action = decide_action(comp, &desired);
        let reason = match action {
            ComponentAction::Create => "no last_applied_hash; first apply".to_string(),
            ComponentAction::Update => "desired_hash differs from last_applied_hash".to_string(),
            ComponentAction::Delete => "deleted=true and component still applied".to_string(),
            ComponentAction::Noop => "desired_hash matches last_applied_hash".to_string(),
            ComponentAction::Conflict => "sync_status=conflict in DB".to_string(),
        };
        match action {
            ComponentAction::Create => plan.summary.create += 1,
            ComponentAction::Update => plan.summary.update += 1,
            ComponentAction::Delete => plan.summary.delete += 1,
            ComponentAction::Noop => plan.summary.noop += 1,
            ComponentAction::Conflict => plan.summary.conflict += 1,
        }
        plan.operations.push(ComponentOperation {
            action,
            scene_id: scene_id.to_string(),
            entity_id: comp.entity_id.clone(),
            component_type: comp.component_type.clone(),
            name: comp.name.clone(),
            desired_hash: desired,
            reason,
        });
    }
    plan
}

fn decide_action(comp: &SceneComponent, desired: &str) -> ComponentAction {
    if comp.sync_status == "conflict" {
        return ComponentAction::Conflict;
    }
    if comp.deleted {
        return if comp.last_applied_hash.is_some() {
            ComponentAction::Delete
        } else {
            ComponentAction::Noop
        };
    }
    match comp.last_applied_hash.as_deref() {
        None => ComponentAction::Create,
        Some(prev) if prev == desired => ComponentAction::Noop,
        Some(_) => ComponentAction::Update,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use surrealdb::sql::Datetime;

    fn _now() -> Datetime {
        Datetime::from(Utc::now())
    }

    fn _component(
        component_type: &str,
        properties: serde_json::Value,
        last_applied_hash: Option<&str>,
        deleted: bool,
        sync_status: &str,
    ) -> SceneComponent {
        SceneComponent {
            id: String::new(),
            scene: "scene:test".to_string(),
            entity_id: "e1".to_string(),
            component_type: component_type.to_string(),
            name: "n1".to_string(),
            properties,
            metadata: serde_json::Value::Null,
            created_at: _now(),
            updated_at: _now(),
            desired_hash: String::new(),
            last_applied_hash: last_applied_hash.map(|s| s.to_string()),
            sync_status: sync_status.to_string(),
            deleted,
            revision: 1,
            last_operation_id: None,
            updated_by: None,
        }
    }

    #[test]
    fn canonical_json_is_order_independent() {
        let a = serde_json::json!({"a":1, "b":[1,2]});
        let b = serde_json::json!({"b":[1,2], "a":1});
        assert_eq!(canonical_json(&a), canonical_json(&b));
    }

    #[test]
    fn desired_hash_matches_python_sha1_canonical_json() {
        assert_eq!(
            compute_desired_hash(&serde_json::json!({"x": 1})),
            "8724fc2165f042facbd9194627e4748bb7571b27"
        );
    }

    #[test]
    fn desired_hash_changes_with_values() {
        assert_ne!(
            compute_desired_hash(&serde_json::json!({"x":1})),
            compute_desired_hash(&serde_json::json!({"x":2})),
        );
    }

    #[test]
    fn create_when_no_last_applied_hash() {
        let c = _component("material", serde_json::json!({"x":1}), None, false, "pending");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.create, 1);
        assert_eq!(plan.operations[0].action, ComponentAction::Create);
    }

    #[test]
    fn noop_when_hashes_match() {
        let props = serde_json::json!({"x":1});
        let hash = compute_desired_hash(&props);
        let c = _component("material", props, Some(&hash), false, "synced");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.noop, 1);
    }

    #[test]
    fn update_when_hashes_differ() {
        let c = _component("material", serde_json::json!({"x":1}), Some("deadbeef"), false, "synced");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.update, 1);
    }

    #[test]
    fn delete_when_deleted_and_was_applied() {
        let c = _component("material", serde_json::json!({"x":1}), Some("aa"), true, "synced");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.delete, 1);
    }

    #[test]
    fn delete_becomes_noop_when_never_applied() {
        let c = _component("material", serde_json::json!({"x":1}), None, true, "pending");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.noop, 1);
    }

    #[test]
    fn conflict_status_short_circuits() {
        let c = _component("material", serde_json::json!({"x":1}), Some("aa"), false, "conflict");
        let plan = plan_component_sync("test", &[c]);
        assert_eq!(plan.summary.conflict, 1);
        assert_eq!(plan.operations[0].action, ComponentAction::Conflict);
    }
}
