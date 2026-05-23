# Unreal MCP プロジェクト タスクランナー
# インストール: https://just.systems/man/en/chapter_4.html
# 使い方: just <command>

# ── ヘルプ（デフォルトタスク） ──
_default:
    @just --list

# ═══════════════════════════════════════════
# Python
# ═══════════════════════════════════════════

# Python 依存関係をインストール
install-python:
    cd Python && uv sync --extra dev

# Python リンター & フォーマッタ (Ruff)
lint-python:
    cd Python && uv run ruff check server helpers scripts --fix && uv run ruff format server helpers scripts

# Python 型チェック (mypy)
typecheck-python:
    cd Python && uv run mypy server helpers

# Python 単体テスト
test-python-unit:
    cd Python && uv run pytest tests/unit tests/contract -v --tb=short

# Python 全テスト（E2E 除く）
test-python:
    cd Python && uv run pytest tests/unit tests/contract tests/e2e --skip-unreal -v

# Python 全テスト + カバレッジ
test-python-cov:
    cd Python && uv run pytest tests/unit tests/contract tests/e2e --skip-unreal -v --cov --cov-report=term --cov-report=xml

# ═══════════════════════════════════════════
# Rust
# ═══════════════════════════════════════════

# Rust テスト
test-rust:
    cd rust/scene-syncd && cargo test

# Rust リンター & フォーマッタ
lint-rust:
    cd rust/scene-syncd && cargo fmt --check && cargo clippy --all-targets --all-features -- -D warnings

# Rust リリースビルド
build-rust-release:
    cd rust/scene-syncd && cargo build --release

# Rust ベンチマーク
bench-rust:
    cd rust/scene-syncd && cargo bench

# Rust 未使用依存関係チェック
udeps-rust:
    cd rust/scene-syncd && cargo +nightly udeps 2>/dev/null || echo "cargo-udeps requires nightly toolchain"

# ═══════════════════════════════════════════
# 全言語共通
# ═══════════════════════════════════════════

# 全リンター／フォーマッタを実行
lint: lint-python lint-rust

# 全テストを実行
test: test-python test-rust

# Pre-commit フックを全ファイルに実行
precommit:
    pre-commit run --all-files

# ═══════════════════════════════════════════
# コード生成
# ═══════════════════════════════════════════

# Codegen: Router とボイラープレートを生成
codegen:
    cd Python && uv run tools/generate_codegen.py

# Codegen が最新かチェック（CI 用）
codegen-check:
    cd Python && uv run tools/generate_codegen.py --check

# ═══════════════════════════════════════════
# 開発スタック
# ═══════════════════════════════════════════

# 開発スタックを起動（Full Stack）
dev-stack:
    python scripts/launch-dev-stack.py --all

# SurrealDB を起動
dev-db:
    python scripts/launch-dev-stack.py --surreal

# scene-syncd を起動
dev-scene-syncd:
    python scripts/launch-dev-stack.py --scene-syncd

# ═══════════════════════════════════════════
# セキュリティ
# ═══════════════════════════════════════════

# Gitleaks: シークレット漏洩スキャン
scan-secrets:
    gitleaks detect --config=.gitleaks.toml --verbose

# Bandit: Python セキュリティスキャン
scan-bandit:
    cd Python && uv run bandit -c pyproject.toml server helpers

# cargo-audit: Rust 依存関係の脆弱性チェック
audit-rust:
    cd rust/scene-syncd && cargo audit

# cargo-deny: Rust ライセンス + アドバイザリチェック
deny-rust:
    cd rust/scene-syncd && cargo deny check --all-features

# ═══════════════════════════════════════════
# 未使用依存関係
# ═══════════════════════════════════════════

# deptry: Python 未使用依存関係チェック
udeps-python:
    cd Python && uv run deptry .

# ═══════════════════════════════════════════
# ドキュメント
# ═══════════════════════════════════════════

# mdbook: ドキュメントビルド
build-docs:
    mdbook build docs/guide 2>/dev/null || echo "mdbook not installed, skipping"

# lychee: リンク切れチェック
check-links:
    lychee --verbose --no-progress --exclude 'localhost' --exclude '127.0.0.1' **/*.md .github/**/*.md

# ═══════════════════════════════════════════
# CI
# ═══════════════════════════════════════════

# CI と同じ検証をローカルで実行
ci: lint codegen-check test-python test-rust scan-secrets
    @echo "✓ CI equivalent passed"

# フル CI（全チェック）
ci-full: ci scan-bandit audit-rust deny-rust check-links udeps-python
    @echo "✓ Full CI passed"

# ═══════════════════════════════════════════
# クリーンアップ
# ═══════════════════════════════════════════

# Python キャッシュを削除
clean-pycache:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
    find . -type f -name '*.pyc' -delete

# Rust ビルドをクリーン
clean-rust:
    cd rust/scene-syncd && cargo clean

# 全クリーン
clean: clean-pycache clean-rust
