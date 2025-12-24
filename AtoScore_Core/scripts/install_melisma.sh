#!/bin/bash
set -e

# Directory where we will install binaries
# Default to ./bin if not specified
INSTALL_DIR=${1:-$(pwd)/bin}
mkdir -p "$INSTALL_DIR"

echo "Installing Melisma to $INSTALL_DIR..."

# Check if wget and make exist
if ! command -v wget &> /dev/null; then
    echo "wget could not be found. Please install it."
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "make could not be found. Please install it."
    exit 1
fi

if ! command -v tar &> /dev/null; then
    echo "tar could not be found. Please install it."
    exit 1
fi

WORK_DIR=$(mktemp -d)
echo "Working in $WORK_DIR"
cd "$WORK_DIR"

wget https://www.link.cs.cmu.edu/music-analysis/melisma2003.tar.gz
if [ "$(uname)" == "Darwin" ]; then
    # sha256sum might not exist on mac, use shasum -a 256
    echo "Skipping checksum verification on macOS for simplicity or use shasum."
else
    echo "b4db2ab616dd2a14c8baff64787d3d0f257df6b0159452fb52fc3e29411743ad  melisma2003.tar.gz" | sha256sum -c -
fi

tar xvfz melisma2003.tar.gz
cd melisma2003/key

# Fix for GCC 10+ which defaults to -fno-common, causing multiple definition errors
echo "Compiling with -fcommon..."
make CC="gcc -fcommon"

cp key "$INSTALL_DIR/melisma-key"

cd /
rm -rf "$WORK_DIR"

echo "Melisma installed to $INSTALL_DIR/melisma-key."
echo "Please add $INSTALL_DIR to your PATH or run with:"
echo "export PATH=\$PATH:$INSTALL_DIR"
