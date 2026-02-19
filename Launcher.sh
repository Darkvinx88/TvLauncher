#!/bin/bash

# TVLauncher - Launching script with venv

# Script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# venv directory
VENV_DIR="$DIR/venv"

# Fix permissions
chmod +x "$DIR/installer.sh" 2>/dev/null
chmod +x "$DIR/launcher.sh" 2>/dev/null

# Verify if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: venv not found! Please run installer.sh first."
    exit 1
fi

# Activating venv
source "$VENV_DIR/bin/activate"

# Start launcher
cd "$DIR"
python3 TvLauncher_Linux.py "$@"
