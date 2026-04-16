#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export QT_QPA_PLATFORM=xcb

# Use Bubbly ecosystem python path
export PYTHONPATH="$(dirname "$DIR")/Locky/libs"

python3 "$DIR/main.py"
