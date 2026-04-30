use crate::compiler::context::CompilerContext;
use crate::compiler::passes::Pass;
use crate::error::AppError;
use crate::layout::kind_registry::KindRegistry;

/// Realization pass: maps semantic kinds to concrete Unreal assets.
/// Supports blockout, asset_binding, detail, and finalize stages.
pub struct RealizePass {
    pub stage: String,
}

impl RealizePass {
    pub fn blockout() -> Self {
        Self {
            stage: "blockout".to_string(),
        }
    }

    pub fn asset_binding() -> Self {
        Self {
            stage: "asset_binding".to_string(),
        }
    }

    pub fn detail() -> Self {
        Self {
            stage: "detail".to_string(),
        }
    }

    pub fn finalize() -> Self {
        Self {
            stage: "finalize".to_string(),
        }
    }
}

impl Pass for RealizePass {
    fn name(&self) -> &'static str {
        "realize"
    }

    fn run(&self, ctx: &mut CompilerContext) -> Result<(), AppError> {
        let registry = KindRegistry::default();
        for obj in &mut ctx.objects {
            if obj.deleted {
                continue;
            }
            let kind = obj
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("layout_kind:"))
                .unwrap_or("");
            if let Some(spec) = registry.get(kind) {
                obj.actor_type = spec.actor_type.to_string();
                match self.stage.as_str() {
                    "blockout" => {
                        obj.asset_ref = serde_json::json!({
                            "mesh": spec.asset_path,
                            "material": null,
                            "draft_color": spec.draft_color,
                        });
                    }
                    "asset_binding" => {
                        obj.asset_ref = serde_json::json!({
                            "mesh": spec.asset_path,
                            "material": null,
                        });
                    }
                    "detail" => {
                        // Integrate crenellations and detail tags.
                        let mut tags = obj.tags.clone();
                        if !tags.iter().any(|t| t.starts_with("detail:")) {
                            tags.push("detail:crenellation".to_string());
                        }
                        obj.tags = tags;
                    }
                    "finalize" => {
                        let mut tags = obj.tags.clone();
                        if !tags.iter().any(|t| t == "lod:high") {
                            tags.push("lod:high".to_string());
                        }
                        if !tags.iter().any(|t| t == "collision:complex") {
                            tags.push("collision:complex".to_string());
                        }
                        obj.tags = tags;
                    }
                    _ => {}
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Rotator, SceneObject, Transform, Vec3};
    use serde_json::json;

    fn make_obj(kind: &str) -> SceneObject {
        SceneObject {
            id: String::new(),
            scene: "scene:test".to_string(),
            group: None,
            mcp_id: "obj".to_string(),
            desired_name: "obj".to_string(),
            unreal_actor_name: None,
            actor_type: "Unknown".to_string(),
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
                scale: Vec3 {
                    x: 1.0,
                    y: 1.0,
                    z: 1.0,
                },
            },
            visual: json!({}),
            physics: json!({}),
            tags: vec![format!("layout_kind:{}", kind)],
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
    fn blockout_sets_basic_shape_mesh() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("keep")];
        let pass = RealizePass::blockout();
        pass.run(&mut ctx).unwrap();
        let obj = &ctx.objects[0];
        assert_eq!(obj.actor_type, "StaticMeshActor");
        let mesh = obj.asset_ref.get("mesh").and_then(|v| v.as_str());
        assert_eq!(mesh, Some("/Engine/BasicShapes/Cube.Cube"));
    }

    #[test]
    fn blockout_skips_deleted() {
        let mut ctx = CompilerContext::new("test".to_string());
        let mut obj = make_obj("keep");
        obj.deleted = true;
        ctx.objects = vec![obj];
        let pass = RealizePass::blockout();
        pass.run(&mut ctx).unwrap();
        assert!(ctx.objects[0].asset_ref.get("mesh").is_none());
    }

    #[test]
    fn asset_binding_sets_mesh_without_draft_color() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("keep")];
        let pass = RealizePass::asset_binding();
        pass.run(&mut ctx).unwrap();
        let obj = &ctx.objects[0];
        assert!(obj.asset_ref.get("mesh").is_some());
        assert!(obj.asset_ref.get("draft_color").is_none());
    }

    #[test]
    fn detail_adds_crenellation_tag() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("keep")];
        let pass = RealizePass::detail();
        pass.run(&mut ctx).unwrap();
        let obj = &ctx.objects[0];
        assert!(obj.tags.iter().any(|t| t == "detail:crenellation"));
    }

    #[test]
    fn finalize_adds_lod_and_collision_tags() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("keep")];
        let pass = RealizePass::finalize();
        pass.run(&mut ctx).unwrap();
        let obj = &ctx.objects[0];
        assert!(obj.tags.iter().any(|t| t == "lod:high"));
        assert!(obj.tags.iter().any(|t| t == "collision:complex"));
    }
}
