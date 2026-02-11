#!/usr/bin/env bash

set -euo pipefail

# Get project root directory (parent of scripts directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

if [[ -x ".venv/bin/ruff" ]]; then
  RUFF_BIN=".venv/bin/ruff"
else
  RUFF_BIN="ruff"
fi

echo "Running Ruff linter..."
"$RUFF_BIN" check --fix .

echo "Formatting code with Ruff..."
"$RUFF_BIN" format .

echo "Linting complete!"
