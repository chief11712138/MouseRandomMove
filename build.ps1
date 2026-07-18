[CmdletBinding()]
param(
    [switch]$Pause
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-StartedFromExplorer {
    try {
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $PID"
        $parent = Get-Process -Id $current.ParentProcessId -ErrorAction Stop
        return $parent.ProcessName -ieq 'explorer'
    }
    catch {
        return $false
    }
}

$projectRoot = $PSScriptRoot
$specPath = Join-Path $projectRoot 'Mouse Random Move.spec'
$requirementsPath = Join-Path $projectRoot 'requirements.txt'
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$dependencyStamp = Join-Path $venvPath '.nethard-requirements.sha256'
$distPath = Join-Path $projectRoot 'dist'
$builtExecutable = Join-Path $distPath 'MouseRandomMove.exe'
$finalExecutable = Join-Path $distPath 'Nethard Music.exe'
$pauseWhenDone = $Pause -or (Test-StartedFromExplorer)

function Get-PythonLauncher {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        return [PSCustomObject]@{
            File = $py.Source
            Prefix = @('-3')
        }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        return [PSCustomObject]@{
            File = $python.Source
            Prefix = @()
        }
    }

    throw 'Python 3 was not found. Install 64-bit Python 3.12 or newer and enable "Add Python to PATH".'
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage Exit code: $LASTEXITCODE."
    }
}

function Initialize-BuildEnvironment {
    if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
        throw "Requirements file was not found: $requirementsPath"
    }

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        Write-Host '[1/3] Creating local Python environment...'
        $launcher = Get-PythonLauncher
        $versionArguments = @($launcher.Prefix) + @(
            '-c',
            'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'
        )
        Invoke-CheckedCommand -FilePath $launcher.File -Arguments $versionArguments -FailureMessage 'Python 3.12 or newer is required.'

        $venvArguments = @($launcher.Prefix) + @('-m', 'venv', $venvPath)
        Invoke-CheckedCommand -FilePath $launcher.File -Arguments $venvArguments -FailureMessage 'Failed to create the local Python environment.'
    }
    else {
        Write-Host '[1/3] Local Python environment found.'
    }

    $requirementsHash = (Get-FileHash -LiteralPath $requirementsPath -Algorithm SHA256).Hash
    $installedHash = if (Test-Path -LiteralPath $dependencyStamp -PathType Leaf) {
        (Get-Content -Raw -LiteralPath $dependencyStamp).Trim()
    }
    else {
        ''
    }

    $probeCode = "import importlib.util; names = ('PyInstaller', 'ttkbootstrap'); raise SystemExit(0 if all(importlib.util.find_spec(name) for name in names) else 1)"
    & $venvPython -c $probeCode
    $importsAvailable = $LASTEXITCODE -eq 0
    if (-not $importsAvailable -or $installedHash -ne $requirementsHash) {
        Write-Host '[2/3] Installing build dependencies...'
        $pipArguments = @(
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            '-r',
            $requirementsPath
        )
        Invoke-CheckedCommand -FilePath $venvPython -Arguments $pipArguments -FailureMessage 'Failed to install build dependencies.'
        Set-Content -LiteralPath $dependencyStamp -Value $requirementsHash -Encoding Ascii
    }
    else {
        Write-Host '[2/3] Build dependencies are up to date.'
    }
}

function Invoke-ApplicationBuild {
    if (-not (Test-Path -LiteralPath $specPath -PathType Leaf)) {
        throw "PyInstaller configuration was not found: $specPath"
    }

    Write-Host '[3/3] Building application...'
    $buildArguments = @('-m', 'PyInstaller', '--clean', '--noconfirm', $specPath)
    Invoke-CheckedCommand -FilePath $venvPython -Arguments $buildArguments -FailureMessage 'PyInstaller failed.'
}

function Rename-BuiltExecutable {
    if (-not (Test-Path -LiteralPath $builtExecutable -PathType Leaf)) {
        throw "The expected build output was not found: $builtExecutable"
    }

    if (Test-Path -LiteralPath $finalExecutable -PathType Leaf) {
        try {
            Remove-Item -LiteralPath $finalExecutable -Force
        }
        catch {
            throw "Unable to replace $finalExecutable. Close the running Nethard Music.exe and try again."
        }
    }

    Move-Item -LiteralPath $builtExecutable -Destination $finalExecutable
}

$buildSucceeded = $false
$locationPushed = $false
try {
    Push-Location $projectRoot
    $locationPushed = $true
    Initialize-BuildEnvironment
    Invoke-ApplicationBuild
    Rename-BuiltExecutable
    $buildSucceeded = $true
    Write-Host ''
    Write-Host "Build completed: $finalExecutable" -ForegroundColor Green
}
catch {
    Write-Host ''
    Write-Host 'Build failed.' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    if ($locationPushed) {
        Pop-Location
    }
}

if ($pauseWhenDone) {
    [void](Read-Host 'Press Enter to close this window')
}

if (-not $buildSucceeded) {
    exit 1
}
