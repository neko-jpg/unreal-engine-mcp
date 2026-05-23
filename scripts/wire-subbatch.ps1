param(
  [Parameter(Mandatory=$true)][string]$HandlerClass,
  [Parameter(Mandatory=$true)][int]$RouteId,
  [Parameter(Mandatory=$true)][string]$Module,
  [Parameter(Mandatory=$true)][string]$Comment,
  [Parameter(Mandatory=$true)][string]$PrevIncludeHeader,
  [Parameter(Mandatory=$true)][int]$PrevRouteId,
  [Parameter(Mandatory=$true)][string]$PrevModule,
  [Parameter(Mandatory=$true)][string]$PrevSubBatchLabel,
  [Parameter(Mandatory=$true)][string]$CommandsCsv,
  [Parameter(Mandatory=$true)][string]$RouterPrevLastCommand
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$Commands = $CommandsCsv.Split(',')

$bridge = "$root\Plugins\UnrealMCP\Source\UnrealMCP\Private\EpicUnrealMCPBridge.cpp"
$c = Get-Content $bridge -Raw
$newInclude = "#include `"Commands/$HandlerClass.h`""
if (-not $c.Contains("$HandlerClass.h")) {
  $prevInclude = "#include `"Commands/$PrevIncludeHeader`""
  $c = $c.Replace($prevInclude, $prevInclude + "`r`n" + $newInclude)
  $prevReg = "    RegisterHandler<F$($PrevIncludeHeader -replace '\.h$','')>($PrevRouteId);"
  $insertAt = $c.IndexOf($prevReg); $eol = $c.IndexOf("`n", $insertAt) + 1
  $newReg = "    RegisterHandler<F$HandlerClass>($RouteId); // $Comment`r`n"
  $c = $c.Insert($eol, $newReg)
  Set-Content -Path $bridge -Value $c -Encoding UTF8 -NoNewline
  Write-Host "Bridge: added include + register $HandlerClass@$RouteId"
}

$router = "$root\Plugins\UnrealMCP\Source\UnrealMCP\Private\Commands\EpicUnrealMCPRouter.cpp"
$rc = Get-Content $router -Raw
$marker = "{TEXT(`"$RouterPrevLastCommand`"), $PrevRouteId},"
if ($rc.Contains($marker) -and -not $rc.Contains("// ---- $Comment ----")) {
  $add = "`r`n        // ---- $Comment ----`r`n"
  foreach ($cmd in $Commands) { $add += "        {TEXT(`"$cmd`"), $RouteId},`r`n" }
  $rc = $rc.Replace($marker, $marker + $add)
  Set-Content -Path $router -Value $rc -Encoding UTF8 -NoNewline
  Write-Host "Router: added $($Commands.Count) entries on route $RouteId"
}

$bs = "$root\Python\server\__init__.py"
$bc = Get-Content $bs -Raw
$prevLine = "    from server import $PrevModule"
if (-not $bc.Contains("from server import $Module")) {
  $newLine = "    from server import $PrevModule"
  # Append the new module on a new line right after the prev line (we add at end of full prev module line, including comment).
  # Find the line containing prevLine and add after the entire line.
  $idx = $bc.IndexOf($prevLine)
  $eol = $bc.IndexOf("`n", $idx) + 1
  $padded = $Module.PadRight(28)
  $bc = $bc.Insert($eol, "    from server import $padded # noqa: F401  $PrevSubBatchLabel`r`n")
  Set-Content -Path $bs -Value $bc -Encoding UTF8 -NoNewline
  Write-Host "Bootstrap: added $Module"
}

$tp = "$root\Python\tests\unit\test_tool_registration_and_mapping.py"
$tc = Get-Content $tp -Raw
if (-not $tc.Contains("$Module,")) {
  $tc = $tc.Replace("$PrevModule,", "$PrevModule, $Module,")
  Set-Content -Path $tp -Value $tc -Encoding UTF8 -NoNewline
  Write-Host "Test patches: added $Module"
}

Write-Host "Done wiring $HandlerClass."
