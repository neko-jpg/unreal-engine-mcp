#[allow(dead_code)]
pub fn generate_scene_id(name: &str) -> String {
    format!("scene:{name}")
}

#[allow(dead_code)]
pub fn generate_scene_object_id(scene: &str, mcp_id: &str) -> String {
    format!("scene_object:{scene}_{mcp_id}")
}

#[allow(dead_code)]
pub fn generate_sync_run_id(scene: &str) -> String {
    let now = chrono::Utc::now();
    format!("sync_run:{}_{}", scene, now.format("%Y%m%d_%H%M%S"))
}

pub fn validate_mcp_id(id: &str) -> Result<(), String> {
    if id.is_empty() {
        return Err("mcp_id must not be empty".to_string());
    }
    if id.contains(' ') {
        return Err("mcp_id must not contain spaces".to_string());
    }
    if id.contains('/') {
        return Err("mcp_id must not contain slashes".to_string());
    }
    Ok(())
}
