#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR/rust/scene-syncd"

export SCENE_SYNCD_HOST=${SCENE_SYNCD_HOST:-127.0.0.1}
export SCENE_SYNCD_PORT=${SCENE_SYNCD_PORT:-8787}
export SURREAL_URL=${SURREAL_URL:-ws://127.0.0.1:8000}
export SURREAL_NS=${SURREAL_NS:-unreal_mcp}
export SURREAL_DB=${SURREAL_DB:-scene}
export SURREAL_USER=${SURREAL_USER:-root}
export SURREAL_PASS=${SURREAL_PASS:-secret}
export UNREAL_MCP_HOST=${UNREAL_MCP_HOST:-127.0.0.1}
export UNREAL_MCP_PORT=${UNREAL_MCP_PORT:-55557}
export SCENE_SYNCD_AUTOSYNC=${SCENE_SYNCD_AUTOSYNC:-false}
export SCENE_SYNCD_LOG=${SCENE_SYNCD_LOG:-info}

echo "Starting scene-syncd on ${SCENE_SYNCD_HOST}:${SCENE_SYNCD_PORT}"
cargo run