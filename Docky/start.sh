#!/bin/bash
# Start Docky: The Bubble App Controller

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Use shared libs from Locky to avoid system permission issues
export PYTHONPATH="$DIR/../Locky/libs"

# Force X11 backend for better desktop positioning
export QT_QPA_PLATFORM=xcb

# Use python3 directly as we assume PyQt6 and psutil are in system/user path
# (since they are used by neighbor Bubbly apps)
python3 "$DIR/main.py"
