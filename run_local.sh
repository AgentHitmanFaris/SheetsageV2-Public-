#!/bin/bash
set -e

# Configuration
VENV_DIR=".venv"
BIN_DIR="$(pwd)/bin"
CACHE_DIR="$(pwd)/cache"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found. Please run './setup_local.sh' first."
    exit 1
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Add local bin to PATH (for melisma-key)
export PATH="$PATH:$BIN_DIR"
export SHEETSAGE_CACHE_DIR="$CACHE_DIR"

# Run the inference command
python -m sheetsage.infer "$@"
