use crate::ir::world_cell::WorldCell;
use crate::sync::{SyncOperation, SyncPlan};
use serde::{Deserialize, Serialize};

/// A deferred command for an unloaded World Partition cell.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DeferredCommand {
    pub cell_id: String,
    pub command: serde_json::Value,
    pub reason: String,
}

/// Cell-aware sync plan that separates operations by loaded/unloaded cells.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CellAwareSyncPlan {
    pub scene_id: String,
    pub loaded_ops: Vec<SyncOperation>,
    pub deferred: Vec<DeferredCommand>,
    pub summary: CellAwareSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct CellAwareSummary {
    pub loaded: usize,
    pub deferred: usize,
    pub cells_affected: usize,
}

/// Split a SyncPlan into loaded vs deferred based on cell state.
/// Operations whose mcp_id falls within a loaded cell are immediate; others are deferred.
pub fn split_by_cell_availability(
    plan: &SyncPlan,
    cells: &[WorldCell],
    loaded_cell_ids: &[&str],
) -> CellAwareSyncPlan {
    let loaded_set: std::collections::HashSet<&str> =
        loaded_cell_ids.iter().map(|s| s.as_ref()).collect();

    let mut loaded_ops = Vec::new();
    let mut deferred = Vec::new();

    for op in &plan.operations {
        // Find which cell contains this operation's mcp_id.
        let cell = cells.iter().find(|c| c.object_ids.contains(&op.mcp_id));
        match cell {
            Some(c) if loaded_set.contains(c.cell_id.as_str()) => {
                loaded_ops.push(op.clone());
            }
            Some(c) => {
                deferred.push(DeferredCommand {
                    cell_id: c.cell_id.clone(),
                    command: serde_json::to_value(op).unwrap_or_default(),
                    reason: format!("Cell {} is not loaded", c.cell_id),
                });
            }
            None => {
                // No cell assignment: treat as loaded (global actor).
                loaded_ops.push(op.clone());
            }
        }
    }

    let cells_affected = cells
        .iter()
        .filter(|c| {
            c.object_ids
                .iter()
                .any(|id| plan.operations.iter().any(|op| op.mcp_id == *id))
        })
        .count();

    let summary = CellAwareSummary {
        loaded: loaded_ops.len(),
        deferred: deferred.len(),
        cells_affected,
    };

    CellAwareSyncPlan {
        scene_id: plan.scene_id.clone(),
        loaded_ops,
        deferred,
        summary,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sync::{SyncAction, SyncPlan, SyncPlanSummary};

    #[test]
    fn all_ops_loaded_when_no_cells() {
        let plan = SyncPlan {
            scene_id: "s".to_string(),
            summary: SyncPlanSummary::default(),
            operations: vec![SyncOperation {
                action: SyncAction::Create,
                mcp_id: "a".to_string(),
                reason: "test".to_string(),
                desired: None,
                actual: None,
            }],
            warnings: vec![],
        };
        let cell_plan = split_by_cell_availability(&plan, &[], &[]);
        assert_eq!(cell_plan.summary.loaded, 1);
        assert_eq!(cell_plan.summary.deferred, 0);
    }

    #[test]
    fn loaded_cell_gets_immediate_ops() {
        let plan = SyncPlan {
            scene_id: "s".to_string(),
            summary: SyncPlanSummary::default(),
            operations: vec![SyncOperation {
                action: SyncAction::Create,
                mcp_id: "a".to_string(),
                reason: "test".to_string(),
                desired: None,
                actual: None,
            }],
            warnings: vec![],
        };
        let cells = vec![WorldCell {
            cell_id: "cell_0_0".to_string(),
            min_x: 0.0,
            max_x: 1000.0,
            min_y: 0.0,
            max_y: 1000.0,
            object_ids: vec!["a".to_string()],
            dirty_hash: String::new(),
        }];
        let cell_plan = split_by_cell_availability(&plan, &cells, &["cell_0_0"]);
        assert_eq!(cell_plan.summary.loaded, 1);
        assert_eq!(cell_plan.summary.deferred, 0);
    }

    #[test]
    fn unloaded_cell_gets_deferred_ops() {
        let plan = SyncPlan {
            scene_id: "s".to_string(),
            summary: SyncPlanSummary::default(),
            operations: vec![SyncOperation {
                action: SyncAction::Create,
                mcp_id: "a".to_string(),
                reason: "test".to_string(),
                desired: None,
                actual: None,
            }],
            warnings: vec![],
        };
        let cells = vec![WorldCell {
            cell_id: "cell_0_0".to_string(),
            min_x: 0.0,
            max_x: 1000.0,
            min_y: 0.0,
            max_y: 1000.0,
            object_ids: vec!["a".to_string()],
            dirty_hash: String::new(),
        }];
        let cell_plan = split_by_cell_availability(&plan, &cells, &[]);
        assert_eq!(cell_plan.summary.loaded, 0);
        assert_eq!(cell_plan.summary.deferred, 1);
    }
}
