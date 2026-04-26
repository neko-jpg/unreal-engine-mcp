use crate::config::Config;
use crate::error::AppError;
use crate::sync::UnrealActorObservation;
use serde_json::json;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::time::timeout;

const MAX_RESPONSE_SIZE: usize = 16 * 1024 * 1024; // 16 MiB
const CONNECT_TIMEOUT: Duration = Duration::from_secs(10);
const READ_TIMEOUT: Duration = Duration::from_secs(30);

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
            .ok_or_else(|| {
                AppError::UnrealBridge("missing actors array in response".to_string())
            })?;

        let mut result = Vec::new();
        for actor_val in actors {
            let actor: UnrealActorObservation = serde_json::from_value(actor_val.clone())
                .map_err(|e| AppError::UnrealBridge(format!("failed to parse actor: {e}")))?;
            result.push(actor);
        }

        Ok(result)
    }

    pub async fn spawn_actor(
        &self,
        params: serde_json::Value,
    ) -> Result<serde_json::Value, AppError> {
        self.send_command("spawn_actor", params).await
    }

    pub async fn find_actor_by_mcp_id(&self, mcp_id: &str) -> Result<serde_json::Value, AppError> {
        self.send_command("find_actor_by_mcp_id", json!({ "mcp_id": mcp_id }))
            .await
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

    pub async fn delete_actor_by_mcp_id(
        &self,
        mcp_id: &str,
    ) -> Result<serde_json::Value, AppError> {
        self.send_command("delete_actor_by_mcp_id", json!({ "mcp_id": mcp_id }))
            .await
    }

    pub async fn set_mesh_material_color(
        &self,
        actor_name: &str,
        r: f64,
        g: f64,
        b: f64,
    ) -> Result<serde_json::Value, AppError> {
        self.send_command(
            "set_mesh_material_color",
            json!({
                "actor_name": actor_name,
                "r": r,
                "g": g,
                "b": b,
            }),
        )
        .await
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

        let stream = timeout(CONNECT_TIMEOUT, TcpStream::connect(&addr))
            .await
            .map_err(|_| AppError::UnrealBridge(format!("connect timeout to {addr}")))?
            .map_err(|e| AppError::UnrealBridge(format!("connect error to {addr}: {e}")))?;

        let mut stream = stream;
        stream
            .write_all(&payload_bytes)
            .await
            .map_err(|e| AppError::UnrealBridge(format!("write payload error: {e}")))?;

        let resp_buf = timeout(
            READ_TIMEOUT,
            read_line_limited(&mut stream, MAX_RESPONSE_SIZE),
        )
        .await
        .map_err(|_| AppError::UnrealBridge("read timeout".to_string()))?
        .map_err(|e| AppError::UnrealBridge(format!("read response error: {e}")))?;

        let response: serde_json::Value = serde_json::from_slice(&resp_buf)
            .map_err(|e| AppError::UnrealBridge(format!("json decode error: {e}")))?;

        Ok(normalize_response(response))
    }
}

