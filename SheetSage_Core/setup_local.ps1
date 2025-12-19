# Setup script for Windows
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$VenvDir = ".venv"
$PythonEmbeded = Join-Path $PSScriptRoot "python_embeded"
$BinDir = Join-Path $PSScriptRoot "bin"
$CacheDir = Join-Path $PSScriptRoot "cache"

# Add local bin to PATH strictly for this session so we can find portable tools
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}
$Env:Path = "$BinDir;$Env:Path"

Write-Host "=========================================="
Write-Host "   Sheet Sage - One-Click Local Setup"
Write-Host "=========================================="
Write-Host ""
Write-Host "Check: Local 'bin' folder added to PATH."
Write-Host "       (You can put portable ffmpeg/lilypond here!)"
Write-Host ""

# --- 0. Python Environment Setup (Embedded Only) ---
Write-Host "--- 0. Setting up Python Environment ---"

if (-not (Test-Path $PythonEmbeded)) {
    Write-Host "Downloading Embedded Python 3.11.9..."
    $PythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null }
    $PythonZip = Join-Path $CacheDir "python-3.11.9-embed-amd64.zip"

    # Download if not already cached
    if (-not (Test-Path $PythonZip)) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        try {
            Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonZip
        } catch {
            Write-Error "Failed to download Python embedded zip. Check your internet connection."
            exit 1
        }
    }

    if (-not (Test-Path $PythonZip)) {
        Write-Error "Python zip file not found at $PythonZip after download attempt."
        exit 1
    }

    Write-Host "Extracting Python..."
    Expand-Archive -Path $PythonZip -DestinationPath $PythonEmbeded -Force
} else {
    Write-Host "Found 'python_embeded' folder. Using existing Embedded Python."
}

# Configure environment variables to use embedded python
$Env:Path = "$PythonEmbeded;$(Join-Path $PythonEmbeded 'Scripts');$Env:Path"
$PythonExe = Join-Path $PythonEmbeded "python.exe"

# Enable 'import site' in ._pth file to support pip/packages
$PthFiles = Get-ChildItem -Path $PythonEmbeded -Filter "python*._pth"
foreach ($File in $PthFiles) {
    $Content = Get-Content $File.FullName
    if ($Content -match "#import site") {
        Write-Host "Uncommenting 'import site' in $($File.Name)..."
        $Content -replace "#import site", "import site" | Set-Content $File.FullName
    }
}

# Verify Python access
try {
    & $PythonExe --version | Out-Null
    Write-Host "Currently using: $PythonExe"
} catch {
    Write-Error "Failed to execute '$PythonExe'. Check your installation."
    exit 1
}

# --- 1. System Dependencies ---
Write-Host "--- 1. Checking & Installing System Dependencies ---"

$LibsDir = Join-Path $PSScriptRoot "libs"
if (-not (Test-Path $LibsDir)) { New-Item -ItemType Directory -Path $LibsDir -Force | Out-Null }

function Download-And-Extract {
    param($Url, $ZipName, $DestDir)
    $ZipPath = Join-Path $CacheDir $ZipName
    
    if (-not (Test-Path $ZipPath)) {
        Write-Host "   Downloading $ZipName..."
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        } catch {
            Write-Error "   Failed to download $Url"
            Write-Error "   Error details: $_"
            return $false
        }
    }
    
    Write-Host "   Extracting $ZipName..."
    Expand-Archive -Path $ZipPath -DestinationPath $DestDir -Force
    return $true
}

# 1.1 FFmpeg
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "✅ Found: ffmpeg"
} else {
    Write-Host "❌ Missing: ffmpeg. Installing..."
    $FFUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    $TempDir = Join-Path $CacheDir "ffmpeg_temp"
    if (Download-And-Extract $FFUrl "ffmpeg.zip" $TempDir) {
        # Find bin folder
        $FFBin = Get-ChildItem -Path $TempDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
        if ($FFBin) {
            Copy-Item (Join-Path $FFBin.DirectoryName "*") -Destination $BinDir -Force
            Write-Host "   Installed FFmpeg to $BinDir"
        }
        Remove-Item $TempDir -Recurse -Force
    }
}

