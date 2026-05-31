param(
    [switch]$Dev,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$profile = if ($Dev) { "dev" } else { "runtime" }
$pythonVersionFile = Join-Path $projectRoot ".python-version"

# Read pinned Python version
$pinnedVersion = Get-Content $pythonVersionFile -Raw
$pinnedVersion = $pinnedVersion.Trim()

$pythonVersion = & py -3.12 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 launcher is unavailable. Install Python ${pinnedVersion} first."
}

# Allow any 3.12.x patch, warn on mismatch
if ($pythonVersion -notmatch "^3\.12\.") {
    throw "Expected Python 3.12.x, found $pythonVersion. Install Python ${pinnedVersion}."
}
if ($pythonVersion -ne $pinnedVersion) {
    Write-Warning "Python $pythonVersion (pinned: $pinnedVersion). This is usually fine for development."
}

if (-not (Test-Path $venvPython)) {
    & py -3.12 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment at $venvPath."
    }
}

# Install via uv (project uses pyproject.toml + uv.lock)
$uvInstall = if ($Dev) { "uv sync --all-extras" } else { "uv sync" }
Write-Host "Running: $uvInstall"
Invoke-Expression $uvInstall
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install dependencies via uv sync."
}

if (-not $SkipVerify) {
    & $venvPython (Join-Path $projectRoot "scripts\verify_environment.py") --profile $profile
    if ($LASTEXITCODE -ne 0) {
        throw "Environment verification failed for profile '$profile'."
    }
}

Write-Host "Environment is ready: $venvPath ($profile)"
