use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Maps semantic entity IDs to the parts (objects, instance sets) generated from them.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SourceMap {
    /// entity_id -> list of generated mcp_ids
    pub entity_to_parts: HashMap<String, Vec<String>>,
    /// mcp_id -> source entity_id
    pub part_to_entity: HashMap<String, String>,
}

impl SourceMap {
    pub fn new() -> Self {
        Self {
            entity_to_parts: HashMap::new(),
            part_to_entity: HashMap::new(),
        }
    }

    pub fn register(&mut self, entity_id: &str, generated_mcp_id: &str) {
        self.entity_to_parts
            .entry(entity_id.to_string())
            .or_default()
            .push(generated_mcp_id.to_string());
        self.part_to_entity
            .insert(generated_mcp_id.to_string(), entity_id.to_string());
    }

    pub fn parts_for(&self, entity_id: &str) -> Option<&Vec<String>> {
        self.entity_to_parts.get(entity_id)
    }

    pub fn entity_for(&self, mcp_id: &str) -> Option<&String> {
        self.part_to_entity.get(mcp_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn register_and_lookup() {
        let mut map = SourceMap::new();
        map.register("tower_1", "tower_1_mesh");
        map.register("tower_1", "tower_1_crenellation");

        assert_eq!(map.parts_for("tower_1").unwrap().len(), 2);
        assert_eq!(map.entity_for("tower_1_mesh").unwrap(), "tower_1");
        assert_eq!(map.entity_for("tower_1_crenellation").unwrap(), "tower_1");
    }

    #[test]
    fn unknown_entity_returns_none() {
        let map = SourceMap::new();
        assert!(map.parts_for("nonexistent").is_none());
    }
}
