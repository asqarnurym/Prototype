param(
    [switch]$Dev,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\\python.exe"
$requirementsFile = if ($Dev) { "requirements-dev.txt" } else { "requirements.txt" }
$profile = if ($Dev) { "dev" } else { "runtime" }

$pythonVersion = & py -3.12 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 launcher is unavailable. Install Python 3.12.10 first."
}

if ($pythonVersion -ne "3.12.10") {
    throw "Expected Python 3.12.10, found $pythonVersion. Install the exact version pinned in .python-version."
}

if (-not (Test-Path $venvPython)) {
    & py -3.12 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment at $venvPath."
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip inside $venvPath."
}

& $venvPython -m pip install --require-hashes -r (Join-Path $projectRoot $requirementsFile)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install locked dependencies from $requirementsFile."
}

if (-not $SkipVerify) {
    & $venvPython (Join-Path $projectRoot "scripts\\verify_environment.py") --profile $profile
    if ($LASTEXITCODE -ne 0) {
        throw "Environment verification failed for profile '$profile'."
    }
}

Write-Host "Environment is ready: $venvPath ($profile)"
