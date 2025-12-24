"""
Build script for creating a standalone Windows executable of atoscore.
This uses PyInstaller to bundle the application with all dependencies.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "atoscore.spec"

def clean_previous_builds():
    """Remove previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   ✓ Removed {dir_path}")

def create_pyinstaller_spec():
    """Create a PyInstaller spec file for the build."""
    print("\n📝 Creating PyInstaller spec file...")
    
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files and submodules for key packages
datas = []
hiddenimports = []

# Gradio and dependencies
datas += collect_data_files('gradio')
datas += collect_data_files('gradio_client')
hiddenimports += collect_submodules('gradio')
hiddenimports += collect_submodules('gradio_client')

# ML Libraries
datas += collect_data_files('torch')
datas += collect_data_files('torchaudio')
datas += collect_data_files('tensorflow')
datas += collect_data_files('librosa')
datas += collect_data_files('basic_pitch')
datas += collect_data_files('demucs')
datas += collect_data_files('transformers')

hiddenimports += collect_submodules('torch')
hiddenimports += collect_submodules('torchaudio')
hiddenimports += collect_submodules('librosa')
hiddenimports += collect_submodules('basic_pitch')
hiddenimports += collect_submodules('demucs')
hiddenimports += collect_submodules('scipy')
hiddenimports += collect_submodules('sklearn')
hiddenimports += collect_submodules('numba')

# Additional hidden imports
hiddenimports += [
    'pretty_midi',
    'pyfluidsynth',
    'validators',
    'matplotlib',
    'numpy',
    'scipy',
    'PIL',
    'pydub',
    'resampy',
    'soundfile',
    'soxr',
    'audioread',
    'ffmpeg',
    'uvicorn',
    'fastapi',
    'pydantic',
    'pkg_resources.py2_warn',
    'pkg_resources.markers',
]

# Add atoscore package data
datas += [
    ('atoscore', 'atoscore'),
    ('soundfont', 'soundfont'),
    ('bin', 'bin'),
    ('libs', 'libs'),
]

# Add CUDA libraries if they exist
if os.path.exists('cuda_libs'):
    datas += [('cuda_libs', 'cuda_libs')]

a = Analysis(
    ['launch_gradio.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib.tests', 'numpy.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='atoscore',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True to show console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='atoscore',
)
"""
    
    with open(SPEC_FILE, 'w') as f:
        f.write(spec_content)
    
    print(f"   ✓ Created {SPEC_FILE}")

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    print("\n📦 Checking PyInstaller installation...")
    try:
        import PyInstaller
        print("   ✓ PyInstaller already installed")
    except ImportError:
        print("   Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("   ✓ PyInstaller installed")

def build_executable():
    """Build the executable using PyInstaller."""
    print("\n🔨 Building executable with PyInstaller...")
    print("   This may take several minutes...")
    
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE)
    ]
    
    subprocess.check_call(cmd)
    print("   ✓ Build completed!")

def copy_additional_files():
    """Copy additional files that need to be in the distribution."""
    print("\n📂 Copying additional files to distribution...")
    
    dist_atoscore = DIST_DIR / "atoscore"
    
    # Files and directories to copy
    items_to_copy = [
        ('.atoscore', '.atoscore'),  # Pre-trained models
        ('output', 'output'),  # Output directory
        ('temp', 'temp'),  # Temp directory
        ('temp_playback', 'temp_playback'),  # Playback temp
        ('cache', 'cache'),  # Cache directory
        ('README.md', 'README.md'),
        ('HowToUse.md', 'HowToUse.md'),
        ('GPU_SETUP_GUIDE.md', 'GPU_SETUP_GUIDE.md'),
    ]
    
    # Check if omnizart_env exists (external environment)
    if (PROJECT_ROOT / 'omnizart_env').exists():
        items_to_copy.append(('omnizart_env', 'omnizart_env'))
    
    for src, dst in items_to_copy:
        src_path = PROJECT_ROOT / src
        dst_path = dist_atoscore / dst
        
        if src_path.exists():
            if src_path.is_dir():
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"   ✓ Copied directory: {src}")
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"   ✓ Copied file: {src}")
        else:
            print(f"   ⚠ Skipped (not found): {src}")

def create_launcher_script():
    """Create a launcher batch script for the executable."""
    print("\n📝 Creating launcher script...")
    
    dist_atoscore = DIST_DIR / "atoscore"
    launcher_path = dist_atoscore / "atoscore.bat"
    
    launcher_content = """@echo off
:: atoscore Launcher
:: This script sets up the environment and launches the application

echo ========================================
echo     NC- AtoScore Launcher
echo ========================================
echo.

:: Get the directory where this script is located
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: Set environment variables
set "atoscore_TEMP=%APP_DIR%temp"
set "atoscore_CACHE_DIR=%APP_DIR%.atoscore"
set "HF_HOME=%APP_DIR%cache\\huggingface"
set "TORCH_HOME=%APP_DIR%cache\\torch"

:: Add local bins to PATH
set "PATH=%APP_DIR%bin;%PATH%"
set "PATH=%APP_DIR%libs\\lilypond-2.24.3\\bin;%PATH%"
set "PATH=%APP_DIR%libs\\w64devkit\\bin;%PATH%"

:: Add CUDA libraries if available
if exist "%APP_DIR%cuda_libs" (
    set "PATH=%APP_DIR%cuda_libs;%PATH%"
    set "CUDA_PATH=%APP_DIR%cuda_libs"
    echo CUDA libraries detected and added to PATH
)

:: Create necessary directories
if not exist "%atoscore_TEMP%" mkdir "%atoscore_TEMP%"
if not exist "%APP_DIR%output" mkdir "%APP_DIR%output"
if not exist "%APP_DIR%temp_playback" mkdir "%APP_DIR%temp_playback"

:: Launch the application
echo Starting NC- AtoScore...
echo.
"%APP_DIR%atoscore.exe" %*

:: Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Application closed normally.
) else (
    echo.
    echo Application exited with error code: %ERRORLEVEL%
    pause
)
"""
    
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    
    print(f"   ✓ Created {launcher_path}")

def create_readme():
    """Create a README for the distribution."""
    print("\n📝 Creating distribution README...")
    
    dist_atoscore = DIST_DIR / "atoscore"
    readme_path = dist_atoscore / "START_HERE.txt"
    
    readme_content = """
