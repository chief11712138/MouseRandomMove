[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$specPath = Join-Path $projectRoot 'Mouse Random Move.spec'
$distPath = Join-Path $projectRoot 'dist'
$builtExecutable = Join-Path $distPath 'MouseRandomMove.exe'
$finalExecutable = Join-Path $distPath 'Nethard Music.exe'
$venvPyInstaller = Join-Path $projectRoot '.venv\Scripts\pyinstaller.exe'

function Invoke-ApplicationBuild {
    if (Test-Path -LiteralPath $venvPyInstaller) {
        & $venvPyInstaller --clean --noconfirm $specPath
    }
    elseif (Get-Command pyinstaller -ErrorAction SilentlyContinue) {
        & pyinstaller --clean --noconfirm $specPath
    }
    else {
        throw 'PyInstaller was not found. Install the dependencies with: pip install -r requirements.txt'
    }

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
}

function Rename-BuiltExecutable {
    if (-not (Test-Path -LiteralPath $builtExecutable -PathType Leaf)) {
        throw "The expected build output was not found: $builtExecutable"
    }

    if (Test-Path -LiteralPath $finalExecutable) {
        Remove-Item -LiteralPath $finalExecutable -Force
    }

    Move-Item -LiteralPath $builtExecutable -Destination $finalExecutable
}

Push-Location $projectRoot
try {
    Invoke-ApplicationBuild
    Rename-BuiltExecutable
    Write-Host "Build completed: $finalExecutable"
}
finally {
    Pop-Location
}
