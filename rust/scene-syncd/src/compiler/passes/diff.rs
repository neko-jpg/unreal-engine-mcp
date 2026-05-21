use crate::compiler::context::CompilerContext;
use crate::compiler::passes::Pass;
use crate::error::AppError;
use crate::ir::sync::SyncIr;
use crate::validation::diagnostic::Diagnostic;

/// Diff Planning Pass (Phase 2).
/// Compares desired state in the context against an optional actual snapshot
/// and produces SyncIr + diagnostics for expected changes.
pub struct DiffPlanningPass {
    /// Optional actual snapshot for comparison.
    pub actual: Option<Vec<crate::domain::SceneObject>>,
}

impl Default for DiffPlanningPass {
    fn default() -> Self {
        Self::new()
    }
}

impl DiffPlanningPass {
    pub fn new() -> Self {
        Self { actual: None }
    }

    pub fn with_actual(actual: Vec<crate::domain::SceneObject>) -> Self {
        Self {
            actual: Some(actual),
        }
    }
}

impl Pass for DiffPlanningPass {
    fn name(&self) -> &'static str {
        "diff"
    }

    fn run(&self, ctx: &mut CompilerContext) -> Result<(), AppError> {
        let total = ctx.objects.len();
        let deleted_tombstoned = ctx.objects.iter().filter(|o| o.deleted).count();
        let active = total - deleted_tombstoned;

        if total > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_PLAN_SUMMARY",
                format!(
                    "Diff plan: {} active objects, {} tombstoned.",
                    active, deleted_tombstoned
                ),
            )]);
        }

        // Incremental skip pass: when last_applied_hash == desired_hash on an
        // object, it has already been pushed to Unreal and does not need to
        // be re-diffed. This is the cheap fast-path for steady-state scenes.
        let already_applied = ctx
            .objects
            .iter()
            .filter(|o| {
                !o.deleted
                    && o.last_applied_hash
                        .as_ref()
                        .map(|h| h == &o.desired_hash)
                        .unwrap_or(false)
            })
            .count();
        if already_applied > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_INCREMENTAL_SKIP",
                format!(
                    "Incremental skip: {} object(s) already in sync (last_applied_hash matches desired_hash).",
                    already_applied
                ),
            )]);
        }

        let sync_ir = SyncIr::from_desired_and_actual(&ctx.objects, self.actual.as_deref());

        // Detailed per-op-kind diagnostics for `compile_plan` consumers.
        let mut creates = 0usize;
        let mut updates = 0usize;
        let mut deletes = 0usize;
        let mut noops = 0usize;
        for op in &sync_ir.operations {
            match op {
                crate::ir::sync::SyncOperation::Create { .. } => creates += 1,
                crate::ir::sync::SyncOperation::Update { .. } => updates += 1,
                crate::ir::sync::SyncOperation::Delete { .. } => deletes += 1,
                crate::ir::sync::SyncOperation::NoOp { .. } => noops += 1,
            }
        }

        let unchanged = active.saturating_sub(creates + updates);
        if creates > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_WOULD_CREATE",
                format!("Would create {creates} actor(s)."),
            )]);
        }
        if updates > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_WOULD_UPDATE",
                format!("Would update {updates} actor(s)."),
            )]);
        }
        if deletes > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_WOULD_DELETE",
                format!("Would delete {deletes} actor(s)."),
            )]);
        }
        if noops > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_WOULD_NOOP",
                format!("{noops} actor(s) reported as explicit no-op."),
            )]);
        }
        if unchanged > 0 {
            ctx.add_diagnostics(vec![Diagnostic::info(
                "DIFF_WOULD_SKIP_UNCHANGED",
                format!("Would skip {unchanged} unchanged actor(s)."),
            )]);
        }

        ctx.sync_ir = Some(sync_ir);

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{SceneObject, Transform};
    use serde_json::json;

    fn make_obj(mcp_id: &str, hash: &str) -> SceneObject {
        SceneObject {
            id: String::new(),
            scene: "scene:test".to_string(),
            group: None,
            mcp_id: mcp_id.to_string(),
            desired_name: mcp_id.to_string(),
            unreal_actor_name: None,
            actor_type: "StaticMeshActor".to_string(),
            asset_ref: json!({}),
            transform: Transform::default(),
            visual: json!({}),
            physics: json!({}),
            tags: vec![],
            metadata: json!({}),
            desired_hash: hash.to_string(),
            last_applied_hash: None,
            sync_status: "pending".to_string(),
            deleted: false,
            revision: 1,
            created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
            updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        }
    }

    #[test]
    fn diff_pass_summarizes_objects() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("a", "h1")];
        let pass = DiffPlanningPass::new();
        pass.run(&mut ctx).unwrap();
        assert!(ctx
            .diagnostics
            .iter()
            .any(|d| d.code == "DIFF_PLAN_SUMMARY"));
        assert!(ctx.sync_ir.is_some());
    }

    #[test]
    fn diff_with_matching_actual_produces_noop() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("a", "h1")];
        let actual = vec![make_obj("a", "h1")];
        let pass = DiffPlanningPass::with_actual(actual);
        pass.run(&mut ctx).unwrap();
        let sync = ctx.sync_ir.unwrap();
        assert!(sync.operations.is_empty());
    }

    #[test]
    fn diff_with_different_hash_produces_update() {
        let mut ctx = CompilerContext::new("test".to_string());
        ctx.objects = vec![make_obj("a", "h2")];
        let actual = vec![make_obj("a", "h1")];
        let pass = DiffPlanningPass::with_actual(actual);
        pass.run(&mut ctx).unwrap();
        let sync = ctx.sync_ir.unwrap();
        assert_eq!(sync.operations.len(), 1);
        assert!(matches!(
            sync.operations[0],
            crate::ir::sync::SyncOperation::Update { .. }
        ));
    }
}
