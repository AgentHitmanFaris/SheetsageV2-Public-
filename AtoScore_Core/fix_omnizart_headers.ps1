# Fix Python Headers for Omnizart Environment (Python 3.8)
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$OmnizartEnv = Join-Path $RootDir "omnizart_env"
$CacheDir = Join-Path $RootDir "cache"

# Ensure cache exists
if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null }

$NugetUrl = "https://www.nuget.org/api/v2/package/python/3.8.10"
$NugetZip = Join-Path $CacheDir "python.3.8.10.zip"
$ExtractDir = Join-Path $CacheDir "python_38_temp"

# 1. Download Nuget Package
if (-not (Test-Path $NugetZip)) {
    Write-Host "Downloading Python 3.8.10 development files..."
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
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
$ToolsDir = Join-Path $ExtractDir "tools"
$IncludeSrc = Join-Path $ToolsDir "include"
$LibsSrc = Join-Path $ToolsDir "libs"

if (Test-Path $IncludeSrc) {
    Write-Host "Found 'include' directory."
    $DestInclude = Join-Path $OmnizartEnv "include"
    if (-not (Test-Path $DestInclude)) {
        Write-Host "Copying include to $DestInclude..."
        Copy-Item -Path $IncludeSrc -Destination $OmnizartEnv -Recurse -Force
    } else {
        Write-Host "Include directory already exists at $DestInclude."
        # Force copy anyway to be sure? No, if it exists it might be fine or partial.
        # Let's assume if it exists we might need to merge or it's fine.
        # But wait, if compilation failed, it means it's missing OR incomplete.
        # Checking content might be better, but let's just Copy-Item -Force to overlay.
        Copy-Item -Path $IncludeSrc -Destination $OmnizartEnv -Recurse -Force
    }
} else {
    Write-Error "Could not find 'include' in extracted package."
}

if (Test-Path $LibsSrc) {
    Write-Host "Found 'libs' directory."
    $DestLibs = Join-Path $OmnizartEnv "libs"
    if (-not (Test-Path $DestLibs)) {
        Write-Host "Copying libs to $DestLibs..."
        Copy-Item -Path $LibsSrc -Destination $OmnizartEnv -Recurse -Force
    } else {
        Write-Host "Libs directory already exists at $DestLibs."
        Copy-Item -Path $LibsSrc -Destination $OmnizartEnv -Recurse -Force
    }
} else {
    Write-Error "Could not find 'libs' in extracted package."
}

Write-Host "Success! Python 3.8 headers and libs patched into omnizart_env."
