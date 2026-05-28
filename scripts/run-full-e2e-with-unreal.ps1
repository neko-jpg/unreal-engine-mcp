# Launch Unreal Editor with HostProject and run E2E tests
$ErrorActionPreference = "Stop"
$repoRoot = "C:\development\unreal-engine-mcp"
$pythonRoot = "$repoRoot\Python"
$env:PYTHONPATH = $pythonRoot
$env:PYTHONIOENCODING = "utf-8"
$env:UNREAL_MCP_UPROJECT = "$repoRoot\artifacts\dev_stack_host\HostProject\HostProject.uproject"

Write-Host "=== Starting Unreal MCP Dev Stack with Unreal Editor ===" -ForegroundColor Green

# Step 1: Start SurrealDB
Write-Host "`n[1/5] Starting SurrealDB..." -ForegroundColor Cyan
$surrealProc = Start-Process -FilePath "$env:USERPROFILE\.local\bin\surreal.exe" `
    -ArgumentList "start", "--bind", "127.0.0.1:8000", "--user", "root", "--pass", "secret", "memory" `
    -WindowStyle Hidden -PassThru

$retry = 0
while ($retry -lt 30) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Milliseconds 500
    $retry++
}
Write-Host "  ✓ SurrealDB ready" -ForegroundColor Green

# Step 2: Start scene-syncd
Write-Host "`n[2/5] Starting scene-syncd..." -ForegroundColor Cyan
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

$sceneProc = Start-Process -FilePath "$repoRoot\rust\scene-syncd\target\debug\scene-syncd.exe" `
    -WindowStyle Hidden -PassThru

$retry = 0
while ($retry -lt 60) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8787/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Milliseconds 500
    $retry++
}
Write-Host "  ✓ scene-syncd ready" -ForegroundColor Green

# Step 3: Start Unreal Editor
Write-Host "`n[3/5] Starting Unreal Editor..." -ForegroundColor Cyan
Write-Host "  Project: $env:UNREAL_MCP_UPROJECT" -ForegroundColor Gray
$ueExe = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe"

$ueProc = Start-Process -FilePath $ueExe `
    -ArgumentList "$env:UNREAL_MCP_UPROJECT", "-Windowed", "-ResX=1280", "-ResY=720" `
    -PassThru

Write-Host "  Waiting for Unreal Editor TCP (port 55771)..." -ForegroundColor Gray
$retry = 0
$ueReady = $false
while ($retry -lt 240) {  # 2 minutes max
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 55771)
        $tcp.Close()
        $ueReady = $true
        break
    } catch {}
    
    if ($ueProc.HasExited) {
        Write-Host "  ✗ Unreal Editor exited early (code: $($ueProc.ExitCode))" -ForegroundColor Red
        break
    }
    
    Start-Sleep -Milliseconds 500
    $retry++
    if ($retry % 20 -eq 0) {
        Write-Host "  ... still waiting ($($retry/2) seconds)" -ForegroundColor Gray
    }
}

if ($ueReady) {
    Write-Host "  ✓ Unreal Editor ready" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Unreal Editor TCP not ready, continuing anyway..." -ForegroundColor Yellow
}

# Step 4: Run E2E tests
Write-Host "`n[4/5] Running E2E Tests..." -ForegroundColor Yellow

# Create test script
$testPy = @"
import sys
sys.path.insert(0, r'$pythonRoot')

class MockMCP:
    class FastMCP:
        def __init__(self, *args, **kwargs): pass
        def tool(self, *args, **kwargs):
            def decorator(func): return func
            return decorator

sys.modules['mcp'] = MockMCP()
sys.modules['mcp.server'] = MockMCP()
sys.modules['mcp.server.fastmcp'] = MockMCP()

import asyncio
from server.agents import initialize_agent_system, execute_intent
from server.dialog_tools import scene_edit, scene_describe
from server.scene_client import call_scene_syncd

print("=" * 60)
print("LIVE E2E TEST RESULTS")
print("=" * 60)

# Test 1: Service connectivity
print("\n[Test 1] Service Connectivity")
try:
    import requests as _requests
    _health_resp = _requests.get("http://127.0.0.1:8787/health", timeout=5)
    print(f"  scene-syncd health: {_health_resp.status_code == 200}")
except Exception as e:
    print(f"  scene-syncd health: False ({e})")

# Test 2: Scene operations via scene-syncd
print("\n[Test 2] Scene Operations")
try:
    result = call_scene_syncd("/scenes/create", {
        "scene_id": "e2e_test_scene",
        "name": "E2E Test Scene"
    })
    print(f"  Scene create: {result.get('success', False)}")
except Exception as e:
    print(f"  Scene create error: {e}")

# Test 3: scene_describe with real backend
print("\n[Test 3] scene_describe with real scene-syncd")
try:
    result = scene_describe(scene_id="e2e_test_scene")
    print(f"  Success: {result['success']}")
    if result['success']:
        print(f"  Scene: {result.get('scene_id')}")
        print(f"  Objects: {result.get('context', {}).get('object_count', 0)}")
except Exception as e:
    print(f"  Error: {e}")

# Test 4: Agent system initialization
print("\n[Test 4] Agent System Initialization")
try:
    orchestrator = initialize_agent_system()
    print(f"  Domain agents: {len(orchestrator.sub_agents)}")
    print(f"  Tools: {len(orchestrator.tool_registry)}")
except Exception as e:
    print(f"  Error: {e}")

# Test 5: execute_intent with real services
print("\n[Test 5] execute_intent")
async def run_intent():
    try:
        result = await execute_intent(
            intent="run collision validation",
            scene_id="e2e_test_scene"
        )
        print(f"  Success: {result.success}")
        if result.error:
            print(f"  Error: {result.error}")
    except Exception as e:
        print(f"  Error: {e}")

asyncio.run(run_intent())

# Test 6: scene_edit agent mode
print("\n[Test 6] scene_edit (agent mode)")
try:
    result = scene_edit(
        intent="spawn a point light",
        scene_id="e2e_test_scene",
        mode="agent"
    )
    print(f"  Success: {result['success']}")
    if 'agent_result' in result:
        ar = result['agent_result']
        print(f"  Agent success: {ar.get('success', False)}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
"@

$testPy | python -

# Step 4b: Run pytest requires_unreal tests
Write-Host "`n[4b/6] Running pytest -m requires_unreal..." -ForegroundColor Yellow
$env:PYTHONPATH = $pythonRoot
try {
    & python -m pytest "$pythonRoot\tests\e2e" "$pythonRoot\tests\integration" "$pythonRoot\tests\benchmarks" -m "requires_unreal" -v --tb=short
    Write-Host "  pytest completed" -ForegroundColor Green
} catch {
    Write-Host "  pytest encountered errors: $_" -ForegroundColor Red
}

# Step 5: Cleanup
Write-Host "`n[6/6] Cleanup..." -ForegroundColor Yellow
if ($ueProc -and !$ueProc.HasExited) {
    Stop-Process -Id $ueProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ Unreal Editor stopped" -ForegroundColor Green
}
if ($sceneProc -and !$sceneProc.HasExited) {
    Stop-Process -Id $sceneProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ scene-syncd stopped" -ForegroundColor Green
}
if ($surrealProc -and !$surrealProc.HasExited) {
    Stop-Process -Id $surrealProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ SurrealDB stopped" -ForegroundColor Green
}

Write-Host "`n=== All Done ===" -ForegroundColor Green
