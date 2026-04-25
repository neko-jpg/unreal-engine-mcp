use crate::config::Config;
use crate::error::AppError;
use crate::sync::UnrealActorObservation;
use serde_json::json;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;

pub struct UnrealClient {
    host: String,
    port: u16,
}

impl UnrealClient {
    pub fn new(config: &Config) -> Self {
        Self {
            host: config.unreal_host.clone(),
            port: config.unreal_port,
        }
    }

    pub async fn get_actors_in_level(&self) -> Result<Vec<UnrealActorObservation>, AppError> {
        let response = self.send_command("get_actors_in_level", json!({})).await?;

        let actors = response
            .get("actors")
            .and_then(|v| v.as_array())
            .ok_or_else(|| AppError::UnrealBridge("missing actors array in response".to_string()))?;

        let mut result = Vec::new();
        for actor_val in actors {
            let actor: UnrealActorObservation = serde_json::from_value(actor_val.clone())
                .map_err(|e| AppError::UnrealBridge(format!("failed to parse actor: {e}")))?;
            result.push(actor);
        }

        Ok(result)
    }

    pub async fn spawn_actor(&self, params: serde_json::Value) -> Result<serde_json::Value, AppError> {
        self.send_command("spawn_actor", params).await
    }

    pub async fn find_actor_by_mcp_id(&self, mcp_id: &str) -> Result<serde_json::Value, AppError> {
        self.send_command("find_actor_by_mcp_id", json!({ "mcp_id": mcp_id })).await
    }

    pub async fn set_actor_transform_by_mcp_id(
        &self,
        mcp_id: &str,
        location: [f64; 3],
        rotation: [f64; 3],
        scale: [f64; 3],
    ) -> Result<serde_json::Value, AppError> {
        self.send_command(
            "set_actor_transform_by_mcp_id",
            json!({
                "mcp_id": mcp_id,
                "location": location,
                "rotation": rotation,
                "scale": scale,
            }),
        )
        .await
    }

    pub async fn delete_actor_by_mcp_id(&self, mcp_id: &str) -> Result<serde_json::Value, AppError> {
        self.send_command("delete_actor_by_mcp_id", json!({ "mcp_id": mcp_id })).await
    }

    async fn send_command(
        &self,
        command: &str,
        params: serde_json::Value,
    ) -> Result<serde_json::Value, AppError> {
        let payload = json!({
            "command": command,
            "params": params,
        });

        let mut payload_bytes = serde_json::to_vec(&payload)
            .map_err(|e| AppError::UnrealBridge(format!("json encode error: {e}")))?;
        payload_bytes.push(b'\n');

        let addr = format!("{}:{}", self.host, self.port);

        let mut stream = TcpStream::connect_timeout(
            &addr.parse().map_err(|e: std::net::AddrParseError| AppError::UnrealBridge(format!("bad address: {e}")))?,
            Duration::from_secs(10),
        )
        .map_err(|e| AppError::UnrealBridge(format!("connect error to {addr}: {e}")))?;

        stream
            .write_all(&payload_bytes)
            .map_err(|e| AppError::UnrealBridge(format!("write payload error: {e}")))?;

        stream
            .set_read_timeout(Some(Duration::from_secs(30)))
            .map_err(|e| AppError::UnrealBridge(format!("set read timeout error: {e}")))?;

        let mut resp_buf = Vec::new();
        let mut chunk = [0u8; 4096];
        loop {
            let bytes_read = stream
                .read(&mut chunk)
                .map_err(|e| AppError::UnrealBridge(format!("read response error: {e}")))?;
            if bytes_read == 0 {
                if resp_buf.is_empty() {
                    return Err(AppError::UnrealBridge("connection closed before response".to_string()));
                }
                break;
            }

            resp_buf.extend_from_slice(&chunk[..bytes_read]);
            if resp_buf.contains(&b'\n') {
                let line_len = resp_buf
                    .iter()
                    .position(|b| *b == b'\n')
                    .unwrap_or(resp_buf.len());
                resp_buf.truncate(line_len);
                break;
            }
        }

        let response: serde_json::Value = serde_json::from_slice(&resp_buf)
            .map_err(|e| AppError::UnrealBridge(format!("json decode error: {e}")))?;

        Ok(normalize_response(response))
    }
}

fn normalize_response(response: serde_json::Value) -> serde_json::Value {
    if response.get("status").and_then(|v| v.as_str()) == Some("error") {
        return json!({
            "success": false,
            "error": response
                .get("error")
                .or_else(|| response.get("message"))
                .and_then(|v| v.as_str())
                .unwrap_or("unknown Unreal error"),
        });
    }

    if response.get("status").and_then(|v| v.as_str()) == Some("success") {
        if let Some(result) = response.get("result").and_then(|v| v.as_object()) {
            // Preserve nested actor envelope (find_actor_by_mcp_id uses this)
            if result.contains_key("actor") || result.contains_key("success") {
                let mut normalized = serde_json::Map::new();
                normalized.insert("success".to_string(), serde_json::Value::Bool(true));
                for (key, value) in result {
                    normalized.insert(key.clone(), value.clone());
                }
                return serde_json::Value::Object(normalized);
            }
            let mut normalized = serde_json::Map::new();
            normalized.insert("success".to_string(), serde_json::Value::Bool(true));
            for (key, value) in result {
                if key != "success" {
                    normalized.insert(key.clone(), value.clone());
                }
            }
            return serde_json::Value::Object(normalized);
        }
        return json!({ "success": true });
    }

    response
}
