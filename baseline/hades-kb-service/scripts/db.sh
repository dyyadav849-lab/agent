#!/usr/bin/env bash

# Change to the project root directory
cd "$(dirname "$0")/.."

# Set GOPATH if not already set
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
fi

# Run the Python script with the correct path
exec python -u "$(dirname "$0")/db.py" "$@"
