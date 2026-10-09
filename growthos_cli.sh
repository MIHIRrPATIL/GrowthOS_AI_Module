#!/usr/bin/env bash
# GrowthOS Presentation CLI Launcher
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$DIR/research/ai-module/.venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "Python environment not found at $PYTHON_BIN. Using system python3."
    PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" "$DIR/research/growthos_cli.py" "$@"
