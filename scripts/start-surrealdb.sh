#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

mkdir -p "$ROOT_DIR/.surreal"

echo "Starting SurrealDB server at ws://127.0.0.1:8000"
surreal start --user root --pass secret --bind 127.0.0.1:8000 rocksdb://"$ROOT_DIR/.surreal/unreal_mcp.db"