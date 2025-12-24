# PowerShell script to download Python headers for embedded distribution
$ErrorActionPreference = "Stop"

$PythonVersion = "3.8.10"
$EmbedDir = Join-Path (Get-Location) "python_embeded"
$IncludeDir = Join-Path $EmbedDir "Include"
$PythonExe = Join-Path $EmbedDir "python.exe"

# Clean up Include dir if it only has pyconfig.h to retry
if (Test-Path $IncludeDir) {
    $Items = Get-ChildItem -Path $IncludeDir
    if ($Items.Count -le 1) {
        Write-Host "Incomplete headers detected. Retrying..."
        # Don't delete pyconfig.h if it exists
    } else {
        Write-Host "Headers seem to be present."
        exit 0
    }
} else {
    New-Item -ItemType Directory -Path $IncludeDir | Out-Null
}

Write-Host "Downloading Python $PythonVersion headers..."
$Url = "https://www.python.org/ftp/python/$PythonVersion/Python-$PythonVersion.tar.xz"
$TarFile = Join-Path (Get-Location) "cache\Python-$PythonVersion.tar.xz"

if (-not (Test-Path "cache")) { New-Item -ItemType Directory -Path "cache" | Out-Null }

if (-not (Test-Path $TarFile)) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $TarFile
}

Write-Host "Extracting headers using Python..."
# We use the embedded python to extract the tar file. 
# It's safer than relying on system tools.

$ScriptBlock = @"
import tarfile
import os
import shutil

tar_path = r'$TarFile'
extract_root = r'cache\py_headers_temp'
target_include = r'$IncludeDir'

if os.path.exists(extract_root):
    shutil.rmtree(extract_root)
os.makedirs(extract_root)

print(f'Extracting {tar_path}...')
with tarfile.open(tar_path) as tar:
    # Filter only Include/
    members = [m for m in tar.getmembers() if 'Include' in m.name]
    tar.extractall(path=extract_root, members=members)

# Move files
# Source is usually cache/py_headers_temp/Python-3.8.10/Include
source_include = os.path.join(extract_root, 'Python-$PythonVersion', 'Include')

if os.path.exists(source_include):
    print(f'Moving headers from {source_include} to {target_include}...')
    for item in os.listdir(source_include):
        s = os.path.join(source_include, item)
        d = os.path.join(target_include, item)
        if os.path.isfile(s):
            shutil.copy2(s, d)
        elif os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
    print('Headers extracted successfully.')
else:
    print(f'Error: Could not find Include directory at {source_include}')
    exit(1)
"@

$ScriptFile = "extract_headers.py"
Set-Content -Path $ScriptFile -Value $ScriptBlock
& $PythonExe $ScriptFile
Remove-Item $ScriptFile

# Fix for pyconfig.h (It's often missing or named PC/pyconfig.h in source)
if (-not (Test-Path "$IncludeDir\pyconfig.h")) {
    Write-Host "Downloading pyconfig.h for Windows..."
    $UrlConfig = "https://raw.githubusercontent.com/python/cpython/3.8/PC/pyconfig.h"
    Invoke-WebRequest -Uri $UrlConfig -OutFile "$IncludeDir\pyconfig.h"
}

Write-Host "Python header setup complete."