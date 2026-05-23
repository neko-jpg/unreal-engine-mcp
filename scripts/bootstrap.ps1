# Unreal MCP プロジェクト ブートストラップスクリプト
# 使い方: PowerShell で右クリック → Run with PowerShell または:
#   powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Unreal MCP - Development Bootstrap         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

# ── 1. Python ──
Write-Host "[1/6] Python environment..." -ForegroundColor Green
Push-Location "$RepoRoot/Python"
try {
    # Check if uv is installed
    $uv = Get-Command "uv" -ErrorAction SilentlyContinue
    if (-not $uv) {
        Write-Host "  Installing uv (Python package manager)..." -ForegroundColor Yellow
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    }
    Write-Host "  Running uv sync..." -ForegroundColor Yellow
    uv sync --extra dev
    Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
} finally {
    Pop-Location
}

# ── 2. Pre-commit ──
Write-Host "[2/6] Pre-commit hooks..." -ForegroundColor Green
try {
    $precommit = Get-Command "pre-commit" -ErrorAction SilentlyContinue
    if (-not $precommit) {
        pip install pre-commit
    }
    Push-Location $RepoRoot
    pre-commit install --hook-type pre-commit --hook-type commit-msg
    Write-Host "  ✓ Pre-commit hooks installed" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Skipped (python not available): $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

# ── 3. Rust ──
Write-Host "[3/6] Rust toolchain..." -ForegroundColor Green
try {
    $rustc = Get-Command "rustc" -ErrorAction SilentlyContinue
    if (-not $rustc) {
        Write-Host "  Installing Rust via rustup..." -ForegroundColor Yellow
        # rustup-init をダウンロードして実行 (non-interactive)
        $temp = "$env:TEMP\rustup-init.exe"
        Invoke-WebRequest -Uri "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe" -OutFile $temp
        & $temp -y --default-toolchain stable
        Remove-Item $temp
    }
    rustup component add clippy rustfmt
    Write-Host "  ✓ Rust toolchain ready" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Skipped: $_" -ForegroundColor Yellow
}

# ── 4. Just (タスクランナー) ──
Write-Host "[4/6] Just task runner..." -ForegroundColor Green
try {
    $just = Get-Command "just" -ErrorAction SilentlyContinue
    if (-not $just) {
        Write-Host "  Installing just..." -ForegroundColor Yellow
        # Chocolatey 経由でインストール
        if (Get-Command "choco" -ErrorAction SilentlyContinue) {
            choco install just
        } elseif (Get-Command "winget" -ErrorAction SilentlyContinue) {
            winget install Casey.Just
        } else {
            Write-Host "  ⚠ Install just manually: https://just.systems/man/en/chapter_4.html" -ForegroundColor Yellow
        }
    }
    if (Get-Command "just" -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ Just installed" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Skipped: $_" -ForegroundColor Yellow
}

# ── 5. direnv ──
Write-Host "[5/6] direnv..." -ForegroundColor Green
try {
    $direnv = Get-Command "direnv" -ErrorAction SilentlyContinue
    if (-not $direnv) {
        Write-Host "  ⚠ Install direnv manually: https://direnv.net/" -ForegroundColor Yellow
        Write-Host "    Then run: direnv allow" -ForegroundColor Yellow
    } else {
        Push-Location $RepoRoot
        direnv allow
        Write-Host "  ✓ direnv configured" -ForegroundColor Green
        Pop-Location
    }
} catch {
    Write-Host "  ⚠ Skipped: $_" -ForegroundColor Yellow
}

# ── 6. Codegen ──
Write-Host "[6/6] Codegen..." -ForegroundColor Green
try {
    Push-Location "$RepoRoot/Python"
    uv run python tools/generate_codegen.py
    Write-Host "  ✓ Codegen output generated" -ForegroundColor Green
    Pop-Location
} catch {
    Write-Host "  ⚠ Skipped: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Bootstrap complete!                          ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Quick commands:                              ║" -ForegroundColor Cyan
Write-Host "║    just lint       # Lint all code            ║" -ForegroundColor Cyan
Write-Host "║    just test       # Run all tests             ║" -ForegroundColor Cyan
Write-Host "║    just ci         # CI equivalent             ║" -ForegroundColor Cyan
Write-Host "║    just codegen    # Regenerate codegen        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
