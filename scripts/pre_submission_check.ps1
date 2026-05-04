param(
    [string]$TexEntry = "academic_paper/main_full.tex",
    [int]$MaxPages = 8,
    [switch]$AllowOverPageLimit
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

$sanityScript = Join-Path $projectRoot "scripts\paper_sanity_check.py"
$buildScript = Join-Path $projectRoot "scripts\build_paper.ps1"

Write-Host "▶ Running paper sanity checks..."
& $pythonExe $sanityScript --paper-dir (Join-Path $projectRoot "academic_paper")
if ($LASTEXITCODE -ne 0) {
    throw "Paper sanity check failed."
}

Write-Host "▶ Building manuscript PDF..."
$buildArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $buildScript,
    "-TexEntry", $TexEntry,
    "-MaxPages", $MaxPages
)
if ($AllowOverPageLimit) {
    $buildArgs += "-AllowOverPageLimit"
}

powershell @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Paper build failed."
}

Write-Host "[PASS] Pre-submission check completed successfully."
