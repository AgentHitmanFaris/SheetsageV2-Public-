#!/bin/bash
set -e

# Configuration
VENV_DIR=".venv"
BIN_DIR="$(pwd)/bin"
CACHE_DIR="$(pwd)/cache"

echo "=========================================="
echo "   Sheet Sage - One-Click Local Setup"
echo "=========================================="
echo ""

# --- 1. System Dependencies ---
echo "--- 1. Checking System Dependencies ---"

OS_NAME=$(uname -s)
MISSING_DEPS=()

check_cmd() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ Missing: $1"
        MISSING_DEPS+=("$1")
    else
        echo "✅ Found: $1"
    fi
}

check_cmd ffmpeg
check_cmd lilypond
check_cmd fluidsynth
check_cmd make
check_cmd wget
check_cmd tar

# Check for build tools for mpi4py (only strict requirement if using jukebox, but good to have)
if ! command -v mpicc &> /dev/null; then
    MISSING_DEPS+=("libopenmpi-dev") # Generic name, handled below
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo ""
    echo "⚠️  Missing system tools: ${MISSING_DEPS[*]}"
    echo "I can attempt to install them for you (requires sudo/admin)."
    read -p "Attempt auto-installation? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$OS_NAME" == "Linux" ]]; then
            if [ -f /etc/debian_version ]; then
                echo "Detected Debian/Ubuntu..."
                sudo apt-get update
                sudo apt-get install -y ffmpeg lilypond fluidsynth libopenmpi-dev wget make tar build-essential
            else
                echo "Unsupported Linux distribution for auto-install. Please install ${MISSING_DEPS[*]} manually."
                exit 1
            fi
        elif [[ "$OS_NAME" == "Darwin" ]]; then
            if ! command -v brew &> /dev/null; then
                echo "Homebrew not found. Please install Homebrew or install dependencies manually."
                exit 1
            fi
            echo "Detected MacOS (Homebrew)..."
            brew install ffmpeg lilypond fluidsynth open-mpi wget
        else
            echo "Unsupported OS: $OS_NAME. Please install dependencies manually."
            exit 1
        fi
    else
        echo "Skipping system dependency installation. Note that the application may fail."
    fi
else
    echo "All system dependencies found."
fi

echo ""

# --- 2. Virtual Environment ---
echo "--- 2. Setting up Python Virtual Environment ---"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate venv for the rest of the script
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

echo ""

# --- 3. Python Dependencies ---
echo "--- 3. Installing Python Dependencies ---"

# Check Python version
PY_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PY_VERSION"

if [[ "$PY_VERSION" != "3.6" && "$PY_VERSION" != "3.7" && "$PY_VERSION" != "3.8" ]]; then
    echo "⚠️  Warning: Active Python version is $PY_VERSION."
    echo "This project targets Python 3.6. Newer versions may have issues with 'torch==1.4.0'."
    echo "Attempting installation anyway..."
fi

# Install requirements
pip install -r requirements.txt || {
    echo "❌ Dependencies failed to install."
    echo "This is likely due to version mismatch with older libraries (torch 1.4)."
    echo "You may need to edit 'requirements.txt' to use newer versions compatible with your system."
    read -p "Continue anyway (e.g. if you fixed it manually)? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

# Install project in editable mode
pip install -e .

echo ""

# --- 4. Install Melisma ---
echo "--- 4. Installing Melisma (Key Detection) ---"
./scripts/install_melisma.sh "$BIN_DIR"

echo ""

# --- 5. Download Models ---
echo "--- 5. Downloading Models ---"
mkdir -p "$CACHE_DIR"
export SHEETSAGE_CACHE_DIR="$CACHE_DIR"

# Check if models already exist (heuristic check)
if [ -d "$CACHE_DIR/sheetsage" ]; then
    echo "Cache directory not empty, assuming models present. Run 'python -m sheetsage.assets SHEETSAGE_V02_HANDCRAFTED' manually to force update."
else
    python -m sheetsage.assets SHEETSAGE_V02_HANDCRAFTED
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "To run the application, use the helper script:"
echo "  ./run_local.sh <input_file>"
echo ""
echo "Or manually:"
echo "  source $VENV_DIR/bin/activate"
echo "  export PATH=\$PATH:$BIN_DIR"
echo "  python -m sheetsage.infer <input_file>"
