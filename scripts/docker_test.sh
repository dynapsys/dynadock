#!/usr/bin/env bash
# Run integration tests inside Docker using the test fixture compose file.
set -euo pipefail

COMPOSE_YAML="tests/fixtures/docker-compose.test.yaml"

echo "Starting docker-compose for integration tests..."
docker-compose -f "$COMPOSE_YAML" up -d

cleanup() {
  echo "Stopping docker-compose test stack..."
  docker-compose -f "$COMPOSE_YAML" down -v || true
}
trap cleanup EXIT

if command -v uv >/dev/null 2>&1; then
  uv run pytest tests/integration/ -v -m docker
else
  python3 -m pytest tests/integration/ -v -m docker
fi