# 1.2 FluidSynth
if (Get-Command fluidsynth -ErrorAction SilentlyContinue) {
    Write-Host "✅ Found: fluidsynth"
} else {
    Write-Host "❌ Missing: fluidsynth. Installing..."
    $FSUrl = "https://github.com/FluidSynth/fluidsynth/releases/download/v2.3.4/fluidsynth-2.3.4-win10-x64.zip"
    $TempDir = Join-Path $CacheDir "fluidsynth_temp"
    if (Download-And-Extract $FSUrl "fluidsynth.zip" $TempDir) {
        # Copy everything from bin to BinDir (includes DLLs)
        $FSBin = Join-Path $TempDir "bin"
        if (Test-Path $FSBin) {
            Copy-Item "$FSBin\*" -Destination $BinDir -Force
            Write-Host "   Installed FluidSynth to $BinDir"
        }
        Remove-Item $TempDir -Recurse -Force
    }
}

# 1.3 MinGW (GCC & Make) via w64devkit
$NeedGcc = -not (Get-Command gcc -ErrorAction SilentlyContinue)
$NeedMake = (-not (Get-Command make -ErrorAction SilentlyContinue)) -and (-not (Get-Command mingw32-make -ErrorAction SilentlyContinue))

if ($NeedGcc -or $NeedMake) {
    Write-Host "❌ Missing: GCC/Make. Installing w64devkit (Portable MinGW)..."
    # Check if already installed in libs
    $W64Dir = Join-Path $LibsDir "w64devkit"
    if (-not (Test-Path "$W64Dir\bin\gcc.exe")) {
        $MinGWUrl = "https://github.com/skeeto/w64devkit/releases/download/v1.20.0/w64devkit-1.20.0.zip"
        Download-And-Extract $MinGWUrl "w64devkit.zip" $LibsDir
    }
    
    if (Test-Path "$W64Dir\bin") {
        $Env:Path = "$W64Dir\bin;$Env:Path"
        Write-Host "   Added w64devkit to PATH."
    }
} else {
    Write-Host "✅ Found: GCC and Make"
}

# 1.4 LilyPond
if (Get-Command lilypond -ErrorAction SilentlyContinue) {
    Write-Host "✅ Found: lilypond"
} else {
    Write-Host "❌ Missing: lilypond. Installing..."
    # Check if already in libs
    $LilyDir = Join-Path $LibsDir "lilypond-2.24.3"
    if (-not (Test-Path "$LilyDir")) {
        $LilyUrl = "https://gitlab.com/lilypond/lilypond/-/releases/v2.24.3/downloads/lilypond-2.24.3-mingw-x86_64.zip"
        Download-And-Extract $LilyUrl "lilypond.zip" $LibsDir
    }
    
    # Locate the bin directory dynamically as it might be nested
    $LilyBin = Get-ChildItem -Path $LibsDir -Recurse -Filter "lilypond.exe" | Select-Object -First 1
    if ($LilyBin) {
        $Env:Path = "$($LilyBin.DirectoryName);$Env:Path"
        Write-Host "   Added LilyPond to PATH."
    }
}

Write-Host "System dependencies check complete."
Write-Host ""

# --- 2. Installing Pip & Dependencies ---
Write-Host "--- 2. Installing Python Dependencies ---"

# Ensure pip is installed
Write-Host "Checking for pip..."
$PipInstalled = $false
try {
    & $PythonExe -c "import pip" *>$null
    if ($LastExitCode -eq 0) {
        $PipInstalled = $true
    }
} catch {
    $PipInstalled = $false
}

