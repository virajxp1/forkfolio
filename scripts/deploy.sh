#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-forkfolio}"
IMAGE_NAME="${IMAGE_NAME:-forkfolio}"
if git rev-parse --short HEAD >/dev/null 2>&1; then
  DEFAULT_TAG="$(git rev-parse --short HEAD)"
else
  DEFAULT_TAG="$(date +%Y%m%d%H%M%S)"
fi
TAG="${TAG:-$DEFAULT_TAG}"
ENV_FILE="${ENV_FILE:-.env}"
PORT="${PORT:-8000}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not installed or not on PATH."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "Docker daemon is not running."
    echo "Start Docker Desktop: open -a Docker"
  else
    echo "Docker daemon is not running or not reachable."
  fi
  exit 1
fi

env_args=()
if [ -f "${ENV_FILE}" ]; then
  env_args=(--env-file "${ENV_FILE}")
else
  echo "Env file not found at ${ENV_FILE}; continuing without --env-file."
fi

echo "Building ${IMAGE_NAME}:${TAG}..."
docker build -f docker/Dockerfile -t "${IMAGE_NAME}:${TAG}" .
docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:latest"

if docker ps -a --format '{{.Names}}' | grep -qx "${APP_NAME}"; then
  echo "Removing existing container ${APP_NAME}..."
  docker rm -f "${APP_NAME}"
fi

echo "Starting ${APP_NAME} on port ${PORT}..."
docker run -d \
  --name "${APP_NAME}" \
  --restart unless-stopped \
  "${env_args[@]}" \
  -p "${PORT}:8000" \
  "${IMAGE_NAME}:${TAG}" \
  uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "Waiting for health check..."
for _ in $(seq 1 30); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "${APP_NAME}" 2>/dev/null || true)"

  if [ "${status}" = "healthy" ]; then
    echo "Deploy successful."
    echo "Health: http://localhost:${PORT}/api/v1/health"
    exit 0
  fi

  if [ "${status}" = "unhealthy" ]; then
    echo "Deploy failed: container is unhealthy."
    docker logs --tail 200 "${APP_NAME}" || true
    exit 1
  fi

  sleep 2
done

echo "Deploy timed out waiting for healthy container."
docker logs --tail 200 "${APP_NAME}" || true
exit 1