async fn read_line_limited(stream: &mut TcpStream, max_size: usize) -> Result<Vec<u8>, AppError> {
    let mut resp_buf = Vec::new();
    let mut chunk = [0u8; 4096];
    loop {
        let bytes_read = stream
            .read(&mut chunk)
            .await
            .map_err(|e| AppError::UnrealBridge(format!("read error: {e}")))?;
        if bytes_read == 0 {
            if resp_buf.is_empty() {
                return Err(AppError::UnrealBridge(
                    "connection closed before response".to_string(),
                ));
            }
            break;
        }

        if resp_buf.len() + bytes_read > max_size {
            return Err(AppError::UnrealBridge(format!(
                "response exceeded maximum size of {max_size} bytes"
            )));
        }

        resp_buf.extend_from_slice(&chunk[..bytes_read]);
        if let Some(pos) = resp_buf.iter().position(|b| *b == b'\n') {
            resp_buf.truncate(pos);
            break;
        }
    }
    Ok(resp_buf)
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

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::TcpListener;

    async fn mock_bridge_server(port: u16) -> tokio::task::JoinHandle<()> {
        let listener = TcpListener::bind(format!("127.0.0.1:{port}"))
            .await
            .expect("mock bridge bind");
        tokio::spawn(async move {
            loop {
                let (mut socket, _) = listener.accept().await.unwrap();
                let mut buf = vec![0u8; 4096];
                let n = socket.read(&mut buf).await.unwrap();
                if n == 0 {
                    continue;
                }
                let req: serde_json::Value = serde_json::from_slice(&buf[..n]).unwrap_or(json!({}));
                let command = req.get("command").and_then(|v| v.as_str());
                let resp = match command {
                    Some("ping") => json!({"status": "success", "result": {"message": "pong"}}),
                    Some("get_actors_in_level") => json!({
                        "status": "success",
                        "result": {"actors": [
                            {
                                "name": "cube_01",
                                "class": "/Script/Engine.StaticMeshActor",
                                "location": [0.0, 0.0, 0.0],
                                "rotation": [0.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                                "tags": ["managed_by_mcp", "mcp_id:cube_01"]
                            }
                        ]}}
                    ),
                    Some("spawn_actor") => json!({
                        "status": "success",
                        "result": {"actor_name": "cube_01", "success": true}
                    }),
                    Some("find_actor_by_mcp_id") => json!({
                        "status": "success",
                        "result": {"actor": {"name": "cube_01", "class": "StaticMeshActor"}, "success": true}
                    }),
                    Some("delete_actor_by_mcp_id") => json!({
                        "status": "success",
                        "result": {"deleted_actor": {"name": "cube_01"}, "success": true}
                    }),
                    Some("set_actor_transform_by_mcp_id") => json!({
                        "status": "success",
                        "result": {"success": true}
                    }),
                    _ => json!({"status": "error", "error": "unknown command"}),
                };
                let mut resp_bytes = serde_json::to_vec(&resp).unwrap();
                resp_bytes.push(b'\n');
                socket.write_all(&resp_bytes).await.unwrap();
                socket.flush().await.unwrap();
            }
        })
    }

    #[tokio::test]
    async fn mock_bridge_ping_roundtrip() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener); // release so server can bind

        let _server = mock_bridge_server(port).await;
        tokio::time::sleep(Duration::from_millis(50)).await;

        let client = UnrealClient {
            host: "127.0.0.1".to_string(),
            port,
        };
        let resp = client.send_command("ping", json!({})).await.unwrap();
        assert_eq!(resp.get("success"), Some(&serde_json::Value::Bool(true)));
    }

    #[tokio::test]
    async fn mock_bridge_get_actors_parses_correctly() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        let _server = mock_bridge_server(port).await;
        tokio::time::sleep(Duration::from_millis(50)).await;

        let client = UnrealClient {
            host: "127.0.0.1".to_string(),
            port,
        };
        let actors = client.get_actors_in_level().await.unwrap();
        assert_eq!(actors.len(), 1);
        assert_eq!(actors[0].name, "cube_01");
    }

    #[tokio::test]
    async fn mock_bridge_spawn_and_find() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        let _server = mock_bridge_server(port).await;
        tokio::time::sleep(Duration::from_millis(50)).await;

        let client = UnrealClient {
            host: "127.0.0.1".to_string(),
            port,
        };
        let spawn_resp = client
            .spawn_actor(json!({"type": "StaticMeshActor"}))
            .await
            .unwrap();
        assert_eq!(
            spawn_resp.get("success"),
            Some(&serde_json::Value::Bool(true))
        );

        let find_resp = client.find_actor_by_mcp_id("cube_01").await.unwrap();
        assert_eq!(
            find_resp.get("success"),
            Some(&serde_json::Value::Bool(true))
        );
    }
}
