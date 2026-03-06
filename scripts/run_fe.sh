#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="${REPO_ROOT}/apps/web"

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required but was not found in PATH."
  exit 1
fi

if [[ ! -d "${WEB_DIR}" ]]; then
  echo "Error: frontend directory not found: ${WEB_DIR}"
  exit 1
fi

cd "${WEB_DIR}"

if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend dev server at http://localhost:3000"
exec npm run dev