╔══════════════════════════════════════════════════════════════════╗
║                    NC- AtoScore - Portable                      ║
║              AI Music Transcription Suite for Windows            ║
╚══════════════════════════════════════════════════════════════════╝

🎼 GETTING STARTED:

1. Double-click "atoscore.bat" to launch the application
2. Wait for the Gradio interface to open in your browser
3. The application will be available at: http://127.0.0.1:7860

📋 SYSTEM REQUIREMENTS:

- Windows 10/11 (64-bit)
- NVIDIA GPU with 6GB+ VRAM (recommended for best performance)
- 8GB+ RAM
- 10GB+ free disk space

⚙️ FIRST RUN:

The first time you run NC- AtoScore, it may take a minute to:
- Initialize the environment
- Check for GPU support
- Load pre-trained models

🎵 FEATURES:

- NC- AtoScore (Lunaverus CNN): Custom-trained piano transcription
- Basic Pitch: Spotify's polyphonic transcription with pitch bend
- Omnizart: Advanced transcription (Music, Drum, Chord, Vocal, Beat)
- Demucs: Vocal/instrument separation
- Audio Synthesis: FluidSynth integration

📚 DOCUMENTATION:

- README.md: Full project documentation
- HowToUse.md: Step-by-step usage guide
- GPU_SETUP_GUIDE.md: GPU acceleration setup

⚠️ TROUBLESHOOTING:

1. GPU Not Detected:
   - Ensure NVIDIA drivers are up to date
   - Check that cuda_libs folder exists
   - Restart the application

2. Audio Playback Issues:
   - Use the "Restart App" button in the interface
   - Check that soundfont files are present
   - Download files directly from the output folder

3. Transcription Errors:
   - Check console output for detailed error messages
   - Ensure input audio is in a supported format (MP3, WAV, FLAC)
   - Try with a shorter audio clip first

🔧 SUPPORT:

For issues and questions, please visit:
https://github.com/your-repo/atoscore

═══════════════════════════════════════════════════════════════════

Developed by NC-Engineering
Powered by: TensorFlow, PyTorch, Gradio, Librosa, Omnizart, Basic Pitch

Generated by Antigravity AI
"""
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"   ✓ Created {readme_path}")

def main():
    """Main build process."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           atoscore Windows Executable Builder              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    try:
        # Change to project directory
        os.chdir(PROJECT_ROOT)
        
        # Build steps
        clean_previous_builds()
        install_pyinstaller()
        create_pyinstaller_spec()
        build_executable()
        copy_additional_files()
        create_launcher_script()
        create_readme()
        
        print("\n" + "="*64)
        print("✅ BUILD COMPLETED SUCCESSFULLY!")
        print("="*64)
        print(f"\n📁 Distribution folder: {DIST_DIR / 'atoscore'}")
        print(f"\n📦 Next steps:")
        print("   1. Test the application by running: dist/atoscore/atoscore.bat")
        print("   2. Create an installer using the Inno Setup script (see build_installer.iss)")
        print("   3. Distribute the installer to users")
        print("\n" + "="*64)
        
    except Exception as e:
        print(f"\n❌ BUILD FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

