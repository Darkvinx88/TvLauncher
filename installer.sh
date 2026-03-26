#!/bin/bash

echo "================================"
echo "   TV Launcher - Installer"
echo "================================"
echo

# Script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Fix permissions
echo "Setting permissions..."
chmod +x "$DIR/installer.sh" 2>/dev/null
chmod +x "$DIR/launcher.sh" 2>/dev/null
echo "[OK] Permissions set."
echo

# Checks if  Python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 not found!"
    echo "Please install Python 3.10 or higher."
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  Fedora/Bazzite: sudo dnf install python3"
    echo "  Arch: sudo pacman -S python"
    exit 1
fi

# checks python minimum version (3.10)
python3 -c "import sys; exit(0) if sys.version_info >= (3,10) else exit(1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Python version too old!"
    echo "Detected: $(python3 --version)"
    echo "Required: Python 3.10 or higher"
    exit 1
fi

echo "[OK] Found $(python3 --version)"

# Checks if python3-venv is available
python3 -m venv --help &>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] python3-venv not found!"
    echo "Please install it:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  Fedora/Bazzite: sudo dnf install python3"
    exit 1
fi

# Crea virtual environment
echo
echo "Creating virtual environment..."
python3 -m venv "$DIR/venv"
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment."
    exit 1
fi
echo "[OK] Virtual environment created."

# Activate Venv
source "$DIR/venv/bin/activate"
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to activate virtual environment."
    exit 1
fi
echo "[OK] Virtual environment activated."

# Install dependencies
echo
echo "Installing dependencies..."
pip install -r "$DIR/requirements.txt"
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    echo "Check your internet connection and try again."
    exit 1
fi
echo "[OK] Dependencies installed."

echo
echo "================================"
echo "  Installation complete!"
echo "  Run ./launcher.sh to start."
echo "================================"
