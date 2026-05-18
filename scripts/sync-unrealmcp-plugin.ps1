<#
.SYNOPSIS
    Synchronize Plugins\UnrealMCP between the canonical root copy and the
    source-built project's local copy.

.DESCRIPTION
    The repository hosts two Unreal projects that both depend on the UnrealMCP
    plugin:
        - FlopperamUnrealMCP\         (source-built engine, no EngineAssociation)
        - "FlopperamUnrealMCP 5.7"\   (UE 5.7 engine via marketplace launcher)

    Historically both projects pointed at .\Plugins\UnrealMCP via
    AdditionalPluginDirectories, which forces a full plugin rebuild every time
    you switch between projects (issue #2). To eliminate the rebuild churn the
    source-built project now keeps its own local copy at
    FlopperamUnrealMCP\Plugins\UnrealMCP. The canonical source of truth is the
    root copy at .\Plugins\UnrealMCP. This script keeps the two in sync.

.PARAMETER Reverse
    Sync FROM the source-built project copy back INTO the canonical root.
    Use this when you have edited inside FlopperamUnrealMCP\Plugins\UnrealMCP
    and want to promote those changes to the canonical root copy.

.PARAMETER Verify
    Do not copy. Instead compare the source files against the destination and
    fail (exit 2) if they differ. Useful in CI to detect drift.

.EXAMPLE
    .\scripts\sync-unrealmcp-plugin.ps1
    Copy root\Plugins\UnrealMCP -> FlopperamUnrealMCP\Plugins\UnrealMCP

.EXAMPLE
    .\scripts\sync-unrealmcp-plugin.ps1 -Reverse
    Copy FlopperamUnrealMCP\Plugins\UnrealMCP -> root\Plugins\UnrealMCP

.EXAMPLE
    .\scripts\sync-unrealmcp-plugin.ps1 -Verify
    Exit 2 if the two copies have diverged. CI may use this for guardrails.
#>
param(
    [switch]$Reverse,
    [switch]$Verify
)

$ErrorActionPreference = 'Stop'

# Resolve the repository root from this script's location (scripts\..)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..')).Path

$CanonicalDir   = Join-Path $RepoRoot 'Plugins\UnrealMCP'
$SourceBuiltDir = Join-Path $RepoRoot 'FlopperamUnrealMCP\Plugins\UnrealMCP'

if ($Reverse) {
    $SourceDir = $SourceBuiltDir
    $TargetDir = $CanonicalDir
} else {
    $SourceDir = $CanonicalDir
    $TargetDir = $SourceBuiltDir
}

if (-not (Test-Path -LiteralPath $SourceDir)) {
    Write-Error "Source directory does not exist: $SourceDir"
    exit 1
}

Write-Host "UnrealMCP plugin sync"
Write-Host "  source: $SourceDir"
Write-Host "  target: $TargetDir"
if ($Verify) { Write-Host "  mode  : VERIFY (no writes)" } else { Write-Host "  mode  : SYNC" }

# Files / directories we must NOT copy. These are build outputs and
# editor-generated artifacts that belong to the project that built them.
$ExcludeNames = @(
    'Binaries',
    'Build',
    'DerivedDataCache',
    'Intermediate',
    'Saved',
    '.vs',
    '.vsconfig'
)

function Should-Exclude {
    param([string]$RelativePath)
    foreach ($name in $ExcludeNames) {
        if ($RelativePath -eq $name) { return $true }
        if ($RelativePath -like "$name\*") { return $true }
    }
    return $false
}

# Build the file list relative to $SourceDir
$SourceFiles = Get-ChildItem -LiteralPath $SourceDir -Recurse -File -Force | Where-Object {
    $rel = $_.FullName.Substring($SourceDir.Length).TrimStart('\','/')
    -not (Should-Exclude $rel)
}

if (-not $Verify -and -not (Test-Path -LiteralPath $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

$copiedCount   = 0
$skippedCount  = 0
$mismatchCount = 0
$mismatches    = New-Object System.Collections.Generic.List[string]

foreach ($file in $SourceFiles) {
    $rel = $file.FullName.Substring($SourceDir.Length).TrimStart('\','/')
    $destPath = Join-Path $TargetDir $rel
    $destDir  = Split-Path $destPath -Parent

    if ($Verify) {
        if (-not (Test-Path -LiteralPath $destPath)) {
            $mismatchCount++
            [void]$mismatches.Add("MISSING in target: $rel")
            continue
        }
        $srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash
        $dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destPath).Hash
        if ($srcHash -ne $dstHash) {
            $mismatchCount++
            [void]$mismatches.Add("CHANGED in target: $rel")
        }
        continue
    }

    # Skip when target file already matches (cheaper than always copying).
    $needCopy = $true
    if (Test-Path -LiteralPath $destPath) {
        try {
            $srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash
            $dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destPath).Hash
            if ($srcHash -eq $dstHash) {
                $needCopy = $false
            }
        } catch {
            # If hashing fails for any reason, fall back to copying.
        }
    }

    if (-not $needCopy) {
        $skippedCount++
        continue
    }

    if (-not (Test-Path -LiteralPath $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $file.FullName -Destination $destPath -Force
    $copiedCount++
}

if ($Verify) {
    if ($mismatchCount -eq 0) {
        Write-Host "VERIFY OK: target matches source ($($SourceFiles.Count) files)."
        exit 0
    }
    Write-Warning "Drift detected ($mismatchCount file(s)):"
    foreach ($m in $mismatches) { Write-Warning "  $m" }
    exit 2
}

Write-Host ""
Write-Host "Sync complete."
Write-Host "  copied : $copiedCount"
Write-Host "  skipped: $skippedCount (already up-to-date)"

