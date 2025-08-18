#!/bin/bash

# Get project root directory (parent of scripts directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Run Ruff linter and auto-fix issues when possible
echo "Running Ruff linter..."
ruff check --fix .

# Format code with Ruff formatter
echo "Formatting code with Ruff..."
ruff format .

echo "Linting complete!"