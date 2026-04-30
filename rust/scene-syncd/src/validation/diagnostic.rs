use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Diagnostic {
    pub severity: Severity,
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub entity_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mcp_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub generated_part: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggestion: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggested_transform: Option<crate::domain::Transform>,
}

impl Diagnostic {
    pub fn error(code: &str, message: String) -> Self {
        Self {
            severity: Severity::Error,
            code: code.to_string(),
            message,
            entity_id: None,
            mcp_id: None,
            generated_part: None,
            suggestion: None,
            suggested_transform: None,
        }
    }

    pub fn warning(code: &str, message: String) -> Self {
        Self {
            severity: Severity::Warning,
            code: code.to_string(),
            message,
            entity_id: None,
            mcp_id: None,
            generated_part: None,
            suggestion: None,
            suggested_transform: None,
        }
    }

    pub fn info(code: &str, message: String) -> Self {
        Self {
            severity: Severity::Info,
            code: code.to_string(),
            message,
            entity_id: None,
            mcp_id: None,
            generated_part: None,
            suggestion: None,
            suggested_transform: None,
        }
    }

    pub fn with_entity_id(mut self, id: String) -> Self {
        self.entity_id = Some(id);
        self
    }

    pub fn with_mcp_id(mut self, id: String) -> Self {
        self.mcp_id = Some(id);
        self
    }

    pub fn with_generated_part(mut self, part: String) -> Self {
        self.generated_part = Some(part);
        self
    }

    pub fn with_suggestion(mut self, suggestion: String) -> Self {
        self.suggestion = Some(suggestion);
        self
    }

    pub fn with_suggested_transform(mut self, t: crate::domain::Transform) -> Self {
        self.suggested_transform = Some(t);
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn diagnostic_builder() {
        let d = Diagnostic::error("E001", "test".to_string())
            .with_mcp_id("obj_1".to_string())
            .with_suggestion("fix it".to_string());
        assert_eq!(d.severity, Severity::Error);
        assert_eq!(d.code, "E001");
        assert_eq!(d.mcp_id, Some("obj_1".to_string()));
        assert_eq!(d.suggestion, Some("fix it".to_string()));
    }
}
