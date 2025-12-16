# Run script for Windows
$ErrorActionPreference = "Stop"

$VenvDir = ".venv"
$PythonEmbeded = Join-Path (Get-Location) "python_embeded"
$BinDir = Join-Path (Get-Location) "bin"
$CacheDir = Join-Path (Get-Location) "cache"

# 1. Try to find Embedded Python (Fooocus style)
if (Test-Path $PythonEmbeded) {
    Write-Host "Using Embedded Python..."
    $Env:Path = "$PythonEmbeded;$(Join-Path $PythonEmbeded 'Scripts');$Env:Path"
}
# 2. Else check for existing venv
elseif (Test-Path $VenvDir) {
    # Activate venv
    $Env:VIRTUAL_ENV = $VenvDir
    $Env:Path = "$(Join-Path $VenvDir 'Scripts');$Env:Path"
}
# 3. Else fallback to system python (will be checked by 'python' command)
else {
    # If standard setup wasn't run, this might fail, but let it proceed to fail at execution or check
    Write-Warning "No embedded python or .venv found. Relying on system PATH."
}

# Add local bin to PATH
$Env:Path = "$BinDir;$Env:Path"

# Add libs to PATH (LilyPond, GCC, etc.)
$LibsDir = Join-Path (Get-Location) "libs"
if (Test-Path $LibsDir) {
    # Find LilyPond bin
    $LilyBin = Get-ChildItem -Path $LibsDir -Recurse -Filter "lilypond.exe" | Select-Object -ExpandProperty DirectoryName -First 1
    if ($LilyBin) {
        $Env:Path = "$LilyBin;$Env:Path"
        Write-Host "Added LilyPond to PATH: $LilyBin"
    }
    
    # Find GCC/Make (w64devkit)
    $GccBin = Get-ChildItem -Path $LibsDir -Recurse -Filter "gcc.exe" | Select-Object -ExpandProperty DirectoryName -First 1
    if ($GccBin) {
        $Env:Path = "$GccBin;$Env:Path"
        Write-Host "Added GCC/Make to PATH: $GccBin"
    }
}

# Set cache dir: Use local .sheetsage if it exists (user provided models), else use default 'cache'
$LocalModels = Join-Path (Get-Location) ".sheetsage"
if (Test-Path $LocalModels) {
    Write-Host "Found local models in '.sheetsage'. Using them."
    $Env:SHEETSAGE_CACHE_DIR = $LocalModels
} else {
    $Env:SHEETSAGE_CACHE_DIR = $CacheDir
}

# Run the Gradio interface
Write-Host "Starting Gradio Interface..."
# Determine Python Executable
if ($Env:SHEETSAGE_PYTHON_EXE) {
    $PythonExec = $Env:SHEETSAGE_PYTHON_EXE
}
elseif (Test-Path $PythonEmbeded) {
    $PythonExec = Join-Path $PythonEmbeded "python.exe"
}
elseif (Test-Path $VenvDir) {
    $PythonExec = Join-Path $VenvDir "Scripts\python.exe"
}
else {
    $PythonExec = "python"
}

# Run the Gradio interface
Write-Host "Starting Gradio Interface..."
Write-Host "Using Python: $PythonExec"
& $PythonExec launch_gradio.py
