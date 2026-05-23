<#
.SYNOPSIS
    Runs UE 5.7 RunUAT BuildPlugin against this repo's UnrealMCP plugin.

.DESCRIPTION
    234-stubs Wave 0.5 follow-up (umbrella: #69).

    Wraps RunUAT.bat BuildPlugin so every category PR can attach the same
    locally-produced log without re-deriving the command line. Sets up the
    output directory, captures both stdout and stderr to a timestamped log
    under `artifacts/local_uat/`, and prints a short summary at the end
    so the artifact path can be quoted in the PR description.

    Honours these inputs (in order of precedence):
        1. -UnrealEngineDir   (CLI arg)
        2. $env:UNREAL_ENGINE_57_DIR
        3. $env:UE_5_7_INSTALL_DIR
        4. C:\Program Files\Epic Games\UE_5.7   (default search)

.PARAMETER UnrealEngineDir
    Path to the UE 5.7 install root. Defaults to the env var above.

.PARAMETER Platforms
    Target platforms passed to BuildPlugin. Defaults to "Win64".

.PARAMETER OutputDir
    Directory that receives the packaged plugin. Defaults to
    `artifacts/local_uat/<timestamp>/UnrealMCP-Plugin`.

.PARAMETER LogPath
    Optional explicit log path. Defaults to
    `artifacts/local_uat/<timestamp>/runuat.log`.

.EXAMPLE
    pwsh -File scripts/run_local_uat_buildplugin.ps1
    pwsh -File scripts/run_local_uat_buildplugin.ps1 -UnrealEngineDir "D:\UE_5.7"
#>

[CmdletBinding()]
param(
    [string]$UnrealEngineDir,
    [string]$Platforms = "Win64",
    [string]$OutputDir,
    [string]$LogPath
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Resolve-UnrealEngineDir {
    param([string]$Explicit)
    if ($Explicit) { return $Explicit }
    if ($env:UNREAL_ENGINE_57_DIR) { return $env:UNREAL_ENGINE_57_DIR }
    if ($env:UE_5_7_INSTALL_DIR) { return $env:UE_5_7_INSTALL_DIR }
    $default = "C:\Program Files\Epic Games\UE_5.7"
    if (Test-Path $default) { return $default }
    throw "Could not locate UE 5.7. Set -UnrealEngineDir or \$env:UNREAL_ENGINE_57_DIR."
}

$engineDir = Resolve-UnrealEngineDir -Explicit $UnrealEngineDir
$runUat = Join-Path $engineDir "Engine\Build\BatchFiles\RunUAT.bat"
if (-not (Test-Path $runUat)) {
    throw "RunUAT.bat not found under '$engineDir'. Verify the UE 5.7 install."
}

$pluginFile = Join-Path $repoRoot "Plugins\UnrealMCP\UnrealMCP.uplugin"
if (-not (Test-Path $pluginFile)) {
    throw "UnrealMCP.uplugin not found at '$pluginFile'."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $repoRoot "artifacts\local_uat\$timestamp"
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

if (-not $OutputDir) {
    $OutputDir = Join-Path $runDir "UnrealMCP-Plugin"
}
if (-not $LogPath) {
    $LogPath = Join-Path $runDir "runuat.log"
}

Write-Host "Engine     : $engineDir"
Write-Host "Plugin     : $pluginFile"
Write-Host "Platforms  : $Platforms"
Write-Host "Output dir : $OutputDir"
Write-Host "Log file   : $LogPath"
Write-Host ""

$cmdArgs = @(
    "BuildPlugin",
    "-Plugin=$pluginFile",
    "-Package=$OutputDir",
    "-TargetPlatforms=$Platforms",
    "-Rocket"
)

# Tee everything to the log file while still streaming to the console.
& $runUat @cmdArgs 2>&1 | Tee-Object -FilePath $LogPath
$uatExit = $LASTEXITCODE

Write-Host ""
Write-Host "RunUAT BuildPlugin exit code: $uatExit"
Write-Host "Log saved to               : $LogPath"

if ($uatExit -ne 0) {
    Write-Error "BuildPlugin failed. See $LogPath for details."
    exit $uatExit
}

Write-Host "BuildPlugin succeeded. Attach the following to your PR description:"
Write-Host "  - $LogPath"
Write-Host "  - $OutputDir"
