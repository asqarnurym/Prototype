param(
    [string]$TexEntry = "academic_paper/main_full.tex",
    [int]$MaxPages = 8,
    [switch]$AllowOverPageLimit
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$texEntryPath = Join-Path $projectRoot $TexEntry

if (-not (Test-Path $texEntryPath)) {
    throw "TeX entrypoint not found: $texEntryPath"
}

$paperDir = Split-Path -Parent $texEntryPath
$texFile = Split-Path -Leaf $texEntryPath
$stem = [System.IO.Path]::GetFileNameWithoutExtension($texFile)

function Resolve-Tool {
    param([Parameter(Mandatory = $true)][string]$Name)

    $fromPath = Get-Command $Name -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $miktex = Join-Path $env:LOCALAPPDATA ("Programs\MiKTeX\miktex\bin\x64\" + $Name + ".exe")
    if (Test-Path $miktex) {
        return $miktex
    }

    throw "Tool '$Name' is not available. Install MiKTeX/TeX CLI first."
}

function Run-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$Label
    )

    Write-Host "▶ $Label"
    & $Exe @Args
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

$pdflatex = Resolve-Tool -Name "pdflatex"
$bibtex = Resolve-Tool -Name "bibtex"
$pdfinfo = Resolve-Tool -Name "pdfinfo"

Push-Location $paperDir
try {
    Run-Step -Exe $pdflatex -Args @("-interaction=nonstopmode", "-file-line-error", $texFile) -Label "pdflatex (pass 1)"
    Run-Step -Exe $bibtex -Args @($stem) -Label "bibtex"
    Run-Step -Exe $pdflatex -Args @("-interaction=nonstopmode", "-file-line-error", $texFile) -Label "pdflatex (pass 2)"
    Run-Step -Exe $pdflatex -Args @("-interaction=nonstopmode", "-file-line-error", $texFile) -Label "pdflatex (pass 3)"

    $pdfPath = Join-Path $paperDir ($stem + ".pdf")
    if (-not (Test-Path $pdfPath)) {
        throw "Expected output PDF was not created: $pdfPath"
    }

    $pdfMeta = & $pdfinfo $pdfPath
    if ($LASTEXITCODE -ne 0) {
        throw "pdfinfo failed for $pdfPath"
    }

    $pagesLine = $pdfMeta | Where-Object { $_ -match "^Pages:\s+\d+$" } | Select-Object -First 1
    if (-not $pagesLine) {
        throw "Could not parse page count from pdfinfo output."
    }
    $pages = [int]([regex]::Match($pagesLine, "^Pages:\s+(\d+)$").Groups[1].Value)

    if (-not $AllowOverPageLimit -and $pages -gt $MaxPages) {
        throw "Page limit exceeded: $pages pages (max allowed: $MaxPages)."
    }

    $logPath = Join-Path $paperDir ($stem + ".log")
    if (-not (Test-Path $logPath)) {
        throw "Expected build log was not produced: $logPath"
    }

    $logText = Get-Content $logPath -Raw
    $undefinedPatterns = @(
        "LaTeX Warning: Citation .* undefined",
        "LaTeX Warning: Reference .* undefined"
    )

    $undefinedLines = New-Object System.Collections.Generic.List[string]
    foreach ($pattern in $undefinedPatterns) {
        foreach ($m in [regex]::Matches($logText, $pattern)) {
            $undefinedLines.Add($m.Value)
        }
    }

    if ($undefinedLines.Count -gt 0) {
        $sample = ($undefinedLines | Select-Object -Unique | Select-Object -First 8) -join [Environment]::NewLine
        throw "Undefined citations/references detected in log:`n$sample"
    }

    Write-Host "[PASS] Paper build completed"
    Write-Host "       PDF: $pdfPath"
    Write-Host "       Pages: $pages"
    Write-Host "       Log: $logPath"
}
finally {
    Pop-Location
}
