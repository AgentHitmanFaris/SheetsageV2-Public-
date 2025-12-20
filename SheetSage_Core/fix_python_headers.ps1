# Fix Python Headers for Embedded Environment
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$PythonEmbeded = Join-Path $RootDir "python_embeded"
$CacheDir = Join-Path $RootDir "cache"

# Ensure cache exists
if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null }

$NugetUrl = "https://www.nuget.org/api/v2/package/python/3.11.9"
$NugetZip = Join-Path $CacheDir "python.3.11.9.zip"
$ExtractDir = Join-Path $CacheDir "python_full_temp"

# 1. Download Nuget Package
if (-not (Test-Path $NugetZip)) {
    Write-Host "Downloading Python 3.11.9 development files (Nuget)..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Invoke-WebRequest -Uri $NugetUrl -OutFile $NugetZip -UserAgent "Mozilla/5.0"
    } catch {
        Write-Error "Failed to download python nuget package."
        exit 1
    }
}

# 2. Extract
if (-not (Test-Path $ExtractDir)) {
    Write-Host "Extracting..."
    Expand-Archive -Path $NugetZip -DestinationPath $ExtractDir -Force
}

# 3. Locate Include and Libs
# Nuget package structure is typically tools/*.
$ToolsDir = Join-Path $ExtractDir "tools"

$IncludeSrc = Join-Path $ToolsDir "include"
$LibsSrc = Join-Path $ToolsDir "libs"

if (Test-Path $IncludeSrc) {
    Write-Host "Found 'include' directory."
    $DestInclude = Join-Path $PythonEmbeded "include"
    if (-not (Test-Path $DestInclude)) {
        Write-Host "Copying include to $DestInclude..."
        Copy-Item -Path $IncludeSrc -Destination $PythonEmbeded -Recurse -Force
    } else {
        Write-Host "Include directory already exists."
    }
} else {
    Write-Error "Could not find 'include' in extracted package."
}

if (Test-Path $LibsSrc) {
    Write-Host "Found 'libs' directory."
    $DestLibs = Join-Path $PythonEmbeded "libs"
    if (-not (Test-Path $DestLibs)) {
        Write-Host "Copying libs to $DestLibs..."
        Copy-Item -Path $LibsSrc -Destination $PythonEmbeded -Recurse -Force
    } else {
        Write-Host "Libs directory already exists."
    }
} else {
    Write-Error "Could not find 'libs' in extracted package."
}

Write-Host "Success! Python headers and libs patched."
