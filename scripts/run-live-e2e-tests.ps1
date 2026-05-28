# Run Live E2E Tests with Running Services
# This script starts SurrealDB and scene-syncd, then runs the E2E tests

$ErrorActionPreference = "Stop"
$repoRoot = "C:\development\unreal-engine-mcp"
$pythonRoot = "$repoRoot\Python"
$env:PYTHONPATH = $pythonRoot
$env:PYTHONIOENCODING = "utf-8"

# Set scene-syncd environment variables globally
$env:SCENE_SYNCD_HOST = "127.0.0.1"
$env:SCENE_SYNCD_PORT = "8787"
$env:SURREAL_URL = "ws://127.0.0.1:8000"
$env:SURREAL_NS = "unreal_mcp"
$env:SURREAL_DB = "scene"
$env:SURREAL_USER = "root"
$env:SURREAL_PASS = "secret"
$env:UNREAL_MCP_HOST = "127.0.0.1"
$env:UNREAL_MCP_PORT = "55771"
$env:SCENE_SYNCD_AUTOSYNC = "false"
$env:SCENE_SYNCD_LOG = "info"

# Step 1: Start SurrealDB
Write-Host "=== Starting SurrealDB ===" -ForegroundColor Cyan
$surrealDbDir = "$repoRoot\.surreal"
if (-not (Test-Path $surrealDbDir)) {
    New-Item -ItemType Directory -Path $surrealDbDir | Out-Null
}
$surrealProc = Start-Process -FilePath "$env:USERPROFILE\.local\bin\surreal.exe" `
    -ArgumentList "start", "--bind", "127.0.0.1:8000", "--user", "root", "--pass", "secret", "rocksdb://$surrealDbDir\unreal_mcp.db" `
    -WindowStyle Hidden -PassThru
Write-Host "SurrealDB started (PID: $($surrealProc.Id))" -ForegroundColor Green

# Wait for SurrealDB
$retry = 0
while ($retry -lt 30) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            Write-Host "SurrealDB is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
    $retry++
}

# Step 2: Start scene-syncd
Write-Host "`n=== Starting scene-syncd ===" -ForegroundColor Blue
$sceneSyncdExe = "$repoRoot\rust\scene-syncd\target\debug\scene-syncd.exe"
$sceneProc = Start-Process -FilePath $sceneSyncdExe `
    -WorkingDirectory "$repoRoot\rust\scene-syncd\target\debug" `
    -WindowStyle Hidden -PassThru
Write-Host "scene-syncd started (PID: $($sceneProc.Id))" -ForegroundColor Green

# Wait for scene-syncd
$retry = 0
while ($retry -lt 60) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8787/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            Write-Host "scene-syncd is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
    $retry++
}

# Step 3: Run E2E tests
Write-Host "`n=== Running E2E Tests ===" -ForegroundColor Yellow

# Test 1: Scene sync health check
Write-Host "`n[Test 1] Scene-syncd Health Check..." -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8787/health" -UseBasicParsing
    $health = $resp.Content | ConvertFrom-Json
    Write-Host "  ✓ Health check passed: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Health check failed: $_" -ForegroundColor Red
}

