param (
    [string]$InstallDir = "bin"
)

$ErrorActionPreference = "Stop"

# Resolve absolute path
if (-not (Test-Path $InstallDir)) {
    $InstallDir = Join-Path (Get-Location) $InstallDir
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
} else {
    $InstallDir = Resolve-Path -Path $InstallDir
}

Write-Host "Installing Melisma to $InstallDir..."

# Check dependencies
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) {
    Write-Error "gcc not found. Please install MinGW (e.g., via Chocolatey or MSYS2)."
    exit 1
}

$MakeCmd = "make"
if (-not (Get-Command make -ErrorAction SilentlyContinue)) {
    if (Get-Command mingw32-make -ErrorAction SilentlyContinue) {
        $MakeCmd = "mingw32-make"
    } else {
        Write-Error "make not found. Please install MinGW or ensure make is in your PATH."
        exit 1
    }
}

if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    Write-Error "tar not found. Windows 10/11 should have it by default."
    exit 1
}

$WorkDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $WorkDir | Out-Null
Write-Host "Working in $WorkDir"

$OriginalLocation = Get-Location
Set-Location $WorkDir

try {
    Write-Host "Downloading Melisma..."
    $Url = "https://www.link.cs.cmu.edu/music-analysis/melisma2003.tar.gz"
    Invoke-WebRequest -Uri $Url -OutFile "melisma2003.tar.gz"

    Write-Host "Extracting..."
    tar xvfz melisma2003.tar.gz

    Set-Location "melisma2003/key"

    Write-Host "Compiling..."
    # Using cmd /c to ensure arguments are passed correctly to the make command
    $BuildCmd = "$MakeCmd CC=""gcc -fcommon"""
    Invoke-Expression $BuildCmd

    $SourceExe = "key.exe"
    $DestExe = Join-Path $InstallDir "melisma-key.exe"

    if (Test-Path $SourceExe) {
        Copy-Item $SourceExe -Destination $DestExe -Force
        Write-Host "Melisma installed to $DestExe."
        Write-Host "Please add $InstallDir to your PATH."
    } else {
        Write-Error "Compilation seemed to finish but key.exe was not found."
        exit 1
    }
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
finally {
    Set-Location $OriginalLocation
    if (Test-Path $WorkDir) {
        Remove-Item -Path $WorkDir -Recurse -Force
    }
}
