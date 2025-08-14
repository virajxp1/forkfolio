#!/bin/bash

# Run Ruff linter and auto-fix issues when possible
echo "Running Ruff linter..."
ruff check --fix .

# Format code with Ruff formatter
echo "Formatting code with Ruff..."
ruff format .

echo "Linting complete!"