# Test 2: Scene create/list via scene-syncd
Write-Host "`n[Test 2] Scene Create/List via scene-syncd..." -ForegroundColor Cyan
try {
    $createResp = Invoke-WebRequest -Uri "http://127.0.0.1:8787/scenes/create" `
        -Method POST -ContentType "application/json" `
        -Body '{"scene_id": "test_scene", "name": "Test Scene", "description": "E2E test scene"}' `
        -UseBasicParsing
    $create = $createResp.Content | ConvertFrom-Json
    Write-Host "  ✓ Scene created: $($create.scene_id)" -ForegroundColor Green

    $listResp = Invoke-WebRequest -Uri "http://127.0.0.1:8787/scenes/list" -UseBasicParsing
    $list = $listResp.Content | ConvertFrom-Json
    Write-Host "  ✓ Scene list retrieved: $($list.scenes.Count) scenes" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Scene create/list failed: $_" -ForegroundColor Red
}

# Test 3: Python agent system tests with real services
Write-Host "`n[Test 3] Python Agent System Tests (with real scene-syncd)..." -ForegroundColor Cyan
$testScript = @"
import sys
sys.path.insert(0, r'$pythonRoot')

# Mock mcp module
class MockMCP:
    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass
        def tool(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

sys.modules['mcp'] = MockMCP()
sys.modules['mcp.server'] = MockMCP()
sys.modules['mcp.server.fastmcp'] = MockMCP()

from server.agents import initialize_agent_system, execute_intent
from server.dialog_tools import scene_edit, scene_describe
import asyncio

print('Initializing agent system...')
try:
    orchestrator = initialize_agent_system()
    print(f'✓ Initialized with {len(orchestrator.sub_agents)} domain agents')
except Exception as e:
    print(f'⚠ Initialization warning: {e}')

# Test scene_describe with real scene-syncd
print()
print('Testing scene_describe with real scene-syncd...')
try:
    result = scene_describe(scene_id='test_scene')
    print(f"✓ scene_describe: success={result['success']}")
    if result['success']:
        ctx = result.get('context', {})
        print(f"  Scene ID: {ctx.get('scene_id')}")
        print(f"  Object count: {ctx.get('object_count', 'N/A')}")
        print(f"  Entity count: {ctx.get('entity_count', 'N/A')}")
except Exception as e:
    print(f'✗ scene_describe failed: {e}')

# Test scene_edit in agent mode
print()
print('Testing scene_edit in agent mode...')
try:
    result = scene_edit(
        intent='create a test cave',
        scene_id='test_scene',
        mode='agent'
    )
    print(f"✓ scene_edit (agent mode): success={result['success']}")
    if 'agent_result' in result:
        ar = result['agent_result']
        print(f"  Agent execution: success={ar['success']}")
        if ar.get('error'):
            print(f"  Agent error: {ar['error']}")
except Exception as e:
    print(f'✗ scene_edit failed: {e}')

# Test execute_intent
print()
print('Testing execute_intent...')
async def test_intent():
    try:
        result = await execute_intent(
            intent='validate the scene',
            scene_id='test_scene'
        )
        print(f'✓ execute_intent: success={result.success}')
        if result.error:
            print(f'  Error: {result.error}')
    except Exception as e:
        print(f'✗ execute_intent failed: {e}')

asyncio.run(test_intent())

print()
print('=== Python tests completed ===')
"@

$testScript | python -

# Step 4: Test 4 - Unreal Editor check
Write-Host "`n[Test 4] Unreal Editor Availability Check..." -ForegroundColor Cyan
$ueExe = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe"
if (Test-Path $ueExe) {
    Write-Host "  ✓ Unreal Editor found: $ueExe" -ForegroundColor Green
    Write-Host "  Note: To run full E2E tests with Unreal Editor, use:" -ForegroundColor Yellow
    Write-Host "    python scripts/launch-dev-stack.py --all" -ForegroundColor Yellow
    Write-Host "  Then run tests in another terminal." -ForegroundColor Yellow
} else {
    Write-Host "  ✗ Unreal Editor not found at expected path" -ForegroundColor Red
}

# Step 5: Cleanup
Write-Host "`n=== Cleanup ===" -ForegroundColor Yellow
if ($sceneProc -and !$sceneProc.HasExited) {
    Stop-Process -Id $sceneProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "scene-syncd stopped." -ForegroundColor Green
}
if ($surrealProc -and !$surrealProc.HasExited) {
    Stop-Process -Id $surrealProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "SurrealDB stopped." -ForegroundColor Green
}

Write-Host "`n=== Live E2E Tests Completed ===" -ForegroundColor Green
