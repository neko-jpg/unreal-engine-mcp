use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub surreal_url: String,
    pub surreal_ns: String,
    pub surreal_db: String,
    pub surreal_user: String,
    pub surreal_pass: String,
    pub unreal_host: String,
    pub unreal_port: u16,
    #[allow(dead_code)]
    pub autosync: bool,
    pub log_level: String,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            host: env_or("SCENE_SYNCD_HOST", "127.0.0.1"),
            port: env_or_parse("SCENE_SYNCD_PORT", 8787),
            surreal_url: env_or("SURREAL_URL", "ws://127.0.0.1:8000"),
            surreal_ns: env_or("SURREAL_NS", "unreal_mcp"),
            surreal_db: env_or("SURREAL_DB", "scene"),
            surreal_user: env_or("SURREAL_USER", "root"),
            surreal_pass: env_or("SURREAL_PASS", ""),
            unreal_host: env_or("UNREAL_MCP_HOST", "127.0.0.1"),
            unreal_port: env_or_parse("UNREAL_MCP_PORT", 55557),
            autosync: env_or_parse("SCENE_SYNCD_AUTOSYNC", false),
            log_level: env_or("SCENE_SYNCD_LOG", "info"),
        }
    }

    pub fn bind_addr(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }

    #[allow(dead_code)]
    pub fn unreal_addr(&self) -> String {
        format!("{}:{}", self.unreal_host, self.unreal_port)
    }
}

fn env_or(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

fn env_or_parse<T: std::str::FromStr>(key: &str, default: T) -> T {
    env::var(key)
        .ok()
        .and_then(|v| match v.parse() {
            Ok(parsed) => Some(parsed),
            Err(_) => {
                eprintln!(
                    "Warning: failed to parse environment variable {key}='{v}', using default"
                );
                None
            }
        })
        .unwrap_or(default)
}