if ($PipInstalled) {
    Write-Host "Pip is already installed."
} else {
    Write-Host "Pip not found. Installing..."
    $GetPip = Join-Path $CacheDir "get-pip.py"
    if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null }
    
    if (-not (Test-Path $GetPip)) {
        Write-Host "Downloading get-pip.py..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
    }
    
    Write-Host "Running get-pip.py..."
    & $PythonExe $GetPip
}

# Upgrade pip, setuptools, and wheel
try {
    & $PythonExe -m pip install --upgrade pip setuptools wheel
} catch {
    Write-Warning "Failed to upgrade pip/setuptools/wheel. Continuing..."
}

# Pre-install Cython and NumPy (Required for Madmom build)
Write-Host "Pre-installing Cython and NumPy..."
try {
    & $PythonExe -m pip install Cython "numpy>=1.22"
} catch {
    Write-Warning "Failed to pre-install Cython/NumPy. Madmom installation might fail."
}

# Upgrade yt-dlp to ensure it's up-to-date for YouTube downloads
Write-Host "Upgrading yt-dlp..."
try {
    & $PythonExe -m pip install --upgrade yt-dlp
} catch {
    Write-Warning "Failed to upgrade yt-dlp. YouTube downloads might be unstable."
}

# Check version (simplified syntax to avoid PS quoting issues)
$PyVer = & $PythonExe -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))"
Write-Host "Python version: $PyVer"

# Install requirements
try {
    & $PythonExe -m pip install -r requirements.txt
} catch {
    Write-Host "❌ Dependencies failed to install."
    $resp = Read-Host "Continue anyway? (y/N)"
    if ($resp -notmatch "^[Yy]$") { exit 1 }
}

# Install Madmom (Optional / Might fail)
Write-Host "Attempting to install Madmom (Beat Tracking)..."
try {
    & $PythonExe -m pip install "git+https://github.com/CPJKU/madmom.git@27f032e8947204902c675e5e341a3faf5dc86dae"
} catch {
    Write-Warning "Madmom failed to install (likely due to missing C++ tools)."
    Write-Warning "The application will fallback to Librosa for beat tracking."
    Write-Warning "This is expected and fine."
}

# Install project
& $PythonExe -m pip install -e .

# --- 3. Install Special Dependencies ---
Write-Host "--- 3. Installing Special Dependencies ---"

# 1. Pop2Piano Dependencies (Transformers/HuggingFace)
& $PythonExe -m pip install "transformers" "sentencepiece" "protobuf" "accelerate" "numpy>=1.22"

# 2. Basic Pitch Dependencies (If not covered)
# & $PythonExe -m pip install "basic-pitch" # Already in requirements.txt usually

# We also support Pop2Piano (Transformers).

# --- 4. Install Melisma ---
Write-Host "--- 4. Installing Melisma ---"
# Check if Melisma is already installed
if (-not (Test-Path "$(Join-Path $BinDir 'melisma-key.exe')")) {
    try {
        .\scripts\install_melisma.ps1 -InstallDir $BinDir
    } catch {
        Write-Warning "Melisma installation failed or was skipped. Some features may not work."
    }
} else {
    Write-Host "Melisma already installed."
}

# --- 5. Downloading Models ---
Write-Host "--- 5. Downloading Models ---"
New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
$Env:SHEETSAGE_CACHE_DIR = $CacheDir

if (Test-Path "$CacheDir/sheetsage") {
    Write-Host "Cache directory not empty, assuming models present."
} else {
    & $PythonExe -m sheetsage.assets SHEETSAGE_V02_HANDCRAFTED
}

# --- 6. Post-Install Verification ---
Write-Host "--- 6. Verifying Installation ---"
try {
    & $PythonExe -c "import gradio, torch, validators, demucs, piano_transcription_inference; print('All key dependencies importable.')"
} catch {
    Write-Warning "Post-install verification failed. Some dependencies might be missing."
}

Write-Host "Setup Complete!"
Write-Host "Run the application with: .\run_local.bat"
