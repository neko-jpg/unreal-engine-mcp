use crate::domain::SceneObject;
use crate::validation::diagnostic::Diagnostic;
use crate::validation::engine::ValidationRule;

pub struct NoZeroOrNegativeScale;

impl ValidationRule for NoZeroOrNegativeScale {
    fn code(&self) -> &'static str {
        "NO_ZERO_OR_NEGATIVE_SCALE"
    }

    fn validate(
        &self,
        objects: &[SceneObject],
        _footprints: &[crate::geom::footprint::Footprint2],
    ) -> Vec<Diagnostic> {
        let mut results = Vec::new();
        for obj in objects {
            let s = &obj.transform.scale;
            if s.x <= 0.0 || s.y <= 0.0 || s.z <= 0.0 {
                results.push(
                    Diagnostic::error(
                        self.code(),
                        format!(
                            "Object {} has zero or negative scale: x={}, y={}, z={}",
                            obj.mcp_id, s.x, s.y, s.z
                        ),
                    )
                    .with_mcp_id(obj.mcp_id.clone())
                    .with_suggestion("Use a positive scale for all axes".to_string()),
                );
            }
        }
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Rotator, SceneObject, Transform, Vec3};
    use serde_json::json;

    fn make_object(scale: Vec3) -> SceneObject {
        SceneObject {
            id: String::new(),
            scene: "scene:test".to_string(),
            group: None,
            mcp_id: "obj_1".to_string(),
            desired_name: "obj_1".to_string(),
            unreal_actor_name: None,
            actor_type: "StaticMeshActor".to_string(),
            asset_ref: json!({}),
            transform: Transform {
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
                scale,
            },
            visual: json!({}),
            physics: json!({}),
            tags: vec![],
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
    fn detects_zero_scale() {
        let rule = NoZeroOrNegativeScale;
        let obj = make_object(Vec3 {
            x: 0.0,
            y: 1.0,
            z: 1.0,
        });
        let diags = rule.validate(&[obj], &[]);
        assert_eq!(diags.len(), 1);
        assert_eq!(diags[0].code, "NO_ZERO_OR_NEGATIVE_SCALE");
    }

    #[test]
    fn detects_negative_scale() {
        let rule = NoZeroOrNegativeScale;
        let obj = make_object(Vec3 {
            x: 1.0,
            y: -2.0,
            z: 1.0,
        });
        let diags = rule.validate(&[obj], &[]);
        assert_eq!(diags.len(), 1);
    }

    #[test]
    fn positive_scale_passes() {
        let rule = NoZeroOrNegativeScale;
        let obj = make_object(Vec3 {
            x: 1.0,
            y: 2.0,
            z: 3.0,
        });
        let diags = rule.validate(&[obj], &[]);
        assert!(diags.is_empty());
    }
}
