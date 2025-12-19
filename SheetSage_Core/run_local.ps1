# Run script for Windows
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$VenvDir = ".venv"
# Python Embeded is still in the grand-parent root? No, we moved everything BUT python_embeded.
# Python Embeded is likely still at ../python_embeded. The user said "remove garbage", but python_embeded was potentially left at root.
# Let's check where python_embeded is.
# IF the user said "correct all file/folder position", I should check if they want python_embeded moved too. 
# Usually huge runtimes are kept at root. But if we moved libs/bin/cache/output/.sheetsage to Core, we should look for them in Core.
$PythonEmbeded = Join-Path $PSScriptRoot "python_embeded"
$BinDir = Join-Path $PSScriptRoot "bin"
$CacheDir = Join-Path $PSScriptRoot "cache"

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
$LibsDir = Join-Path $PSScriptRoot "libs"
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
$LocalModels = Join-Path $PSScriptRoot ".sheetsage"
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
# Loop for restart capability (Exit Code 42 = Restart)
$ExitCode = 42
$ScriptArgs = @($args) # Copy args to a modifiable array

while ($ExitCode -eq 42) {
    & $PythonExec launch_gradio.py $ScriptArgs
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -eq 42) {
        Write-Host "Restarting Sheet Sage..." -ForegroundColor Cyan
        Start-Sleep -Seconds 1
        
        # On restart, don't open a new browser tab; the existing one will refresh.
        if ($ScriptArgs -notcontains "--no-browser") {
             $ScriptArgs += "--no-browser"
        }
    }
}
