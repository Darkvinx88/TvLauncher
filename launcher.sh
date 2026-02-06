#!/bin/bash

# TVLauncher - Launching script with venv

# Script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# venv directory
VENV_DIR="$DIR/venv"

# verify if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Errore: venv not found in $VENV_DIR!"
    exit 1
fi

# Activating venv
source "$VENV_DIR/bin/activate"

# start launcher
cd "$DIR"
python3 TvLauncher_Linux.py "$@"

